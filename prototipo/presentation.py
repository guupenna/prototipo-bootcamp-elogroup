"""Presentation adapters. Financial answers always come from the governed core."""
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from .core import Scope


def brl(value):
    if value is None:
        return 'Indisponível'
    return 'R$ ' + f'{value:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def number(value, digits=0):
    if value is None:
        return '—'
    return f'{value:,.{digits}f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def percent(value):
    return 'Indisponível' if value is None else number(value, 2) + '%'


def scope_label(scope):
    return f'{scope.start} → {scope.end} · população {scope.population} · {scope.channel or "todos os canais"} · {scope.category or "todas as categorias"}'


def context_key(scope):
    return hashlib.sha256(json.dumps(asdict(scope), sort_keys=True).encode()).hexdigest()[:16]


def eligible_scope(scope):
    return replace(scope, population='B', ticket_lt=min(scope.ticket_lt or 250, 250), discounted_only=True)


def calculate_scenario(room, scope, fraction, retention, intervention='desconto'):
    if intervention == 'desconto':
        return room.simulate_discount(scope, fraction, retention)
    if intervention == 'frete':
        return room.simulate_freight(scope, fraction, retention)
    raise ValueError('Intervenção não autorizada')


def scenario_description(e):
    v = e['valores']
    action = ('Redução hipotética de '+percent(v['fracao_frete_reduzida']*100)+' do custo de frete registrado'
              if v.get('intervencao')=='frete' else 'Retirada de '+percent(v['fracao_desconto_removida']*100)+' do desconto')
    return action+' · retenção hipotética: '+percent(v['retencao_assumida']*100)


def sensitivity(room, scope, removal_fraction, intervention='desconto'):
    """No independent financial formula in the UI."""
    rows = []
    for step in range(0, 101, 5):
        v = calculate_scenario(room, scope, removal_fraction, step/100, intervention)['valores']
        rows.append({'Retenção hipotética (%)': step, 'MC simulada (R$)': v['mc_cenario'], 'Variação da MC (R$)': v['delta_mc_cenario']})
    return rows


def snapshot(room, scope, removal_fraction, retention, intervention='desconto'):
    return {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'baseline': room.metrics(scope),
        'scenario': calculate_scenario(room, scope, removal_fraction, retention, intervention),
        'order_ids': sorted(room.select(scope).order_id.tolist()),
    }


def deterministic_brief(evidences):
    """Useful offline fallback, explicitly not AI or a replay."""
    parts = ['## Resumo calculado — sem IA', '', 'Texto padronizado gerado a partir do núcleo de cálculo. Não é uma resposta de modelo.']
    for e in evidences:
        v = e['valores']; ref = e['evidence_id']
        parts += ['', f"### Evidência {ref}", f"Recorte: {scope_label(Scope(**e['escopo']))}"]
        if e['tipo'] == 'observacao':
            parts += [f"{number(v['pedidos'])} pedidos; receita líquida registrada {brl(v['receita_liquida'])}; MC observável {brl(v['margem_contribuicao'])} ({percent(v['mc_pct'])})."]
        elif e['tipo'] == 'cenario_condicional':
            parts += [scenario_description(e)+f". MC simulada: {brl(v['mc_cenario'])}; variação: {brl(v['delta_mc_cenario'])}.",
                      'Retenção de equilíbrio: '+(percent(v['retencao_equilibrio']*100) if v['retencao_equilibrio'] is not None else 'não aplicável')+'.']
        parts += ['**Limitações:**'] + ['- '+x for x in e['limitacoes']]
    parts += ['', '## Próximo passo', 'Revisar premissas e definir uma hipótese e critérios de teste. Nenhuma política foi alterada.']
    return '\n'.join(parts)


def scope_description(scope):
    """Business-facing description without exposing parameter dictionaries."""
    start = datetime.fromisoformat(scope.start).strftime('%d/%m/%Y')
    end = datetime.fromisoformat(scope.end).strftime('%d/%m/%Y')
    population = 'aprovados e sem devolução registrada (B)' if scope.population=='B' else 'todos os status, incluindo não aprovados e devolvidos (A)'
    rows = [('Período dos pedidos', f'{start} a {end}'), ('Pedidos considerados', population),
            ('Canal', scope.channel or 'Todos'), ('Categoria', scope.category or 'Todas'),
            ('Valor dos pedidos', 'Receita líquida histórica abaixo de '+brl(scope.ticket_lt) if scope.ticket_lt else 'Sem limite de valor'),
            ('Desconto', 'Somente pedidos com desconto' if scope.discounted_only else 'Com ou sem desconto')]
    return rows


def evidence_explanation(e):
    """Short explanations for all evidence types returned by the governed tools."""
    kind = e['tipo']
    if kind=='cenario_condicional' and e['valores'].get('intervencao')=='frete':
        return ('Simulação de custo de frete', 'Reduzimos a porcentagem escolhida do frete registrado de cada pedido, com arredondamento por pedido. Acrescentamos essa redução à MC e aplicamos a retenção hipotética a todo o recorte. Frete zero não gera benefício. Viabilidade operacional e impacto no serviço precisam ser validados.')
    explanations = {
        'observacao': ('Indicadores do grupo selecionado',
            'Somamos os valores dos pedidos selecionados. A margem de contribuição (MC) é a receita líquida menos produto e frete. MC% é a MC total dividida pela receita líquida total.'),
        'decomposicao_descritiva': ('Comparação entre grupos',
            'Separamos os pedidos pela dimensão escolhida e somamos os valores em cada grupo. O percentual de margem é calculado a partir dos totais de cada grupo.'),
        'status_pedidos': ('Situação dos pedidos',
            'Contamos todos os pedidos do período e dos filtros, inclusive não aprovados e devolvidos. Cada pedido aparece em apenas uma situação. Os percentuais usam esse total como denominador.'),
        'cenario_condicional': ('Simulação de desconto',
            'Somamos à MC histórica o desconto que seria retirado. Depois aplicamos a retenção hipotética. O equilíbrio é a parcela que precisaria permanecer para preservar a MC histórica, se o perfil dos pedidos e os custos por pedido forem mantidos.'),
        'comparacao_estratificada': ('Comparação dentro de grupos semelhantes',
            'Comparamos a MC% separadamente em cada grupo de controle. Isso ajuda a observar diferenças de composição, mas não demonstra causalidade.'),
        'comparacao_marketplace': ('Marketplace versus os demais canais',
            'Agrupamos os pedidos em Marketplace e demais canais, mantendo os filtros. Em cada grupo, dividimos a MC, o produto e o frete pela receita líquida total. Uma diferença em pontos percentuais é a subtração entre esses percentuais.'),
    }
    return explanations.get(kind, ('Resultado da análise', 'O resultado foi produzido pelas funções autorizadas, respeitando o recorte abaixo.'))


def comparison_total(room, scope):
    """Company total in the same date window and population; no segment filters."""
    return room.metrics(replace(scope, channel=None, category=None, ticket_lt=None, discounted_only=False))
