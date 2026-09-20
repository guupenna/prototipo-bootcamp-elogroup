# Contexto governado — Vértice — revisão 16/09/2026

Fonte de produto: `Vertice_Retail_BusinessCase.pdf`, seções 9–14. Complemento técnico: `solucao/ESPECIFICACAO_PROTOTIPO.md`. Fonte dos cálculos: `prototipo/core.py` e contrato versionado. Memória auxilia contexto; não substitui consulta de dados.

## Solução

Profitability Control Tower monitora e governa; Order Margin Engine decompõe e simula; AI Investigation & Executive Copilot consulta, investiga e explica. Workflow e Decision Log preservam hipóteses e decisão humana. Primeira onda do Copilot: consulta/explicação/memo; investigações multi-etapa após avaliação.

## Dados e definições

- Briefing declara queda qualitativa de rentabilidade; não fornece queda numérica da Vértice.
- Vendas:1 pedido/linha,1 SKU associado,quantidade em unidades;2023 completo e janeiro/2024 parcial.
- A=todos os status na janela; B=aprovados sem devolução. B/2023 contém19.903 de26.538 pedidos. A proporção não é cobertura da MC.
- MC observável=receita líquida-custo produto-frete; MC%=razão de totais. Não é lucro.
- Frete registrado não é cobrança ao cliente. O padrão em R$250 não confirma política operacional. Valores positivos variam; não usar mediana como frete universal. Não inferir economia automática ao cruzar o limiar.
- Atendimento precisa de pedido+cliente+cronologia. Uma coorte de pedidos de2023 pode conter tickets abertos até2025. Tarifa registrada por canal; vínculo ausente não comprova custo zero. Frete já está na MC.
- Estoque é fotografia sem data; IDs válidos não autorizam explicação histórica de ruptura.
- Clientes: IDs cruzam, mas semântica/históricos precisam de reconciliação. Baixa cobertura ou concentração não prova ID falso, geração aleatória ou impossibilidade matemática de RFM descritivo.
- Marketing: ROAS interno calculável com ressalvas; conversões não comprovam novos clientes, portanto CAC de negócio não calculável. Sem atribuição campanha-pedido; não alocar MC causalmente por canal.

## Interpretação

Observação não prova causa; cenário não prevê resposta; exposição não é saving. Não calcular MC realizada pela subtração de devoluções de B. Falta economia pós-devolução, custos incorridos de cancelados e demais custos. Sem SLA prometido, tempo de entrega não identifica atraso. Motivos de devolução não dão percentual recuperável.

Comparação estratificada é descritiva, não teste causal. Hipóteses inconclusivas podem ser revisitadas com nova evidência. Populações e janelas devem acompanhar cada número. Retenção de equilíbrio M/(M+D) só com M>0 e premissas explícitas; nunca 1-D/M.

## Operação da IA

Consultar somente tools autorizadas; citar evidence_id, escopo, fonte e limitação. Não alterar fórmulas, executar código arbitrário, preencher lacunas, aprovar decisões ou publicar política comercial. Erro de tool não é evidência. Esgotamento de orçamento sem evidência deve gerar abstenção. Referência existente não certifica que a frase é sustentada: factualidade precisa de avaliação.

Resultados novos entram como propostas para revisão humana. Registros históricos obsoletos estão no backup e não podem alimentar o contexto ativo. Não usar memórias antigas como fontes de números sem novo cálculo.
