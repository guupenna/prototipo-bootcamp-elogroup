"""Immutable local scenario/decision records; no commercial execution or authentication."""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sqlite3
import uuid

TRANSITIONS = {
    'rascunho': ['revisado', 'cancelado'],
    'revisado': ['aprovado para teste', 'cancelado'],
    'aprovado para teste': ['em execução', 'cancelado'],
    'em execução': ['encerrado', 'cancelado'],
    'encerrado': [], 'cancelado': [],
}
PLAN_FIELDS = ['elegibilidade', 'kpi_primario', 'comparacao', 'guardrails', 'criterio', 'janela']


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def identifier():
    return uuid.uuid4().hex


def required(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'Preencha {label}.')
    return value.strip()


def verify_evidence(e):
    body = {k: v for k, v in e.items() if k != 'evidence_id'}
    digest = hashlib.sha256(encode(body).encode()).hexdigest()[:20]
    if digest != e.get('evidence_id'):
        raise ValueError('Evidência alterada ou sem identificação válida.')


class DecisionStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS cases (
              id TEXT PRIMARY KEY, title TEXT NOT NULL, hypothesis TEXT NOT NULL,
              owner TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS scenarios (
              id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id),
              version INTEGER NOT NULL, created_at TEXT NOT NULL,
              payload TEXT NOT NULL, snapshot_hash TEXT NOT NULL,
              UNIQUE(case_id, version));
            CREATE TABLE IF NOT EXISTS evidence (
              id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS decisions (
              id TEXT PRIMARY KEY, scenario_id TEXT NOT NULL REFERENCES scenarios(id),
              revision INTEGER NOT NULL, status TEXT NOT NULL, reviewer TEXT NOT NULL,
              rationale TEXT NOT NULL, created_at TEXT NOT NULL,
              UNIQUE(scenario_id, revision));
            CREATE TABLE IF NOT EXISTS experiment_plans (
              id TEXT PRIMARY KEY, decision_id TEXT NOT NULL UNIQUE REFERENCES decisions(id),
              payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS audit_events (
              id TEXT PRIMARY KEY, entity_id TEXT NOT NULL, event TEXT NOT NULL,
              payload TEXT NOT NULL, created_at TEXT NOT NULL);
            ''')

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        return db

    def _audit(self, db, entity, event, payload):
        db.execute('INSERT INTO audit_events VALUES (?,?,?,?,?)',
                   (identifier(), entity, event, encode(payload), stamp()))

    def save_scenario(self, snapshot, title='', hypothesis='', owner='', case_id=None):
        """One transaction freezes membership, parameters, sources and evidence."""
        if snapshot.get('scenario', {}).get('tipo') != 'cenario_condicional':
            raise ValueError('Selecione um cenário calculado pelo Engine.')
        scenario = snapshot['scenario']
        base = snapshot['baseline']
        for e in [base, scenario]:
            verify_evidence(e)
        if base['escopo'] != scenario['escopo']:
            raise ValueError('Base e cenário devem ter o mesmo recorte.')
        if base['fontes_sha256'] != scenario['fontes_sha256']:
            raise ValueError('Base e cenário devem usar as mesmas fontes.')
        ids = snapshot.get('order_ids', [])
        if (not ids or len(ids) != len(set(ids)) or
                len(ids) != scenario['valores']['pedidos_elegiveis']):
            raise ValueError('População congelada vazia ou inconsistente.')
        payload = encode(snapshot)
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            if case_id is None:
                title = required(title, 'título')
                hypothesis = required(hypothesis, 'hipótese')
                owner = required(owner, 'responsável')
                case_id = identifier()
                db.execute('INSERT INTO cases VALUES (?,?,?,?,?)',
                           (case_id, title, hypothesis, owner, stamp()))
                self._audit(db, case_id, 'caso_criado', {'owner': owner})
            elif not db.execute('SELECT id FROM cases WHERE id=?', (case_id,)).fetchone():
                raise ValueError('Caso não encontrado.')
            version = db.execute('SELECT COALESCE(MAX(version),0)+1 FROM scenarios WHERE case_id=?', (case_id,)).fetchone()[0]
            sid = identifier()
            db.execute('INSERT INTO scenarios VALUES (?,?,?,?,?,?)',
                       (sid, case_id, version, stamp(), payload, hashlib.sha256(payload.encode()).hexdigest()))
            for e in [base, scenario]:
                db.execute('INSERT OR IGNORE INTO evidence VALUES (?,?)', (e['evidence_id'], encode(e)))
            db.execute('INSERT INTO decisions VALUES (?,?,?,?,?,?,?)',
                       (identifier(), sid, 1, 'rascunho', 'sistema', 'Cenário salvo; ainda não revisado.', stamp()))
            self._audit(db, sid, 'cenario_salvo', {'case_id': case_id, 'version': version})
        return sid

    def list_scenarios(self):
        with closing(self.connect()) as db:
            return [dict(r) for r in db.execute('''
            SELECT s.id, s.case_id, s.version, s.created_at, c.title, c.hypothesis, c.owner,
                   d.status, d.revision
            FROM scenarios s JOIN cases c ON s.case_id=c.id
            JOIN decisions d ON d.scenario_id=s.id
            WHERE d.revision=(SELECT MAX(revision) FROM decisions WHERE scenario_id=s.id)
            ORDER BY s.created_at DESC''')]

    def load(self, scenario_id):
        with closing(self.connect()) as db:
            row = db.execute('SELECT * FROM scenarios WHERE id=?', (scenario_id,)).fetchone()
            if row is None:
                raise ValueError('Cenário não encontrado.')
            result = dict(row)
            if hashlib.sha256(result['payload'].encode()).hexdigest() != result['snapshot_hash']:
                raise ValueError('O registro foi alterado fora do sistema; integridade inválida.')
            result['snapshot'] = json.loads(result.pop('payload'))
            result['case'] = dict(db.execute('SELECT * FROM cases WHERE id=?', (row['case_id'],)).fetchone())
            result['decisions'] = [dict(r) for r in db.execute('SELECT * FROM decisions WHERE scenario_id=? ORDER BY revision', (scenario_id,))]
            result['plans'] = [dict(r) | {'payload': json.loads(r['payload'])} for r in db.execute('''SELECT p.* FROM experiment_plans p JOIN decisions d ON p.decision_id=d.id WHERE d.scenario_id=? ORDER BY d.revision''', (scenario_id,))]
            result['audit'] = [dict(r) for r in db.execute('SELECT * FROM audit_events WHERE entity_id IN (?,?) ORDER BY created_at', (scenario_id, row['case_id']))]
            return result

    def transition(self, scenario_id, status, reviewer, rationale, expected_revision, plan=None):
        reviewer, rationale = required(reviewer, 'revisor'), required(rationale, 'justificativa')
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            latest = db.execute('SELECT * FROM decisions WHERE scenario_id=? ORDER BY revision DESC LIMIT 1', (scenario_id,)).fetchone()
            if latest is None:
                raise ValueError('Cenário não encontrado.')
            if latest['revision'] != expected_revision:
                raise ValueError('Registro atualizado por outra sessão. Recarregue antes de decidir.')
            if status not in TRANSITIONS.get(latest['status'], []):
                raise ValueError('Transição de decisão não permitida.')
            if status == 'aprovado para teste':
                plan = {k: required((plan or {}).get(k), k) for k in PLAN_FIELDS}
            elif plan:
                raise ValueError('O plano formal é registrado ao aprovar para teste.')
            did = identifier()
            db.execute('INSERT INTO decisions VALUES (?,?,?,?,?,?,?)',
                       (did, scenario_id, latest['revision']+1, status, reviewer, rationale, stamp()))
            if plan:
                db.execute('INSERT INTO experiment_plans VALUES (?,?,?)', (identifier(), did, encode(plan)))
            self._audit(db, scenario_id, 'decisao_registrada', {'decision_id': did, 'status': status, 'reviewer': reviewer})
        return did


def export_markdown(record):
    s = record['snapshot']['scenario']
    v = s['valores']
    c = record['case']
    lines = [f"# {c['title']}", '', '**Registro local de decisão — não é resultado de experimento.**', '',
             f"Hipótese: {c['hypothesis']}", f"Responsável declarado: {c['owner']}",
             f"Cenário: {record['id']} · versão {record['version']}",
             f"Integridade do snapshot: {record['snapshot_hash']}", '', '## Recorte',
             '```json', json.dumps(s['escopo'], ensure_ascii=False, indent=2), '```', '',
             '## Cenário condicional', '```json', json.dumps(v, ensure_ascii=False, indent=2), '```', '',
             '## Premissas e limitações', *['- '+x for x in s['limitacoes']], '',
             '## Evidências', f"- Base: {record['snapshot']['baseline']['evidence_id']}",
             f"- Cenário: {s['evidence_id']}", f"- Contrato: {s['versao_contrato']} · cálculo: {s['versao_calculo']}",
             '```json', json.dumps(s['fontes_sha256'], indent=2), '```', '', '## Histórico de decisões']
    for d in record['decisions']:
        lines += [f"### {d['revision']} · {d['status']}", f"{d['created_at']} · {d['reviewer']}", d['rationale'], '']
    for p in record['plans']:
        lines += ['## Plano de validação'] + [f"- **{k}:** {v}" for k, v in p['payload'].items()]
    lines += ['', 'Identidades declaradas, sem autenticação. Aprovação para teste não comprova impacto.']
    return '\n'.join(lines)
