"""Cálculos determinísticos. Sem chamadas de IA, gravações ou decisões comerciais."""
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import hashlib
import json
import math
import pandas as pd

VERSION = "1.0.0"
MONEY = ["receita_bruta", "desconto_reais", "receita_liquida", "custo_produto", "custo_frete", "margem_contribuicao"]
DIMENSIONS = {"canal", "categoria", "metodo_pagamento", "mes", "com_desc", "com_frete", "faixa_ticket"}

def cents(value):
    d = Decimal(str(value))
    if not d.is_finite():
        raise ValueError("Valor financeiro não finito")
    return int((d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

def cash(value):
    return float(Decimal(int(value)) / 100)

def ratio(numerator, denominator):
    return None if denominator == 0 else float(100 * numerator / denominator)

def locate_root(start=None):
    p = Path(start or Path.cwd()).resolve()
    for candidate in [p, *p.parents]:
        if (candidate / "data-room/vendas.csv").is_file():
            return candidate
    raise FileNotFoundError("Não foi encontrada a pasta data-room")

@dataclass(frozen=True)
class Scope:
    start: str = "2023-01-01"
    end: str = "2023-12-31"
    population: str = "B"
    channel: str | None = None
    category: str | None = None
    ticket_lt: float | None = None
    discounted_only: bool = False

    def __post_init__(self):
        start, end = pd.Timestamp(self.start), pd.Timestamp(self.end)
        if pd.isna(start) or pd.isna(end) or start != start.normalize() or end != end.normalize() or start > end:
            raise ValueError("Período deve conter datas válidas, sem horário, início <= fim")
        if self.population not in {"A", "B"}:
            raise ValueError("População deve ser A ou B")
        if self.ticket_lt is not None and (not math.isfinite(self.ticket_lt) or self.ticket_lt <= 0):
            raise ValueError("Limite de ticket deve ser positivo e finito")
        if not isinstance(self.discounted_only, bool):
            raise ValueError("discounted_only deve ser booleano")

class DataRoom:
    def __init__(self, root=None):
        self.root = locate_root(root)
        sources = [self.root / "data-room" / f"{name}.csv" for name in ["vendas", "atendimento"]]
        self.source_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
        self.contract = json.loads((Path(__file__).parent / "contratos/metricas.json").read_text())
        self.contract_hash = hashlib.sha256(json.dumps(self.contract, sort_keys=True).encode()).hexdigest()
        v, a = [pd.read_csv(p, encoding="utf-8-sig") for p in sources]
        # Known truncated final record: identifiers exist but the entire financial tail is absent.
        tail = ["quantidade", "preco_unitario", *MONEY, "metodo_pagamento", "status_pagamento", "tempo_entrega_real", "devolvido", "motivo_devolucao"]
        blank_v = v.order_id.eq("ORD-072219") & v[tail].isna().all(axis=1)
        blank_a = a.drop(columns="ticket_id").isna().all(axis=1)
        self.removed = {"vendas": int(blank_v.sum()), "atendimento": int(blank_a.sum())}
        v, a = v.loc[~blank_v].copy(), a.loc[~blank_a].copy()
        required = ["order_id", "customer_id", "sku_id", "data_pedido", "status_pagamento", "devolvido", "quantidade", "preco_unitario", *MONEY]
        if v[required].isna().any().any() or v.order_id.duplicated().any():
            raise ValueError("Vendas: campos obrigatórios ausentes ou order_id duplicado")
        ar = ["ticket_id", "order_id", "customer_id", "data_abertura", "custo_operacional_ticket"]
        if a[ar].isna().any().any() or a.ticket_id.duplicated().any():
            raise ValueError("Atendimento: campos obrigatórios ausentes ou ticket_id duplicado")
        boolean = v.devolvido.astype(str).str.lower()
        if not boolean.isin(["true", "false"]).all():
            raise ValueError("devolvido contém valor desconhecido")
        if not v.status_pagamento.isin(["Aprovado", "Cancelado", "Aguardando"]).all():
            raise ValueError("status_pagamento desconhecido")
        v["devolvido"] = boolean.eq("true")
        v["aprovado"] = v.status_pagamento.eq("Aprovado")
        v["dt"] = pd.to_datetime(v.data_pedido, errors="raise")
        a["dt_ticket"] = pd.to_datetime(a.data_abertura, errors="raise")
        for col in MONEY:
            v[col + "_centavos"] = v[col].map(cents)
        a["custo_at_centavos"] = a.custo_operacional_ticket.map(cents)
        if (a.custo_at_centavos < 0).any():
            raise ValueError("Custo registrado de atendimento negativo")
        for col in MONEY[:-1]:
            if (v[col + "_centavos"] < 0).any():
                raise ValueError(f"Valor negativo não previsto: {col}")
        if (v.desconto_reais_centavos > v.receita_bruta_centavos).any():
            raise ValueError("Desconto superior à receita bruta")
        if (v.quantidade <= 0).any() or (v.quantidade % 1 != 0).any():
            raise ValueError("Quantidade deve ser inteira e positiva")
        residuals = {
            "receita_bruta": v.receita_bruta_centavos - (v.quantidade * v.preco_unitario).map(cents),
            "receita_liquida": v.receita_liquida_centavos - (v.receita_bruta_centavos-v.desconto_reais_centavos),
            "mc": v.margem_contribuicao_centavos - (v.receita_liquida_centavos-v.custo_produto_centavos-v.custo_frete_centavos),
        }
        self.identity_residual_cents = {k: int(s.abs().max()) for k, s in residuals.items()}
        if any(x > 1 for x in self.identity_residual_cents.values()):
            raise ValueError("Identidade financeira não fecha com tolerância de um centavo")
        v["mes"] = v.dt.dt.to_period("M").astype(str)
        v["com_desc"] = v.desconto_reais_centavos.gt(0)
        v["com_frete"] = v.custo_frete_centavos.gt(0)
        v["faixa_ticket"] = pd.cut(v.receita_liquida, [-float("inf"),100,250,500,1000,float("inf")], labels=["até 100", "(100,250]", "(250,500]", "(500,1000]", ">1000"]).astype(str)
        pairs = a.merge(v[["order_id", "customer_id", "dt"]], on="order_id", how="left", suffixes=("_ticket", "_pedido"), validate="many_to_one", indicator=True)
        match = pairs._merge.eq("both")
        same = pairs.customer_id_ticket.eq(pairs.customer_id_pedido)
        chrono = pairs.dt_ticket.ge(pairs.dt)
        self.quality = {"tickets_validos": len(a), "pedidos_validos": len(v), "tickets_sem_pedido": int((~match).sum()), "tickets_cliente_divergente": int((match & ~same).sum()), "tickets_anteriores_pedido": int((match & ~chrono).sum())}
        self.tickets = a
        self.linked = pairs.loc[match & same & chrono].copy()
        # One row per order: aggregate the many tickets BEFORE enriching sales.
        costs = self.linked.groupby("order_id").agg(tickets_vinculados=("ticket_id", "size"), atendimento_vinculado_centavos=("custo_at_centavos", "sum"))
        self.orders = v.merge(costs, on="order_id", how="left", validate="one_to_one")
        self.orders["tem_vinculo_atendimento"] = self.orders.tickets_vinculados.notna()
        # Missing monetary value is retained as null. No link does not prove zero cost.
        self.orders["tickets_vinculados"] = self.orders.tickets_vinculados.fillna(0).astype(int)

    def select(self, scope=Scope()):
        d = self.orders
        if pd.Timestamp(scope.start) < d.dt.min().normalize() or pd.Timestamp(scope.end) > d.dt.max().normalize():
            raise ValueError("Janela solicitada excede a cobertura de Vendas")
        if scope.channel is not None and scope.channel not in set(d.canal):
            raise ValueError("Canal desconhecido")
        if scope.category is not None and scope.category not in set(d.categoria):
            raise ValueError("Categoria desconhecida")
        mask = d.dt.ge(scope.start) & d.dt.lt(pd.Timestamp(scope.end)+pd.Timedelta(days=1))
        if scope.population == "B": mask &= d.aprovado & ~d.devolvido
        if scope.channel is not None: mask &= d.canal.eq(scope.channel)
        if scope.category is not None: mask &= d.categoria.eq(scope.category)
        if scope.ticket_lt is not None: mask &= d.receita_liquida_centavos.lt(cents(scope.ticket_lt))
        if scope.discounted_only: mask &= d.com_desc
        return d.loc[mask].copy()

    def envelope(self, kind, scope, values, caveats=None):
        result = {"tipo": kind, "versao_calculo": VERSION, "versao_contrato": self.contract["version"], "hash_contrato": self.contract_hash, "fontes_sha256": self.source_hashes, "escopo": asdict(scope), "valores": values, "limitacoes": caveats or []}
        result["evidence_id"] = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()[:20]
        return result

    def metrics(self, scope=Scope()):
        d = self.select(scope)
        total = {c: int(d[c+"_centavos"].sum()) for c in MONEY}
        b = d.aprovado & ~d.devolvido
        linked_cost = int(d.atendimento_vinculado_centavos.sum())
        at = self.linked[self.linked.order_id.isin(d.order_id)]
        values = {"pedidos": len(d), **{c: cash(n) for c,n in total.items()}, "mc_pct": ratio(total["margem_contribuicao"], total["receita_liquida"]), "desconto_pct_bruta": ratio(total["desconto_reais"], total["receita_bruta"]), "pedidos_B_no_recorte": int(b.sum()), "participacao_B_pct": ratio(int(b.sum()),len(d)), "pedidos_com_atendimento": int(d.tem_vinculo_atendimento.sum()), "tickets_vinculados": int(d.tickets_vinculados.sum()), "cobertura_atendimento_pct": ratio(int(d.tem_vinculo_atendimento.sum()),len(d)), "atendimento_vinculado_registrado": cash(linked_cost), "custo_vinculado_por_pedido_populacao": None if d.empty else cash(linked_cost)/len(d), "janela_tickets_vinculados": None if at.empty else [str(at.dt_ticket.min()),str(at.dt_ticket.max())]}
        caveats = ["MC observável não é lucro ou rentabilidade completa.", "Atendimento é custo padronizado; acompanha pedidos da janela selecionada com tickets disponíveis até 2025.", "Sem vínculo de Atendimento não significa custo real zero.", "Frete já está deduzido na MC. Não deduzir novamente."]
        if scope.population == "A": caveats.append("População A inclui cancelados e devolvidos: valores registrados, não realização financeira.")
        if scope.end.startswith("2024-01"): caveats.append("Janeiro/2024 é parcial; não comparar com mês completo como se tivesse a mesma cobertura.")
        return self.envelope("observacao", scope, values, caveats)

    def breakdown(self, dimension, scope=Scope()):
        if dimension not in DIMENSIONS: raise ValueError("Dimensão não autorizada")
        d = self.select(scope)
        rows=[]
        for key,g in d.groupby(dimension, observed=True):
            sums={c:int(g[c+"_centavos"].sum()) for c in MONEY}
            rows.append({"grupo":str(key), "pedidos":len(g), **{c:cash(n) for c,n in sums.items()}, "mc_pct":ratio(sums["margem_contribuicao"],sums["receita_liquida"])})
        return self.envelope("decomposicao_descritiva",scope,{"dimensao":dimension,"grupos":rows},["Comparação contábil; não identifica causalidade nem parcela recuperável.", "MC% é razão de totais, não média simples dos percentuais."])

    def funnel(self, scope=Scope(population="A")):
        if scope.population != "A": raise ValueError("Funil exige população A como denominador")
        d=self.select(scope); groups={"nao_aprovados":~d.aprovado,"aprovados_devolvidos":d.aprovado & d.devolvido,"aprovados_sem_devolucao":d.aprovado & ~d.devolvido}
        values={k:{"pedidos":int(mask.sum()),"pct_pedidos":ratio(int(mask.sum()),len(d)),"mc_registrada":cash(d.loc[mask,"margem_contribuicao_centavos"].sum())} for k,mask in groups.items()}
        values["total_pedidos"]=len(d)
        return self.envelope("status_pedidos",scope,values,["Grupos mutuamente exclusivos. MC fora de B não é perda realizada.","Não subtrair MC de devolvidos de B nem calcular MC realizada com estas bases."])

    def simulate_discount(self, scope=Scope(ticket_lt=250, discounted_only=True), removal_fraction=1.0, retention=1.0):
        if scope.population != "B": raise ValueError("Simulação inicial exige população B")
        for value in [removal_fraction,retention]:
            if isinstance(value,bool) or not math.isfinite(value) or not 0 <= value <= 1: raise ValueError("Premissas devem estar entre 0 e 1")
        d=self.select(scope)
        reductions=d.desconto_reais_centavos.map(lambda x:int((Decimal(int(x))*Decimal(str(removal_fraction))).quantize(Decimal("1"),rounding=ROUND_HALF_UP)))
        # Freeze eligible historical order IDs before changing any price.
        m=int(d.margem_contribuicao_centavos.sum()); delta=int(reductions.sum()); full=m+delta
        scenario=int((Decimal(full)*Decimal(str(retention))).quantize(Decimal("1"),rounding=ROUND_HALF_UP))
        breakeven=(m/full) if len(d) and m>0 and full>0 else None
        changed=int((reductions>0).sum())
        values={"pedidos_elegiveis":len(d),"pedidos_com_alteracao":changed,"mc_base":cash(m),"reducao_desconto_se_todos_retidos":cash(delta),"mc_com_retencao_integral":cash(full),"mc_cenario":cash(scenario),"delta_mc_cenario":cash(scenario-m),"retencao_equilibrio":breakeven,"retencao_assumida":retention,"fracao_desconto_removida":removal_fraction,"pedidos_esperados_sob_premissa":len(d)*retention,"status": "sem_populacao" if d.empty else "sem_alteracao" if changed==0 else "cenario_condicional", "guardrails": {"mc_agregada_cenario_negativa": scenario<0,"pedidos_com_mc_negativa_se_retidos":int(((d.margem_contribuicao_centavos+reductions)<0).sum()),"limites_comerciais":"pendentes de definição humana"}, "formula":"MC_cenario = retencao * (MC_base + reducao_desconto); equilibrio = MC_base/(MC_base+reducao_desconto) quando MC_base>0"}
        return self.envelope("cenario_condicional",scope,values,["Retenção uniforme e mix constante são premissas, não previsão nem conversão observada.","Quantidade, custo de produto e frete por pedido retido permanecem constantes. Custo de Atendimento não está nesta simulação.","Cruzamento de R$250 não elimina frete; política operacional não confirmada.","Não inclui custos adicionais de implementação, aquisição, recompra ou efeitos de longo prazo.","Se MC base não é positiva, a régua usual de retenção não é aplicável; requer outra análise."])

    def simulate_freight(self, scope=Scope(), reduction_fraction=0.1, retention=1.0):
        """Conditional cost reduction on each order's observed freight; frozen membership."""
        if scope.population != "B": raise ValueError("Simulação de frete exige população B")
        for value in [reduction_fraction, retention]:
            if isinstance(value, bool) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("Premissas devem estar entre 0 e 1")
        d = self.select(scope)
        reductions = d.custo_frete_centavos.map(lambda x: int(
            (Decimal(int(x))*Decimal(str(reduction_fraction))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)))
        m = int(d.margem_contribuicao_centavos.sum())
        delta = int(reductions.sum()); full = m + delta
        scenario = int((Decimal(full)*Decimal(str(retention))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        values = {
            "intervencao": "frete", "pedidos_elegiveis": len(d),
            "pedidos_com_frete_registrado": int(d.com_frete.sum()),
            "pedidos_com_alteracao": int(reductions.gt(0).sum()),
            "frete_base": cash(d.custo_frete_centavos.sum()), "mc_base": cash(m),
            "reducao_frete_se_todos_retidos": cash(delta),
            "fracao_frete_reduzida": reduction_fraction,
            "mc_com_retencao_integral": cash(full), "mc_cenario": cash(scenario),
            "delta_mc_cenario": cash(scenario-m), "retencao_assumida": retention,
            "retencao_equilibrio": m/full if len(d) and m>0 and full>0 else None,
            "pedidos_esperados_sob_premissa": len(d)*retention,
            "status": "sem_populacao" if d.empty else "sem_alteracao" if not reductions.gt(0).any() else "cenario_condicional",
            "guardrails": {"mc_agregada_cenario_negativa": scenario<0,
                "pedidos_com_mc_negativa_se_retidos": int((d.margem_contribuicao_centavos+reductions).lt(0).sum()),
                "limites_comerciais": "pendentes de definição humana"},
            "formula": "MC_cenario = retencao * (MC_base + reducao_frete); reducao por pedido = frete registrado * fracao; equilibrio = MC_base/(MC_base+reducao_frete) quando MC_base>0",
        }
        return self.envelope("cenario_condicional", scope, values, [
            "Redução do custo de frete é hipotética: viabilidade operacional e parcela negociável não comprovadas.",
            "Usa o custo de frete registrado de cada pedido. Pedidos com frete zero permanecem no recorte, sem benefício de frete.",
            "Retenção uniforme e mix constante são premissas, não previsão. A retenção se aplica a todo o recorte congelado, inclusive pedidos com frete zero.",
            "Receita, desconto, unidades e custo de produto por pedido retido permanecem constantes. Cruzar R$250 não gera economia automática.",
            "Não modela prazo, qualidade logística, devoluções, Atendimento, aquisição ou custos de implementação. Validar SLA e experiência antes de testar.",
            "Resultado é variação condicional de MC sobre o recorte histórico, não saving comprovado ou ganho anual.",
            "Se MC base não é positiva, a régua usual de retenção não é aplicável; requer outra análise.",
        ])

    def stratified(self, dimension, control, scope=Scope()):
        if dimension not in DIMENSIONS or control not in DIMENSIONS or dimension==control: raise ValueError("Dimensões inválidas")
        d=self.select(scope); rows=[]
        for (a,b),g in d.groupby([dimension,control], observed=True):
            rows.append({"grupo":str(a),"estrato":str(b),"pedidos":len(g),"mc_pct":ratio(int(g.margem_contribuicao_centavos.sum()),int(g.receita_liquida_centavos.sum()))})
        groups=set(d[dimension].astype(str)); support={str(k): sorted(groups-set(g[dimension].astype(str))) for k,g in d.groupby(control,observed=True)}
        return self.envelope("comparacao_estratificada",scope,{"grupos":rows,"grupos_ausentes_por_estrato":support},["Não é teste de causalidade. Sobrevivência ou desaparecimento de diferença não prova causa.","Ausência de grupos em estratos limita a comparação; não implica que duas variáveis sejam idênticas."])

def combine_component_changes(baseline, actions):
    """Combine explicit per-order COMPONENT deltas. Same-component collisions are refused.

    baseline: {order_id: contribution_cents}; actions: {name:{order_id:{component:delta_cents}}}.
    This is conditional arithmetic only, not behavioural or causal impact estimation.
    """
    allowed={"receita_bruta","desconto_reais","custo_produto","custo_frete"}
    seen=set(); usage={}; result=dict(baseline)
    if any(type(n) is not int for n in baseline.values()): raise ValueError("Use centavos inteiros")
    for name,orders in actions.items():
        for oid,changes in orders.items():
            if oid not in baseline: raise ValueError("Pedido não pertence à população congelada")
            usage.setdefault(oid,set()).add(name)
            for component,delta in changes.items():
                if component not in allowed or type(delta) is not int: raise ValueError("Componente/delta inválido")
                if (oid,component) in seen: raise ValueError("Duas alterações do mesmo componente exigem cenário conjunto explícito")
                seen.add((oid,component))
                result[oid] += delta if component=="receita_bruta" else -delta
    return {"mc_final_centavos_por_pedido":result,"delta_total_centavos":sum(result.values())-sum(baseline.values()),"pedidos_sobrepostos":sorted(k for k,v in usage.items() if len(v)>1),"classificacao":"aritmetica_condicional; efeitos comportamentais não modelados"}
