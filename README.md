# vértice

### Inteligência de margem

Protótipo desenvolvido para o case **Vértice Retail**, no Bootcamp da EloGroup. Um ambiente para explorar a margem dos pedidos, avaliar cenários e preparar decisões com evidências.

**Analisar → Investigar → Simular → Decidir**

---

## O que você encontra

- **Control Tower:** indicadores, gráficos e comparação do recorte selecionado com o total.
- **Explorar:** análise da margem por canal, categoria e outros grupos.
- **Order Margin Engine:** simulações de desconto e custo de frete, com premissas explícitas.
- **AI Investigation & Executive Copilot:** consultas e explicações com referências aos cálculos.
- **Decisões:** registro de hipóteses, cenários e revisões humanas.

Os resultados das simulações são condicionais às premissas. Não representam ganhos comprovados, e nenhuma política comercial é executada automaticamente.

## Documentação da entrega

Este repositório reúne a entrega do projeto: **business case, protótipo e notebooks de análise**.

O **[documentacao.zip](documentacao.zip)**, disponível na raiz, contém o business case atualizado. Baixe e extraia o arquivo para consultar a documentação da solução. As análises estão em [`analises/`](analises/), e o código do sistema está em [`prototipo/`](prototipo/).

## Análises e evidências

A pasta [`analises/`](analises/) reúne os notebooks que documentam a análise e a exploração técnica do projeto:

- **[EDA do Data Room](analises/EDA_data_room.ipynb):** qualidade e integração das bases, análise exploratória, hipóteses, cenários e limitações que sustentam a proposta.
- **[Agente ReAct com memória](analises/agente_ReAct_memoria.ipynb):** estrutura de investigação com ferramentas de cálculo e memória, com verificações locais. As missões de IA estão desativadas na versão entregue; esse notebook documenta a implementação técnica, não uma nova rodada de descobertas geradas pelo modelo.

Os notebooks incluem resultados salvos e podem ser visualizados no GitHub sem executar código. Para reexecutá-los, use Jupyter ou VS Code e mantenha a estrutura do projeto: a EDA requer os cinco CSVs de `data-room/`; o ReAct também requer as memórias de `agente/` e dependências adicionais de LangChain/LangGraph. As dependências do aplicativo abaixo não incluem necessariamente todas as dependências dos notebooks.

## Executar localmente

Crie um ambiente virtual:

```bash
python -m venv .venv
```

**Windows**

```powershell
.venv\Scripts\python.exe -m pip install -r prototipo/requirements.txt
.venv\Scripts\python.exe -m streamlit run prototipo/app.py
```

**Linux ou macOS**

```bash
.venv/bin/python -m pip install -r prototipo/requirements.txt
.venv/bin/python -m streamlit run prototipo/app.py
```

Abra **[localhost:8501](http://localhost:8501)** no navegador. Para encerrar, pressione `Ctrl+C` no terminal.

## Ativar o Copilot (opcional)

Painéis, simulações, resumo sem IA e registro de decisões funcionam sem uma chave de API.

Para usar o **EloAgents**, crie `.streamlit/secrets.toml` na raiz do repositório:

```toml
VERTICE_API_KEY = "SUA_CHAVE"
VERTICE_API_BASE_URL = "https://chat.eloagents.click/api"
VERTICE_MODEL = "claude-opus-47"
```

O modelo acima é o usado nesta implementação; sua disponibilidade depende do acesso fornecido pelo bootcamp. Salve o arquivo e reinicie o aplicativo. As consultas usam os créditos do provedor.

Essa configuração ativa o Copilot do aplicativo. O notebook ReAct utiliza variáveis de ambiente e a opção `EXECUTAR_LLM`, conforme suas próprias instruções.

## Estrutura

```text
.
├── documentacao.zip       # Business case
├── prototipo/             # Aplicação, cálculos e registro de decisões
│   ├── app.py
│   ├── requirements.txt
│   ├── GUIA_DE_USO.md
│   └── contratos/
├── analises/              # Notebooks com resultados salvos
│   ├── EDA_data_room.ipynb
│   └── agente_ReAct_memoria.ipynb
├── agente/                # Memórias usadas pelo notebook ReAct
│   ├── memoria_semantica.md
│   └── memoria_episodica.json
├── data-room/
│   ├── vendas.csv
│   ├── atendimento.csv
│   ├── clientes.csv
│   ├── marketing.csv
│   └── estoque.csv
└── .streamlit/
    └── config.toml        # Tema e configuração do servidor
```

Mantenha as pastas nessa disposição. O aplicativo utiliza `vendas.csv` e `atendimento.csv`; os demais CSVs são usados pela EDA. As decisões são salvas localmente em `prototipo/runtime/`, criada ao executar, e não são compartilhadas automaticamente entre computadores.

**Stack:** Python · pandas · Streamlit · Plotly · SQLite · API de IA
