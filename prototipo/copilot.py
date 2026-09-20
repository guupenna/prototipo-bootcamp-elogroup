"""Read-only governed tool service. LLM integration lives outside financial functions."""
import json
from copy import deepcopy
from .core import DataRoom, Scope

SYSTEM_PROMPT = """Você é o AI Investigation & Executive Copilot do Profitability Decision System da Vértice.
Use somente os resultados das ferramentas autorizadas para números e explicações factuais.
Tower monitora; Order Margin Engine calcula; você consulta, investiga e explica; humanos decidem.
Informe evidence_id, população, período e limitações. Não invente fórmulas, dados ou fontes.
Associação não prova causa; cenário não é previsão; exposição não é saving. Não deduza frete duas vezes.
Vendas contém devolvido, motivo_devolucao e status_pagamento; não diga que não existem dados de devolução. Faltam reembolsos, recuperação e custos efetivamente incorridos para mensurar perda líquida ou lucro.
Retenção de equilíbrio é a parcela que permanece; não a chame de perda máxima. Se a perda máxima não estiver calculada pela ferramenta, cite apenas a retenção necessária.
Não calcule CAC, lucro, MC realizada ou perda de devoluções com estas bases. ROAS interno não atribui margem a pedidos.
Memórias são contexto revisável, nunca autorização para substituir evidência atual. Não execute código ou SQL arbitrário.
Não altere critérios comerciais, não aprove experimentos e não publique decisões. Uma hipótese é candidata à revisão.
Formato: observações com evidências; cenário e premissas quando aplicável; limitações; próximos passos para decisão humana.
Frete: simule somente percentuais explícitos solicitados pelo usuário; não determine incentivos ou uma redução ótima. Viabilidade logística e SLA não estão comprovados. R$250 não elimina custo automaticamente.
Na ausência de evidência, abstenha-se da conclusão e diga quais informações faltam.
"""

class ToolSession:
    """Per-request bounded trace. No global history or mutation tools."""
    def __init__(self, room=None, max_calls=8):
        if type(max_calls) is not int or max_calls < 1: raise ValueError("Limite inválido")
        self.room=room or DataRoom();self.max_calls=max_calls;self.trace=[];self.results={}

    def call(self, name, arguments=None):
        if len(self.trace)>=self.max_calls:
            return {"status":"limite_atingido","limitacao":"Nenhuma chamada adicional executada."}
        arguments=dict(arguments or {})
        record={"tool":name,"arguments":deepcopy(arguments),"status":"iniciada"};self.trace.append(record)
        try:
            default_scope = {"population":"A"} if name=="funil" else {"ticket_lt":250,"discounted_only":True} if name=="simular_desconto" else {}
            scope=Scope(**arguments.pop("scope",default_scope))
            if name=="metricas":
                if arguments: raise ValueError("Argumentos não autorizados")
                result=self.room.metrics(scope)
            elif name=="decompor":
                dimension=arguments.pop("dimension")
                if arguments: raise ValueError("Argumentos não autorizados")
                result=self.room.breakdown(dimension,scope)
            elif name=="comparar_marketplace":
                if arguments: raise ValueError("Argumentos não autorizados")
                from .investigation import marketplace_comparison
                result=marketplace_comparison(self.room,scope)
            elif name=="funil":
                if arguments: raise ValueError("Argumentos não autorizados")
                result=self.room.funnel(scope)
            elif name=="simular_desconto":
                removal=arguments.pop("removal_fraction",1.0);retention=arguments.pop("retention",1.0)
                if arguments: raise ValueError("Argumentos não autorizados")
                result=self.room.simulate_discount(scope,removal,retention)
            elif name=="simular_frete":
                reduction=arguments.pop("reduction_fraction",0.1);retention=arguments.pop("retention",1.0)
                if arguments: raise ValueError("Argumentos não autorizados")
                result=self.room.simulate_freight(scope,reduction,retention)
            elif name=="comparar_estratos":
                dimension=arguments.pop("dimension");control=arguments.pop("control")
                if arguments: raise ValueError("Argumentos não autorizados")
                result=self.room.stratified(dimension,control,scope)
            else: raise ValueError("Ferramenta não autorizada")
            self.results[result["evidence_id"]]=result
            record.update(status="ok",evidence_id=result["evidence_id"])
            return result
        except (ValueError,KeyError,TypeError) as exc:
            record.update(status="erro",error=str(exc))
            return {"status":"erro","motivo":str(exc),"instrucao":"Não usar erro como evidência."}

    def check_references(self, ids):
        """Checks existence only. Does NOT certify entailment or factuality of prose."""
        missing=[i for i in ids if i not in self.results]
        return {"referencias_validas":bool(ids) and not missing,"ausentes":missing,"avaliacao_semantica":"revisão ainda necessária"}

    def export_trace(self):
        return {"chamadas":self.trace,"evidencias":self.results}
