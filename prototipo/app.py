"""Run from the project root: python -m streamlit run prototipo/app.py"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dataclasses import asdict, replace
from datetime import date
import hashlib
import html
import json
import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from prototipo.core import DataRoom, Scope
from prototipo.presentation import brl, number, percent, scope_label, context_key, eligible_scope, sensitivity, snapshot, deterministic_brief, scope_description, evidence_explanation, calculate_scenario, scenario_description, comparison_total
from prototipo.workflow import DecisionStore, TRANSITIONS, PLAN_FIELDS, export_markdown
from prototipo.ai_service import configuration, run_investigation
from prototipo.investigation import marketplace_comparison, discount_candidate

st.set_page_config(page_title='Vértice | Profitability Decision System', page_icon='◭', layout='wide')
PAGES = ['01 · Control Tower', '02 · Investigar', '03 · Simular', '04 · Copilot', '05 · Decisões']
NAVY, TEAL, AMBER, RED = '#24382F', '#42634D', '#B28339', '#AD5147'
st.markdown("""<style>
/* Local system fonts: no remote assets or requests. */
:root {--ink:#24382F; --muted:#687269; --line:#DADDD4; --paper:#F8F7F2;}
.stApp {background:var(--paper); color:var(--ink);}
.block-container {padding:1.25rem 3rem 4rem; max-width:1440px;}
[data-testid="stHeader"] {background:transparent;}
[data-testid="stToolbar"], [data-testid="stStatusWidget"], #MainMenu {display:none !important;}
h1 {font-family:Georgia,'Times New Roman',serif !important; font-size:clamp(2.5rem,3vw,3.5rem) !important; font-weight:400 !important; letter-spacing:-.045em !important; line-height:1.08 !important; padding-bottom:.75rem !important; color:var(--ink);}
h2,h3 {font-weight:500 !important; letter-spacing:-.025em !important; color:var(--ink);}
h3 {font-size:1.15rem !important;}
[data-testid="stCaptionContainer"] {color:var(--muted);}
[data-testid="stSidebar"] {background:#ECEEE6; border-right:1px solid var(--line);}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {padding-top:0;}
[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {height:0 !important;min-height:0 !important;margin-bottom:0 !important;position:relative;z-index:2;}
[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] {position:absolute;top:1.15rem;right:0;}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"],
[data-testid="stSidebar"] .block-container {padding-top:1.25rem !important;padding-bottom:2rem !important;}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > [data-testid="stVerticalBlock"] {gap:.85rem;}
.brand {display:flex;align-items:center;gap:12px;padding:8px 0 2px;}
.brand-mark {width:28px;height:32px;border-left:3px solid #42634D;border-bottom:3px solid #42634D;transform:skew(-18deg);position:relative;margin-left:6px;}
.brand-mark:after {content:'';position:absolute;left:8px;top:0;height:24px;border-left:3px solid #B28339;}
.brand-name {font-family:Georgia,serif;font-size:2rem;letter-spacing:-.06em;}
.brand-sub {font-size:.66rem;letter-spacing:.15em;text-transform:uppercase;color:#59655A;margin:0 0 1.1rem 46px;}
[data-testid="stSidebar"] [role="radiogroup"] {gap:.3rem;}
[data-testid="stSidebar"] [role="radiogroup"] label {min-height:42px;padding:8px 10px;border-radius:4px;transition:background .15s;}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {background:#DCE3D7;box-shadow:inset 3px 0 #42634D;}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {background:#E1E6DB;}
[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(hr) {margin:.5rem 0 .35rem;}
[data-testid="stSidebar"] hr {margin:0;}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {margin-bottom:0;}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {margin-bottom:.35rem;}
[data-testid="stMetric"] {background:transparent;border:0;border-top:1px solid var(--line);border-radius:0;padding:18px 0 22px;}
[data-testid="stMetricValue"] {font-size:clamp(1.05rem,1.75vw,1.8rem);font-weight:500;font-variant-numeric:tabular-nums;letter-spacing:-.04em;color:var(--ink);}
[data-testid="stMetricLabel"] p {white-space:normal;font-size:.78rem;color:#586359;}
.kpi-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin:0 0 .65rem;}
.kpi-card {min-width:0;min-height:142px;display:flex;flex-direction:column;padding:18px 20px 16px;background:#FCFBF7;border:1px solid var(--line);border-top:2px solid #42634D;border-radius:6px;box-shadow:0 1px 2px rgba(36,56,47,.035);}
.kpi-label {display:flex;align-items:center;gap:6px;min-height:19px;font-size:.75rem;line-height:1.35;color:#687269;}
.kpi-help {display:inline-flex;align-items:center;justify-content:center;flex:0 0 15px;width:15px;height:15px;border:1px solid #98A198;border-radius:50%;font-size:.6rem;font-weight:600;color:#758076;cursor:help;}
.kpi-value {margin:12px 0 0;font-size:clamp(1.35rem,2vw,2rem);font-weight:500;font-variant-numeric:tabular-nums;letter-spacing:-.045em;line-height:1.12;color:var(--ink);overflow-wrap:anywhere;}
.kpi-card.has-comparison .kpi-value {margin-bottom:14px;}
.kpi-total {margin-top:auto;padding-top:10px;border-top:1px solid #E6E8E1;font-size:.72rem;line-height:1.35;color:#7A827B;font-variant-numeric:tabular-nums;}
.kpi-total strong {font-weight:500;color:#59635B;}
.kpi-reference {display:flex;align-items:baseline;gap:.75rem;max-width:68rem;margin:.15rem 0 1.4rem;padding:.65rem .8rem;background:#F0F1EB;border-left:2px solid #AAB7A6;border-radius:0 4px 4px 0;color:#687269;font-size:.72rem;line-height:1.5;}
.kpi-reference-label {flex:0 0 auto;font-size:.62rem;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:#4F6655;}
.eyebrow {font-size:.65rem;letter-spacing:.18em;font-weight:600;color:#63745E;border-top:3px solid #42634D;padding-top:12px;margin-bottom:8px;}
.page-heading {margin:0 0 1rem;}
.page-heading h1 {margin:0 !important;padding:0 0 .6rem !important;border-bottom:2px solid #42634D;}
[data-testid="stVerticalBlockBorderWrapper"]>div {border-radius:3px !important;}
[data-testid="stExpander"] {background:transparent;border:0;border-top:1px solid var(--line);border-radius:0;}
[data-testid="stExpander"] summary {padding:14px 4px;}
[data-testid="stTabs"] [role="tablist"] {border-bottom:1px solid var(--line);gap:28px;}
[data-testid="stTabs"] [role="tab"] {padding:12px 2px 10px;font-size:.88rem;color:#687269;}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {color:var(--ink);font-weight:500;}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {height:2px;background:#42634D;}
[class*="st-key-panel_"] [data-testid="stVerticalBlockBorderWrapper"] > div {background:#FCFBF7;border:1px solid var(--line) !important;border-radius:6px !important;padding:1rem 1.1rem .7rem;box-shadow:0 1px 2px rgba(36,56,47,.025);}
.panel-title {font-size:1rem;font-weight:500;line-height:1.3;color:var(--ink);margin:.05rem 0 .35rem;}
.st-key-panel_monthly :is([data-testid="stButtonGroup"],[data-testid="stSegmentedControl"]) {margin:0;overflow-x:auto;overflow-y:hidden;border-bottom:1px solid #E1E4DC;scrollbar-width:none;}
.st-key-panel_monthly :is([data-testid="stButtonGroup"],[data-testid="stSegmentedControl"])::-webkit-scrollbar {display:none;}
.st-key-panel_monthly :is([data-testid="stButtonGroup"],[data-testid="stSegmentedControl"]) [role="group"] {display:flex;min-width:max-content;background:transparent;border:0;}
.st-key-panel_monthly :is([data-testid="stButtonGroup"],[data-testid="stSegmentedControl"]) button {position:relative;min-height:36px;margin:0 16px 0 0 !important;padding:5px 4px 10px !important;background:transparent !important;border:0 !important;border-radius:0 !important;box-shadow:none !important;color:#687269 !important;font-size:.78rem;font-weight:400;white-space:nowrap;}
.st-key-panel_monthly :is([data-testid="stButtonGroup"],[data-testid="stSegmentedControl"]) button:last-child {margin-right:0 !important;}
.st-key-panel_monthly :is([data-testid="stButtonGroup"],[data-testid="stSegmentedControl"]) button:hover {color:#3F5C48 !important;}
.st-key-panel_monthly :is([data-testid="stButtonGroup"],[data-testid="stSegmentedControl"]) button:is([aria-pressed="true"],[aria-checked="true"],[data-active="true"],[data-selected="true"]) {color:#24382F !important;font-weight:500;}
.st-key-panel_monthly :is([data-testid="stButtonGroup"],[data-testid="stSegmentedControl"]) button:is([aria-pressed="true"],[aria-checked="true"],[data-active="true"],[data-selected="true"])::after {content:'';position:absolute;right:0;bottom:-1px;left:0;height:2px;background:#42634D;}
.st-key-panel_monthly :is([data-testid="stButtonGroup"],[data-testid="stSegmentedControl"]) button:focus-visible {outline:2px solid rgba(66,99,77,.42) !important;outline-offset:-2px;border-radius:2px !important;}
[class*="st-key-panel_"] [data-testid="stPlotlyChart"] {margin-top:-.2rem;}
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button {border-radius:4px;font-size:.85rem;min-height:40px;box-shadow:none;}
[data-testid="stButton"] button[kind="secondary"] {background:transparent;border-color:#B9C4B4;}
[data-testid="stButton"] button:hover {border-color:#42634D;}
[data-testid="stAlert"] {border-radius:3px;}
[data-testid="stForm"] {border-radius:3px;border-color:var(--line);}
hr {border-color:var(--line);}
@media (max-width:700px) {
 .block-container {padding:1.25rem 1.2rem 3rem;}
 .kpi-grid {grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;}
 .kpi-card {min-height:132px;padding:15px 14px 13px;}
 .kpi-value {font-size:1.25rem;}
 .kpi-reference {align-items:flex-start;flex-direction:column;gap:.2rem;}
 .st-key-overview_kpis [data-testid="stHorizontalBlock"] {flex-wrap:wrap !important;gap:.8rem;}
 .st-key-overview_kpis [data-testid="stColumn"] {width:calc(50% - .8rem) !important;flex:1 1 calc(50% - .8rem) !important;min-width:0 !important;}
 [data-testid="stMetricValue"] {font-size:1.18rem;}
}
</style>""", unsafe_allow_html=True)


@st.cache_resource
def load_room(signature):
    return DataRoom(ROOT)


def navigate(page, **changes):
    st.session_state['page'] = PAGES[page]
    for key, value in changes.items():
        st.session_state[key] = value


def select_eligible():
    limit = st.session_state.get('ticket_limit', 250.0) if st.session_state.get('limit_ticket') else 250.0
    st.session_state.update(population='B', limit_ticket=True, ticket_limit=min(limit, 250.0), discount_only=True)


def apply_eligible():
    st.session_state['simulation_kind'] = 'desconto'
    select_eligible()
    st.session_state['investigation_topic'] = 'discount'
    navigate(2)


def open_simulation(intervention):
    st.session_state['simulation_kind'] = intervention
    navigate(2)


def apply_freight_population():
    st.session_state['population'] = 'B'


def begin_investigation(topic, all_channels=False):
    st.session_state['investigation_topic'] = topic
    st.session_state['analysis_view'] = 'Marketplace' if topic == 'marketplace' else 'Composição da margem'
    if topic == 'discount':
        select_eligible()
    if all_channels:
        st.session_state['channel'] = 'Todos'
    navigate(1)


def explain_investigation(topic):
    questions = {
        'discount': 'Explique a contribuição deste grupo e o que precisamos considerar antes de testar uma mudança de desconto. Não trate desconto registrado como economia garantida.',
        'marketplace': 'Compare a margem e os componentes de Marketplace e demais canais neste recorte. Use uma comparação ponderada pela receita e separe a diferença contábil de uma causa operacional.',
    }
    st.session_state.pop('copilot_question', None)
    st.session_state['suggested_question'] = questions.get(topic, 'Explique os números deste recorte, suas limitações e próximos passos para avaliação humana.')
    navigate(3)


def preset(name):
    st.session_state.update(start=date(2023, 1, 1), end=date(2023, 12, 31), population='B',
                            channel='Todos', category='Todas', limit_ticket=False, ticket_limit=250.0, discount_only=False)
    begin_investigation(name)


def chart(figure, key):
    figure.update_layout(template='plotly_white', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                         font=dict(family='Arial', color=NAVY, size=12), margin=dict(l=18, r=18, t=12, b=32),
                         separators=',.', hoverlabel=dict(bgcolor='#FCFBF7', bordercolor='#C9D0C7', font_color=NAVY))
    if not figure.layout.legend.orientation:
        figure.update_layout(legend=dict(orientation='h', y=-.18))
    axis_style=dict(gridcolor='#E7E9E2', zerolinecolor='#D6DAD2', tickfont=dict(color='#6F786F',size=11),
                    title_font=dict(color='#687269',size=12), automargin=True)
    figure.update_xaxes(**axis_style)
    figure.update_yaxes(**axis_style)
    st.plotly_chart(figure, width='stretch', key=key, config={'displayModeBar': False})


def partial_months(rows, scope, room):
    """Months clipped by the selected window or by the source coverage."""
    if not rows:
        return set()
    start, end = pd.Timestamp(scope.start), pd.Timestamp(scope.end)
    source_start = room.orders.dt.min().normalize()
    source_end = room.orders.dt.max().normalize()
    partial = set()
    first_month, last_month = rows[0]['grupo'], rows[-1]['grupo']
    if start.day != 1 or (start.to_period('M') == source_start.to_period('M') and source_start.day != 1):
        partial.add(first_month)
    if end != end + pd.offsets.MonthEnd(0) or (end.to_period('M') == source_end.to_period('M') and source_end != source_end + pd.offsets.MonthEnd(0)):
        partial.add(last_month)
    return partial


def trend_value(value, metric):
    if value is None:
        return '—'
    if metric in {'margem_contribuicao', 'receita_liquida'}:
        return brl(value)
    if metric == 'mc_pct':
        return percent(value)
    return number(value)


def evidence(e, label='Como estes números foram calculados'):
    with st.expander(label):
        title, explanation = evidence_explanation(e)
        st.markdown('**'+title+'**')
        st.write(explanation)
        st.markdown('**Quais pedidos entram nesta conta?**')
        for name, value in scope_description(Scope(**e['escopo'])):
            st.write(f'**{name}:** {value}')
        st.markdown('**O que considerar ao interpretar**')
        for caveat in e['limitacoes']:
            st.write('• '+caveat)
        st.caption('Fontes: '+', '.join(e['fontes_sha256'])+'. Os detalhes técnicos permitem reproduzir esta análise.')
        if st.checkbox('Mostrar identificação técnica e arquivo de auditoria', key='tech_'+label+e['evidence_id']):
            st.caption(f"Referência: {e['evidence_id']} · cálculo {e['versao_calculo']} · contrato {e['versao_contrato']}")
            st.download_button('Baixar evidência técnica (JSON)', json.dumps(e, ensure_ascii=False, indent=2),
                file_name=e['evidence_id']+'.json', mime='application/json', key='download_'+label+e['evidence_id'])


def signal_cards(room, scope):
    with st.expander('Atalhos de análise · desconto e Marketplace'):
        discount = discount_candidate(room, scope)
        dv = discount['valores']
        cv = marketplace_comparison(room, scope)['valores']
        left, right = st.columns(2)
        with left:
            st.markdown('**Desconto em pedidos pequenos**')
            st.write(f"{number(dv['pedidos'])} pedidos elegíveis · {brl(dv['margem_contribuicao'])} de MC.")
            st.caption('Seleciona aprovados sem devolução, com desconto e abaixo de R$ 250 ou do limite menor atual. Preserva datas, canal e categoria.')
            st.button('Investigar desconto', on_click=begin_investigation, args=('discount',), disabled=not dv['pedidos'], width='stretch')
        with right:
            st.markdown('**Marketplace versus demais canais**')
            if cv['disponivel']:
                st.write(f"Diferença de MC: {number(cv['gap_mc_pp'],2)} p.p. · comparação contábil.")
                st.caption('Preserva todos os filtros. Diferença de margem não equivale a ganho recuperável.')
                st.button('Investigar Marketplace', on_click=begin_investigation, args=('marketplace',), width='stretch')
            else:
                st.caption(cv['motivo'])
                if scope.channel is not None:
                    st.button('Comparar com todos os canais', on_click=begin_investigation, args=('marketplace',True), help='Remove somente o filtro de canal.', width='stretch')
                else:
                    st.button('Investigar Marketplace', disabled=True, width='stretch')


def cards(e, total):
    with st.container(key='overview_kpis'):
        values = e['valores']
        items = []
        for title, value, tip in zip(
            ['Pedidos no recorte', 'Receita líquida registrada', 'MC observável', 'MC% observável'],
            [number(values['pedidos']), brl(values['receita_liquida']), brl(values['margem_contribuicao']), percent(values['mc_pct'])],
            ['Contagem de pedidos únicos no recorte.', 'Soma de receita bruta menos desconto; não reconstrói impostos.',
             'Receita líquida − produto − frete. Não é lucro.', 'Soma da MC ÷ soma da receita líquida. Não é média dos percentuais.']):
            field = {'Pedidos no recorte':'pedidos','Receita líquida registrada':'receita_liquida','MC observável':'margem_contribuicao','MC% observável':'mc_pct'}[title]
            whole = total['valores'][field]
            formatted = percent(whole) if field=='mc_pct' else number(whole) if field=='pedidos' else brl(whole)
            comparison = '' if formatted == value else f'<div class="kpi-total"><strong>Total</strong>&nbsp;&nbsp;{html.escape(formatted)}</div>'
            card_class = 'kpi-card has-comparison' if comparison else 'kpi-card'
            items.append(
                f'<article class="{card_class}">'
                f'<div class="kpi-label">{html.escape(title)}<span class="kpi-help" title="{html.escape(tip, quote=True)}" aria-label="{html.escape(tip, quote=True)}">?</span></div>'
                f'<div class="kpi-value">{html.escape(value)}</div>'
                f'{comparison}'
                '</article>'
            )
        st.markdown('<div class="kpi-grid">'+''.join(items)+'</div>', unsafe_allow_html=True)
        st.markdown('<aside class="kpi-reference"><span class="kpi-reference-label">Base de comparação</span><span>Total do mesmo período e população, sem filtros de canal, categoria, valor ou desconto. MC% representa a margem do total, não a soma dos percentuais.</span></aside>', unsafe_allow_html=True)


def table_groups(e):
    rows = e['valores']['grupos']
    if not rows:
        st.info('Nenhum pedido neste recorte.')
        return
    data = pd.DataFrame(rows).rename(columns={'grupo':'Grupo','pedidos':'Pedidos','receita_bruta':'Receita bruta',
        'desconto_reais':'Desconto','receita_liquida':'Receita líquida','custo_produto':'Produto',
        'custo_frete':'Frete','margem_contribuicao':'MC','mc_pct':'MC%'})
    st.dataframe(data, hide_index=True, width='stretch', column_config={
        c: st.column_config.NumberColumn(c, format='%.2f') for c in data.columns if c not in ['Grupo','Pedidos']})


DIMENSION_LABELS = {'canal':'Canal', 'categoria':'Categoria', 'faixa_ticket':'Faixa de valor', 'mes':'Mês', 'com_desc':'Com / sem desconto', 'com_frete':'Com / sem frete', 'metodo_pagamento':'Pagamento'}
METRIC_LABELS = {'mc_pct':'MC (%)', 'margem_contribuicao':'MC (R$)', 'receita_liquida':'Receita líquida (R$)', 'pedidos':'Pedidos', 'custo_frete':'Frete (R$)', 'desconto_reais':'Descontos (R$)'}
TREND_METRIC_LABELS = {'margem_contribuicao':'MC (R$)', 'mc_pct':'MC (%)', 'receita_liquida':'Receita líquida', 'pedidos':'Pedidos'}


def group_name(name):
    return {'True':'Sim', 'False':'Não', 'até 100':'Até R$ 100', '(100,250]':'R$ 100–250', '(250,500]':'R$ 250–500', '(500,1000]':'R$ 500–1.000', '>1000':'Acima de R$ 1 mil'}.get(str(name),str(name))


def bars(e, metric, key, height=300):
    groups = e['valores']['grupos']
    dimension = e['valores'].get('dimensao')
    if dimension == 'faixa_ticket':
        order=['até 100','(100,250]','(250,500]','(500,1000]','>1000']
        groups=sorted(groups,key=lambda g: order.index(g['grupo']))
    elif dimension == 'canal':
        groups=sorted(groups,key=lambda g: g[metric] if g[metric] is not None else float('-inf'),reverse=True)
    if not groups:
        st.info('Nenhum grupo disponível.')
        return
    f=go.Figure(go.Bar(x=[g[metric] for g in groups],y=[group_name(g['grupo']) for g in groups],orientation='h',
        marker_color=[AMBER if g['grupo']=='Marketplace' else TEAL for g in groups],
        text=[percent(g[metric]) if metric=='mc_pct' else number(g[metric]) if metric=='pedidos' else brl(g[metric]) for g in groups],
        textposition='outside', cliponaxis=False,
        customdata=[[g['pedidos'],g['receita_liquida']] for g in groups],
        hovertemplate='%{y}<br>'+METRIC_LABELS[metric]+': %{x:,.2f}<br>Pedidos: %{customdata[0]:,}<br>Receita: R$ %{customdata[1]:,.2f}<extra></extra>'))
    f.update_layout(height=max(height,len(groups)*36+54),xaxis_title=METRIC_LABELS[metric],yaxis=dict(autorange='reversed'),bargap=.38)
    if key in {'channels', 'ticket_bands'}:
        f.update_xaxes(title_text=None)
        f.update_yaxes(showgrid=False, zeroline=False)
    points=[g[metric] for g in groups if g[metric] is not None]
    if points:
        low=min(0,min(points));high=max(0,max(points));span=max(high-low,1)
        f.update_xaxes(range=[low-span*.22 if low<0 else 0,high+span*.42])
    chart(f,key)


def waterfall(metrics, key):
    v=metrics['valores']
    f=go.Figure(go.Waterfall(x=['Receita bruta','Desconto','Produto','Frete','MC'],
        measure=['absolute','relative','relative','relative','total'],
        y=[v['receita_bruta'],-v['desconto_reais'],-v['custo_produto'],-v['custo_frete'],0],
        text=[brl(v['receita_bruta']),brl(-v['desconto_reais']),brl(-v['custo_produto']),brl(-v['custo_frete']),brl(v['margem_contribuicao'])],textposition='outside',cliponaxis=False,
        increasing={'marker':{'color':TEAL}},decreasing={'marker':{'color':AMBER}},totals={'marker':{'color':NAVY}}))
    f.update_layout(height=330,yaxis_title='R$')
    chart(f,key)


def quality_panel(room, metrics):
    v=metrics['valores']
    a,b,c=st.columns(3)
    a.metric('Cobertura de Atendimento',percent(v['cobertura_atendimento_pct']))
    b.metric('Tickets vinculados',number(v['tickets_vinculados']))
    c.metric('Custo vinculado registrado',brl(v['atendimento_vinculado_registrado']))
    window=' → '.join(x[:10] for x in v['janela_tickets_vinculados']) if v['janela_tickets_vinculados'] else 'sem vínculos'
    st.caption(f'Tickets: {window}. Tarifa padronizada; sem vínculo não comprova custo zero. Não é despesa exclusivamente do período dos pedidos.')
    q=room.quality
    checks=[('Tickets sem pedido correspondente',q['tickets_sem_pedido']),('Cliente divergente',q['tickets_cliente_divergente']),('Abertura anterior ao pedido',q['tickets_anteriores_pedido'])]
    f=go.Figure(go.Bar(x=[n for _,n in checks],y=[label for label,_ in checks],orientation='h',marker_color=AMBER,text=[number(n) for _,n in checks],textposition='auto',cliponaxis=False))
    f.update_layout(height=250,xaxis_title='Tickets · fonte completa',yaxis=dict(autorange='reversed'))
    chart(f,'quality_links')
    with st.expander('Regras de vínculo e lacunas'):
        st.write('Vinculamos pedido e cliente correspondentes, com abertura do ticket não anterior ao pedido. Os tickets são agregados antes do cruzamento para não multiplicar a receita.')
        st.write(f"Removidas as linhas incompletas conhecidas: {room.removed['vendas']} em Vendas e {room.removed['atendimento']} em Atendimento.")
        st.write('Ainda não calculáveis: lucro completo, perda líquida de devoluções, CAC de novos clientes e efeito causal das intervenções. Marketing e Clientes não são integrados sem reconciliação; Estoque não tem fotografia histórica datada.')
    evidence(metrics,'Definições e fontes dos indicadores')


def tower(room, scope, metrics):
    cards(metrics, comparison_total(room, scope))
    if not metrics['valores']['pedidos']:
        st.info('Nenhum pedido encontrado. Ajuste os filtros.')
        evidence(metrics)
        return
    panorama,quality=st.tabs(['Visão geral','Qualidade e cobertura'])
    with panorama:
        left,right=st.columns([1.15,1])
        monthly=room.breakdown('mes',scope)
        channels=room.breakdown('canal',scope)
        with left:
            with st.container(border=True,key='panel_monthly'):
                st.markdown('<div class="panel-title">Evolução mensal</div>',unsafe_allow_html=True)
                trend_options=['margem_contribuicao','mc_pct','receita_liquida','pedidos']
                trend_default=st.session_state.get('trend_metric','margem_contribuicao')
                if trend_default not in trend_options:
                    trend_default='margem_contribuicao'
                metric=st.segmented_control('Indicador da série',trend_options,default=trend_default,format_func=TREND_METRIC_LABELS.get,key='trend_metric_selector',selection_mode='single',label_visibility='collapsed') or trend_default
                st.session_state['trend_metric']=metric
                rows=monthly['valores']['grupos']
                month_names={'01':'jan','02':'fev','03':'mar','04':'abr','05':'mai','06':'jun','07':'jul','08':'ago','09':'set','10':'out','11':'nov','12':'dez'}
                x_values=[g['grupo'] for g in rows]
                y_values=[g[metric] for g in rows]
                labels=[month_names.get(g['grupo'][5:7],g['grupo'][5:7]) for g in rows]
                partial=partial_months(rows,scope,room)
                hover_data=[[labels[i],trend_value(g[metric],metric),'<br>Parcial' if g['grupo'] in partial else ''] for i,g in enumerate(rows)]
                f=go.Figure(go.Scatter(
                    x=x_values,y=y_values,mode='lines+markers',
                    line=dict(color=TEAL,width=2.5),
                    marker=dict(size=4.5,color=TEAL,line=dict(color=TEAL,width=0)),
                    customdata=hover_data,
                    hovertemplate='<b>%{customdata[0]}</b><br>%{customdata[1]}%{customdata[2]}<extra></extra>',
                    showlegend=False,
                ))
                partial_rows=[(i,g) for i,g in enumerate(rows) if g['grupo'] in partial]
                if partial_rows:
                    f.add_trace(go.Scatter(
                        x=[g['grupo'] for _,g in partial_rows],y=[g[metric] for _,g in partial_rows],mode='markers',
                        marker=dict(size=8,color='#FCFBF7',line=dict(color=TEAL,width=2),symbol='circle'),
                        customdata=[[labels[i],trend_value(g[metric],metric)] for i,g in partial_rows],
                        hovertemplate='<b>%{customdata[0]}</b><br>%{customdata[1]}<br>Parcial<extra></extra>',
                        showlegend=False,
                    ))
                yaxis=dict(title=None,showgrid=True,gridcolor='rgba(104,114,105,.12)',gridwidth=1,zeroline=False)
                if metric in {'margem_contribuicao','receita_liquida'}:
                    yaxis.update(tickformat='.1s',separatethousands=True)
                elif metric=='mc_pct':
                    yaxis.update(ticksuffix='%',tickformat='.1f')
                else:
                    yaxis.update(tickformat=',.0f')
                f.update_layout(height=280,hovermode='closest',hoverdistance=24,yaxis=yaxis,
                    xaxis=dict(type='category',tickmode='array',tickvals=x_values,ticktext=labels,showgrid=False,zeroline=False))
                chart(f,'monthly')
        with right:
            with st.container(border=True,key='panel_channels'):
                st.markdown('<div class="panel-title">Margem de Contribuição por Canal (%)</div>',unsafe_allow_html=True)
                bars(channels,'mc_pct','channels',300)
        left,right=st.columns([1.15,1])
        bands=room.breakdown('faixa_ticket',scope)
        funnel=room.funnel(replace(scope,population='A'))
        with left:
            with st.container(border=True,key='panel_bands'):
                st.markdown('<div class="panel-title">Margem de Contribuição por Valor do Pedido (%)</div>',unsafe_allow_html=True)
                bars(bands,'mc_pct','ticket_bands',300)
        with right:
            with st.container(border=True,key='panel_status'):
                st.markdown('<div class="panel-title">Situação dos pedidos</div>',unsafe_allow_html=True)
                fv=funnel['valores']
                keys=['aprovados_sem_devolucao','aprovados_devolvidos','nao_aprovados']
                labels=['Aprovados sem devolução','Aprovados e devolvidos','Não aprovados']
                f=go.Figure(go.Pie(labels=labels,values=[fv[k]['pedidos'] for k in keys],hole=.64,sort=False,
                    domain=dict(x=[0,.54],y=[.04,.96]),marker=dict(colors=[TEAL,AMBER,'#C9D0BF']),
                    textinfo='percent',textfont=dict(size=11),hovertemplate='%{label}<br>%{value} pedidos · %{percent}<extra></extra>'))
                f.update_layout(height=290,showlegend=True,
                    legend=dict(orientation='v',x=.61,y=.5,yanchor='middle',font=dict(size=11),traceorder='normal'),
                    annotations=[dict(text=f"<b>{number(fv['total_pedidos'])}</b><br><span style='font-size:11px;color:#687269'>pedidos</span>",x=.27,y=.5,showarrow=False,font=dict(size=21))])
                chart(f,'order_status')
        signal_cards(room,scope)
        with st.expander('Dados e cálculos dos gráficos'):
            evidence(monthly,'Série mensal')
            evidence(channels,'Comparação por canal')
            evidence(bands,'Faixas de valor')
            evidence(funnel,'Situação dos pedidos')
        st.caption('Comparações descritivas; diferenças observadas não demonstram efeito causal.')
    with quality:
        quality_panel(room,metrics)


def investigate(room, scope, metrics):
    st.title('Explorar')
    cards(metrics, comparison_total(room, scope))
    if not metrics['valores']['pedidos']:
        st.info('Nenhum pedido neste recorte. Ajuste os filtros.')
        return
    view=st.radio('Visualização',['Comparar grupos','Composição da margem','Marketplace'],horizontal=True,key='analysis_view',label_visibility='collapsed')
    if view=='Marketplace':
        comparison=marketplace_comparison(room,scope)
        cv=comparison['valores']
        if not cv['disponivel']:
            st.info(cv['motivo'])
            if scope.channel is not None:
                st.button('Comparar com todos os canais',on_click=begin_investigation,args=('marketplace',True),help='Remove somente o filtro de canal.')
        else:
            mp,others=cv['grupos']
            a,b,c=st.columns(3)
            a.metric('MC% Marketplace',percent(mp['mc_pct']))
            b.metric('MC% demais canais',percent(others['mc_pct']))
            c.metric('Diferença de MC',number(cv['gap_mc_pp'],2)+' p.p.')
            f=go.Figure()
            for field,label,color in [('produto_pct','Produto','#C9D0BF'),('frete_pct','Frete',AMBER),('mc_pct','MC observável',TEAL)]:
                f.add_trace(go.Bar(name=label,x=[g[field] for g in cv['grupos']],y=[g['grupo'] for g in cv['grupos']],orientation='h',marker_color=color,text=[percent(g[field]) for g in cv['grupos']],textposition='auto'))
            f.update_layout(barmode='relative',height=280,xaxis_title='Participação na receita líquida (%)')
            chart(f,'marketplace_components')
            st.caption(f"Frete: {percent(mp['frete_pct'])} da receita no Marketplace e {percent(others['frete_pct'])} nos demais. Comparação contábil; não demonstra causa operacional ou ganho recuperável.")
            with st.expander('Interpretar a comparação'):
                st.write('A comparação usa os totais de receita de cada grupo, não a média simples das margens dos canais. Fees, comissões, subsídios e condições logísticas precisam ser validados antes de uma intervenção.')
            evidence(comparison,'Como calculamos esta comparação')
    else:
        col1,col2=st.columns(2)
        dimension=col1.selectbox('Agrupar por',list(DIMENSION_LABELS),format_func=DIMENSION_LABELS.get,key='dimension')
        breakdown=room.breakdown(dimension,scope)
        if view=='Comparar grupos':
            metric=col2.selectbox('Indicador',list(METRIC_LABELS),format_func=METRIC_LABELS.get,key='explore_metric')
            left,right=st.columns([1.1,1])
            with left,st.container(border=False):
                st.subheader(METRIC_LABELS[metric]+' por '+DIMENSION_LABELS[dimension].lower())
                bars(breakdown,metric,'explore_groups',340)
            with right,st.container(border=False):
                st.subheader('Receita × margem')
                rows=[g for g in breakdown['valores']['grupos'] if g['mc_pct'] is not None]
                max_n=max((g['pedidos'] for g in rows),default=1)
                f=go.Figure(go.Scatter(x=[g['receita_liquida'] for g in rows],y=[g['mc_pct'] for g in rows],mode='markers',
                    text=[group_name(g['grupo']) for g in rows],customdata=[g['pedidos'] for g in rows],
                    marker=dict(size=[12+35*(g['pedidos']/max_n)**.5 for g in rows],color=TEAL,opacity=.75),
                    hovertemplate='%{text}<br>Receita: R$ %{x:,.2f}<br>MC: %{y:.2f}%<br>Pedidos: %{customdata}<extra></extra>'))
                f.update_layout(height=340,xaxis_title='Receita líquida (R$)',yaxis_title='MC (%)')
                chart(f,'economic_map')
                st.caption('Bolha maior = mais pedidos. Relação descritiva, sem inferência causal.')
        else:
            left,right=st.columns([1.1,1])
            with left,st.container(border=False):
                st.subheader('Da receita à contribuição')
                waterfall(metrics,'waterfall')
            with right,st.container(border=False):
                st.subheader('Componentes por grupo')
                rows=breakdown['valores']['grupos']
                f=go.Figure()
                for field,label,color in [('custo_produto','Produto','#C9D0BF'),('custo_frete','Frete',AMBER),('margem_contribuicao','MC',TEAL)]:
                    f.add_trace(go.Bar(name=label,y=[group_name(g['grupo']) for g in rows],x=[g[field] for g in rows],orientation='h',marker_color=color,text=[brl(g[field]) for g in rows],textposition='auto',hovertemplate='%{y}<br>%{text}<extra>%{fullData.name}</extra>'))
                f.update_layout(height=330,barmode='relative',xaxis_title='R$ · produto + frete + MC = receita líquida',yaxis=dict(autorange='reversed'))
                chart(f,'group_components')
            st.caption('Frete já está deduzido na MC. Atendimento tem cobertura parcial e não está nesta decomposição.')
        with st.expander('Tabela detalhada e fontes'):
            table_groups(breakdown)
            evidence(breakdown,'Como calculamos os grupos')
            evidence(metrics,'Como calculamos os totais')
        with st.expander('Comparar por um segundo critério'):
            options=[x for x in DIMENSION_LABELS if x!=dimension]
            control=st.selectbox('Separar também por',options,format_func=DIMENSION_LABELS.get)
            stratified=room.stratified(dimension,control,scope)
            rows=stratified['valores']['grupos']
            frame=pd.DataFrame(rows)
            if not frame.empty:
                pivot=frame.pivot(index='grupo',columns='estrato',values='mc_pct')
                f=go.Figure(go.Heatmap(z=pivot.values.tolist(),x=[group_name(x) for x in pivot.columns],y=[group_name(x) for x in pivot.index],colorscale=[[0,'#EFF0E6'],[.5,'#A6B498'],[1,'#365640']],colorbar=dict(title='MC%'),hoverongaps=False))
                f.update_layout(height=340,xaxis_title=DIMENSION_LABELS[control],yaxis_title=DIMENSION_LABELS[dimension])
                chart(f,'stratified_heatmap')
            st.caption('Combinações ausentes ficam vazias. Estratificar não prova causalidade.')
            evidence(stratified,'Como calculamos os subgrupos')
    candidate = st.selectbox('Intervenção a avaliar', ['Escolha uma intervenção', 'Custo de frete', 'Desconto'],
        index=1 if view=='Marketplace' else 2 if st.session_state.get('investigation_topic')=='discount' else 0,
        key='candidate_intervention', help='Escolha uma ação compatível com a sua análise. O cenário não comprova sua viabilidade.')
    left,right=st.columns(2)
    if candidate=='Custo de frete':
        left.button('Simular redução do custo de frete',on_click=open_simulation,args=('frete',),width='stretch')
    elif candidate=='Desconto':
        left.button('Simular alteração de desconto',on_click=open_simulation,args=('desconto',),width='stretch')
    else:
        left.caption('Escolha uma intervenção para abrir o cenário. Você também pode continuar investigando as lacunas com o Copilot.')
    right.button('Levar esta pergunta ao Copilot',on_click=explain_investigation,args=('marketplace' if view=='Marketplace' else 'discount' if st.session_state.get('investigation_topic')=='discount' else 'free',),width='stretch')
    st.caption('Explore livremente ou abra um cenário. Os atalhos não definem uma política comercial.')


def remember_parameter(key):
    st.session_state['saved_'+key] = st.session_state[key]


def simulate(room, scope, store):
    st.title('Simular')
    intervention = st.radio('Intervenção', ['desconto','frete'], horizontal=True, key='simulation_kind',
        format_func=lambda x: 'Desconto' if x=='desconto' else 'Custo de frete')
    freight = intervention=='frete'
    st.caption('Compare cenários condicionais. A viabilidade da intervenção e a retenção precisam ser validadas.')
    eligible = replace(scope, population='B') if freight else eligible_scope(scope)
    if scope != eligible:
        before = room.metrics(scope)['valores']['pedidos']
        after = room.metrics(eligible)['valores']['pedidos']
        if freight:
            st.info(f'O cenário usa aprovados sem devolução (B). Ajustar muda de {number(before)} para {number(after)} pedidos. Datas, canal, categoria, limite de valor e filtro de desconto serão preservados.')
            st.button('Usar aprovados sem devolução (B)', on_click=apply_freight_population, type='primary')
        else:
            st.info(f'O cenário de desconto usa B, desconto positivo e receita líquida histórica abaixo de R$250 (ou limite menor). Ajustar muda de {number(before)} para {number(after)} pedidos. Datas, canal e categoria serão preservados.')
            st.button('Aplicar recorte elegível', on_click=apply_eligible, type='primary')
        return
    c1, c2 = st.columns(2)
    removal = c1.slider('Redução hipotética do custo de frete (%)' if freight else 'Desconto a retirar (%)', 0, 100, value=st.session_state.get('saved_freight_reduction' if freight else 'saved_removal', 10 if freight else 100), key='freight_reduction' if freight else 'removal', step=5, on_change=remember_parameter, args=('freight_reduction' if freight else 'removal',),
                        help='Aplica a porcentagem ao frete registrado de cada pedido; viabilidade não comprovada.' if freight else '100% remove todo o desconto histórico; 50% remove metade.') / 100
    if freight:
        retention = c2.slider('Retenção hipotética dos pedidos (%)', 0.0, 100.0,
            value=float(st.session_state.get('saved_freight_retention', 100.0)), key='freight_retention', step=0.1,
            on_change=remember_parameter, args=('freight_retention',),
            help='Premissa aplicada a todo o recorte. Use décimos de ponto percentual para avaliar pequenas perdas. 100% isola o efeito financeiro da redução de custo.') / 100
    else:
        retention = c2.slider('Retenção hipotética dos pedidos (%)', 0, 100, value=st.session_state.get('saved_retention', 80), key='retention', step=5, on_change=remember_parameter, args=('retention',),
                            help='Entrada de cenário. Não é previsão nem taxa de conversão medida.') / 100
    e = calculate_scenario(room, scope, removal, retention, intervention)
    v = e['valores']
    st.session_state['active_scenario'] = e
    st.caption(scenario_description(e))
    if freight:
        st.caption(f"Recorte preservado: {number(v['pedidos_elegiveis'])} pedidos; {number(v['pedidos_com_frete_registrado'])} com custo de frete positivo. Pedidos com frete zero ficam na base sem redução de custo.")
    a, b, c, d = st.columns(4)
    a.metric('Pedidos elegíveis congelados', number(v['pedidos_elegiveis']))
    b.metric('MC histórica', brl(v['mc_base']))
    c.metric('MC do cenário', brl(v['mc_cenario']), delta=brl(v['delta_mc_cenario']), delta_color='normal')
    d.metric('Retenção de equilíbrio', percent(v['retencao_equilibrio']*100) if v['retencao_equilibrio'] is not None else 'Não aplicável')
    if not v['pedidos_elegiveis']:
        st.info('Nenhum pedido elegível. Não há cenário para salvar.')
        evidence(e)
        return
    with st.container(border=False):
        rows = sensitivity(room, scope, removal, intervention)
        f = go.Figure(go.Scatter(x=[r['Retenção hipotética (%)'] for r in rows], y=[r['Variação da MC (R$)'] for r in rows],
                                mode='lines', line=dict(color=TEAL, width=3), fill='tozeroy', fillcolor='rgba(66,99,77,.08)'))
        f.add_hline(y=0, line_dash='dash', line_color=AMBER)
        f.add_trace(go.Scatter(x=[retention*100], y=[v['delta_mc_cenario']], mode='markers', marker=dict(size=12, color=NAVY), name='Cenário selecionado'))
        if v['retencao_equilibrio'] is not None:
            f.add_vline(x=v['retencao_equilibrio']*100, line_dash='dot', line_color=TEAL)
        f.update_layout(height=310, xaxis_title='Retenção hipotética (%)', yaxis_title='Variação da MC (R$)', showlegend=False)
        chart(f, 'sensitivity')
        st.caption('O equilíbrio depende do perfil médio dos pedidos retidos. A curva não estima probabilidade nem demanda futura.')
    st.caption('Limites comerciais não definidos · cenário sujeito à revisão humana.')
    reduction_field = 'reducao_frete_se_todos_retidos' if freight else 'reducao_desconto_se_todos_retidos'
    st.caption(('Redução hipotética do custo de frete' if freight else 'Desconto removido')+f": {brl(v[reduction_field])} se todos forem retidos. Não é ganho garantido.")
    if v['guardrails']['mc_agregada_cenario_negativa']:
        st.error('A MC agregada simulada é negativa. O resultado exige revisão; nenhuma venda foi bloqueada.')
    st.caption(f"Pedidos com MC negativa se retidos: {v['guardrails']['pedidos_com_mc_negativa_se_retidos']}.")
    with st.expander('Premissas e cálculo', expanded=False):
        component = 'redução hipotética do custo de frete' if freight else 'desconto retirado'
        st.write(f'Contribuição simulada = (contribuição histórica + {component}) × parcela dos pedidos retidos.')
        st.write(f'Retenção de equilíbrio = contribuição histórica ÷ (contribuição histórica + {component}), quando a contribuição histórica é positiva.')
        for x in e['limitacoes']:
            st.write('• '+x)
    with st.expander('Sobreposição entre intervenções'):
        st.write('Este cenário altera apenas o componente selecionado. Não adiciona exposição de frete ou Atendimento ao resultado. O núcleo combina componentes distintos por pedido e rejeita duas alterações do mesmo componente sem uma regra conjunta explícita. A composição de múltiplas intervenções não está habilitada nesta tela.')
    evidence(e, 'Evidência do cenário')
    with st.expander('Salvar cenário e hipótese'):
        st.subheader('Salvar para revisão humana')
        records = store.list_scenarios()
        existing = {r['case_id']: r['title'] for r in records}
        with st.form('save_scenario'):
            target = st.selectbox('Vincular a um caso', ['novo', *existing], format_func=lambda x: 'Criar novo caso' if x=='novo' else existing[x])
            title = st.text_input('Título do caso', value='Redução do custo logístico no recorte selecionado' if freight else 'Revisão de desconto em pedidos abaixo de R$ 250')
            hypothesis = st.text_area('Hipótese a testar', value='Uma alternativa logística pode reduzir o custo de frete e preservar contribuição, prazo e experiência dentro dos limites acordados. Viabilidade e impacto precisam ser testados.' if freight else 'Uma redução de desconto pode melhorar a contribuição por unidade elegível sem deteriorar conversão e experiência além dos limites acordados.')
            owner = st.text_input('Responsável declarado', placeholder='Nome ou papel responsável pela análise')
            save = st.form_submit_button('Salvar cenário', type='primary')
        if save:
            try:
                sid = store.save_scenario(snapshot(room, scope, removal, retention, intervention), title, hypothesis, owner,
                                          case_id=None if target=='novo' else target)
                st.session_state['selected_scenario'] = sid
                st.success('Cenário salvo como rascunho. População, premissas e evidências foram congeladas.')
            except ValueError as exc:
                st.error(str(exc))
    left, right = st.columns(2)
    left.button('Explicar cenário no Copilot', on_click=navigate, args=(3,), width='stretch')
    right.button('Abrir histórico de decisões', on_click=navigate, args=(4,), width='stretch')


def copilot(room, scope, metrics):
    st.title('Copilot')
    st.caption('Pergunte sobre o recorte atual. Respostas com fontes, para revisão humana.')
    active = st.session_state.get('active_scenario')
    if active and active['escopo'] != asdict(scope):
        active = None
    evidences = [metrics] + ([active] if active else [])
    if active:
        st.info('Contexto inclui o cenário atual: '+scenario_description(active))
    with st.expander('Ver resumo calculado · sem IA'):
        brief = deterministic_brief(evidences)
        st.markdown(brief)
        st.download_button('Baixar resumo sem IA', brief, file_name='resumo_calculado.md', mime='text/markdown')
    conf = configuration()
    if conf.get('config_error'):
        st.error('Não foi possível ler a configuração local de IA. Confira a sintaxe de .streamlit/secrets.toml.')
    if not conf['configured']:
        st.info('IA ainda não configurada. O resumo calculado permanece disponível acima.')
        with st.expander('Configuração técnica da integração de IA'):
            st.caption('EloAgents: preencha VERTICE_API_KEY em .streamlit/secrets.toml no servidor. Endereço e modelo já estão indicados nesse arquivo. Variáveis de ambiente têm prioridade. Não compartilhe esse arquivo.')
    else:
        st.caption('Modelo configurado: '+conf['model'])
    key = context_key(scope) + (active['evidence_id'] if active else '')
    histories = st.session_state.setdefault('ai_history', {})
    history = histories.setdefault(key, [])
    with st.form('ask_copilot'):
        question = st.text_area('Pergunta para o Copilot', value=st.session_state.get('suggested_question', 'Explique os números deste recorte, suas limitações e quais próximos passos merecem avaliação humana.'), key='copilot_question', max_chars=4000)
        remember = st.checkbox('Usar as duas últimas interações deste mesmo contexto como memória revisável', value=False)
        st.caption('Ao consultar, a pergunta, agregados do recorte e, se selecionado, o histórico serão enviados à API configurada. IDs de clientes, pedidos e tickets não são enviados.')
        ask = st.form_submit_button('Consultar IA', disabled=not conf['configured'], type='primary')
    if ask:
        with st.spinner('Consultando ferramentas governadas…'):
            result = run_investigation(room, scope, question, scenario=active, history=history if remember else [])
        st.session_state['ai_last'] = {'key': key, 'question': question, 'result': result}
        if result.get('status')=='rascunho':
            history.append({'question': question, 'answer': result['answer']})
    last = st.session_state.get('ai_last')
    if last and last['key']==key:
        r = last['result']
        st.caption('Pergunta: '+last['question'])
        if r['status']=='rascunho':
            st.warning('Rascunho para revisão. Referências existentes não garantem que a interpretação esteja correta.')
            doc = r['answer']
            if doc['abstention']:
                st.info('Limite da resposta: '+doc['abstention_reason'])
            for i, claim in enumerate(doc['claims']):
                st.write(claim['text'])
                for eid in claim['evidence_ids']:
                    evidence(r['evidence'][eid], f'Fonte {i+1} · {eid}')
            st.markdown('**Limitações**')
            for x in doc['limitations']:
                st.write('• '+x)
            st.markdown('**Próximos passos para revisão**')
            for x in doc['next_steps']:
                st.write('• '+x)
            st.download_button('Baixar investigação e rastro', json.dumps(r, ensure_ascii=False, indent=2), file_name='investigacao_copilot.json', mime='application/json')
        else:
            st.error(r['message'])
        with st.expander('O que foi consultado nesta resposta'):
            tool_names = {'metricas':'Indicadores do recorte', 'decompor':'Comparação entre grupos', 'funil':'Situação dos pedidos', 'simular_desconto':'Simulação de desconto', 'simular_frete':'Simulação de custo de frete', 'comparar_estratos':'Comparação por subgrupos', 'comparar_marketplace':'Marketplace versus demais canais'}
            trace = [{'Consulta': tool_names.get(x['tool'], 'Solicitação não autorizada'), 'Resultado': 'Concluída' if x['status']=='ok' else 'Não concluída'} for x in r.get('trace', [])]
            if trace:
                st.table(pd.DataFrame(trace))
            st.caption(f"Tempo: {r.get('latency_seconds', 'indisponível')} segundos. A correção da interpretação ainda exige revisão humana; custo monetário deve ser conferido no provedor.")
    elif last:
        st.caption('A resposta anterior pertence a outro contexto e foi ocultada. Consulte novamente para usar estes filtros.')
    for e in evidences:
        evidence(e, 'Contexto '+e['evidence_id'])
    st.button('Ir para decisões', on_click=navigate, args=(4,))


def decisions(room, store):
    st.title('Decisões')
    st.write('Consulte cenários congelados e registre revisões humanas. Aprovar para teste não comprova ganho.')
    st.caption('MVP local: responsáveis são declarados, sem autenticação. Nenhuma política comercial é executada.')
    rows = store.list_scenarios()
    if not rows:
        st.info('Nenhum cenário salvo. Comece com uma simulação e registre sua hipótese.')
        st.button('Criar primeiro cenário', on_click=navigate, args=(2,), type='primary')
        return
    choices = {r['id']: f"{r['title']} · v{r['version']} · {r['status']} · {r['id'][:6]}" for r in rows}
    if st.session_state.get('selected_scenario') not in choices:
        st.session_state['selected_scenario'] = rows[0]['id']
    sid = st.selectbox('Cenário salvo', list(choices), format_func=choices.get, key='selected_scenario')
    record = store.load(sid)
    s = record['snapshot']['scenario']; v = s['valores']; latest = record['decisions'][-1]
    st.caption('Este registro usa o recorte salvo, independentemente dos filtros atuais da barra lateral.')
    st.write('**Recorte congelado:** '+scope_label(Scope(**s['escopo'])))
    st.write('**Hipótese:** '+record['case']['hypothesis'])
    st.write('**Responsável:** '+record['case']['owner'])
    a, b, c = st.columns(3)
    a.metric('MC histórica', brl(v['mc_base']))
    b.metric('MC simulada', brl(v['mc_cenario']))
    c.metric('Situação', latest['status'])
    st.caption(scenario_description(s))
    if s['fontes_sha256'] != room.source_hashes or s['hash_contrato'] != room.contract_hash:
        st.warning('Fontes ou contrato mudaram desde este cenário. O registro histórico foi preservado; crie uma nova versão para analisar a base atual.')
    evidence(s, 'Cálculo congelado do cenário')
    st.subheader('Histórico de revisão')
    st.dataframe(pd.DataFrame(record['decisions'])[['revision','status','reviewer','rationale','created_at']].rename(columns={
        'revision':'Revisão','status':'Situação','reviewer':'Revisor declarado','rationale':'Justificativa','created_at':'Data UTC'}), hide_index=True, width='stretch')
    options = TRANSITIONS[latest['status']]
    if options:
        target = st.selectbox('Próxima situação', options, key='next_'+sid+'_'+str(latest['revision']))
        with st.form('decision_'+sid+'_'+str(latest['revision'])):
            reviewer = st.text_input('Revisor / decisor declarado')
            rationale = st.text_area('Justificativa e evidência da decisão', help='Ao encerrar, informe resultado, limitações e aprendizado. Não invente resultado de experimento.')
            if target == 'aprovado para teste':
                st.caption('Defina o plano antes de aprovar o teste.')
            plan_labels = {'elegibilidade':'Quem será elegível (incluindo não compradores)', 'kpi_primario':'KPI primário',
                           'comparacao':'Desenho de comparação / controle', 'guardrails':'Guardrails e limites definidos pelo negócio',
                           'criterio':'Critério para escalar, iterar ou encerrar', 'janela':'Janela e maturação de devoluções'}
            plan = {k: st.text_area(label, key='plan_'+sid+'_'+k) for k, label in plan_labels.items()} if target=='aprovado para teste' else None
            acknowledged = st.checkbox('Confirmo a revisão humana; este registro não executa uma política nem comprova ganho.')
            save = st.form_submit_button('Registrar decisão', type='primary')
        if save:
            if not acknowledged:
                st.error('Confirme a revisão antes de registrar.')
            else:
                try:
                    store.transition(sid, target, reviewer, rationale, latest['revision'], plan if target=='aprovado para teste' else None)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
    else:
        st.info('Registro encerrado. Para alterar as premissas, salve uma nova versão pelo simulador.')
    if record['plans']:
        with st.expander('Planos de validação registrados'):
            for p in record['plans']:
                plan_names = {'elegibilidade':'Quem participa', 'kpi_primario':'Métrica principal', 'comparacao':'Comparação / controle', 'guardrails':'Limites de proteção', 'criterio':'Critério de decisão', 'janela':'Período de avaliação'}
                for field, value in p['payload'].items():
                    st.write(f'**{plan_names.get(field, field)}:** {value}')
    left, right = st.columns(2)
    left.download_button('Exportar dossiê Markdown', export_markdown(record), file_name='decisao_'+sid[:8]+'.md', mime='text/markdown', width='stretch')
    # Evidence includes aggregate values; no customer IDs or raw ticket content in the export.
    right.download_button('Exportar registro completo JSON', json.dumps(record, ensure_ascii=False, indent=2), file_name='decisao_'+sid[:8]+'.json', mime='application/json', width='stretch')
    with st.expander('Histórico de registros do sistema'):
        event_names = {'caso_criado':'Caso criado', 'cenario_salvo':'Cenário salvo', 'decisao_registrada':'Decisão humana registrada'}
        st.table(pd.DataFrame([{'Data UTC': x['created_at'], 'Registro': event_names.get(x['event'], x['event'])} for x in record['audit']]))


def main():
    signature = tuple((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in [ROOT/'data-room/vendas.csv', ROOT/'data-room/atendimento.csv', ROOT/'prototipo/contratos/metricas.json'])
    try:
        room = load_room(signature)
    except (ValueError, KeyError, OSError) as exc:
        st.error('Falha na validação das fontes. Nenhum KPI foi publicado: '+str(exc))
        st.stop()
    defaults = dict(page=PAGES[0], start=date(2023,1,1), end=date(2023,12,31), population='B', channel='Todos',
                    category='Todas', limit_ticket=False, ticket_limit=250.0, discount_only=False)
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)
    with st.sidebar:
        st.markdown('<div class="brand"><span class="brand-mark"></span><span class="brand-name">vértice.</span></div><div class="brand-sub">Inteligência de margem</div>', unsafe_allow_html=True)
        st.radio('Área', PAGES, key='page', label_visibility='collapsed', format_func=lambda x: 'Explorar' if x==PAGES[1] else x.split(' · ',1)[1])
        st.divider()
        st.markdown('**Recorte da análise**')
        lower, upper = room.orders.dt.min().date(), room.orders.dt.max().date()
        st.date_input('Início', key='start', min_value=lower, max_value=upper)
        st.date_input('Fim', key='end', min_value=lower, max_value=upper)
        st.selectbox('Canal', ['Todos', *sorted(room.orders.canal.unique())], key='channel')
        st.selectbox('Categoria', ['Todas', *sorted(room.orders.categoria.unique())], key='category')
        with st.expander('Mais filtros: situação, valor e desconto'):
            st.selectbox('Pedidos considerados', ['B','A'], key='population', format_func=lambda x: 'Aprovados sem devolução' if x=='B' else 'Todos os status', help='B: aprovados e sem devolução registrada. A: inclui também não aprovados e devolvidos.')
            st.checkbox('Limitar receita líquida histórica', key='limit_ticket')
            st.number_input('Receita líquida menor que (R$)', min_value=0.01, max_value=100000.0, key='ticket_limit', disabled=not st.session_state['limit_ticket'])
            st.checkbox('Apenas pedidos com desconto', key='discount_only')
        st.divider()
        st.caption('ATALHOS · 2023')
        st.button('Desconto · pedidos abaixo de R$ 250', on_click=preset, args=('discount',), width='stretch')
        st.button('Marketplace · comparação de canais', on_click=preset, args=('marketplace',), width='stretch')
        st.caption('Protótipo local • base histórica\nNenhuma alteração comercial automática')
    state = st.session_state
    try:
        scope = Scope(start=state.start.isoformat(), end=state.end.isoformat(), population=state.population,
            channel=None if state.channel=='Todos' else state.channel, category=None if state.category=='Todas' else state.category,
            ticket_lt=state.ticket_limit if state.limit_ticket else None, discounted_only=state.discount_only)
        metrics = room.metrics(scope)
    except ValueError as exc:
        st.error(str(exc)); st.stop()
    if state.page == PAGES[0]:
        st.markdown('<header class="page-heading"><h1>Control Tower</h1></header>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="eyebrow">VÉRTICE RETAIL &nbsp; / &nbsp; ANÁLISE DE RENTABILIDADE</div>', unsafe_allow_html=True)
    if scope.ticket_lt is not None or scope.discounted_only:
        st.caption(('Receita líquida histórica < '+brl(scope.ticket_lt)+' · ' if scope.ticket_lt else '')+('com desconto' if scope.discounted_only else 'com ou sem desconto'))
    if scope.population=='A':
        st.warning('População A inclui não aprovados e devolvidos. Valores registrados não comprovam realização financeira.')
    if scope.end >= '2024-01-01':
        st.warning('Janeiro de 2024 tem cobertura parcial na base. Compare períodos com cautela.')
    try:
        store = DecisionStore(os.environ.get('VERTICE_DB_PATH', str(ROOT/'prototipo/runtime/vertice.sqlite3')))
        page = PAGES.index(state.page)
        if page==0: tower(room, scope, metrics)
        elif page==1: investigate(room, scope, metrics)
        elif page==2: simulate(room, scope, store)
        elif page==3: copilot(room, scope, metrics)
        else: decisions(room, store)
    except (ValueError, OSError) as exc:
        st.error('Não foi possível concluir esta operação: '+str(exc))


if __name__=='__main__':
    main()
