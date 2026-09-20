"""Descriptive investigation paths. No causal inference or opportunity scoring."""
from .core import MONEY, cash, ratio
from .presentation import eligible_scope


def marketplace_comparison(room, scope):
    """Keep all filters. Never silently remove the channel filter for a benchmark."""
    caveats = ['Comparação descritiva; não identifica causa operacional ou ganho recuperável.',
               'Outros canais são agregados pela receita, não pela média simples das margens.',
               'Fees, comissões e custos completos do canal não estão nesta conta.']
    if scope.population == 'A':
        caveats.append('Inclui não aprovados e devolvidos: valores registrados, não realização financeira.')
    if scope.channel is not None:
        return room.envelope('comparacao_marketplace', scope,
            {'disponivel': False, 'motivo': 'O filtro seleciona um único canal. Remova esse filtro para comparar Marketplace aos demais canais.'}, caveats)
    d = room.select(scope)
    mp = d.canal.eq('Marketplace')
    if not mp.any() or not (~mp).any():
        return room.envelope('comparacao_marketplace', scope,
            {'disponivel': False, 'motivo': 'Não há pedidos dos dois grupos neste recorte. Amplie o período ou reveja os filtros.'}, caveats)
    groups = []
    for name, group in [('Marketplace', d[mp]), ('Demais canais', d[~mp])]:
        totals = {c: int(group[c+'_centavos'].sum()) for c in MONEY}
        net = totals['receita_liquida']
        groups.append({'grupo': name, 'pedidos': len(group),
            **{c: cash(v) for c,v in totals.items()},
            'mc_pct': ratio(totals['margem_contribuicao'], net),
            'frete_pct': ratio(totals['custo_frete'], net),
            'produto_pct': ratio(totals['custo_produto'], net)})
    available = all(g['mc_pct'] is not None for g in groups)
    values = {'disponivel': available, 'grupos': groups,
              'motivo': '' if available else 'Receita líquida zero em um grupo: comparação percentual indisponível.'}
    if available:
        values.update(gap_mc_pp=groups[0]['mc_pct']-groups[1]['mc_pct'],
                      gap_frete_pp=groups[0]['frete_pct']-groups[1]['frete_pct'])
    return room.envelope('comparacao_marketplace', scope, values, caveats)


def discount_candidate(room, scope):
    """Candidate for testing, not a claim that discounts should be eliminated."""
    return room.metrics(eligible_scope(scope))
