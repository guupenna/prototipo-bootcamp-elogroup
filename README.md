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

## Executar localmente

Você precisa de **Python 3.12** e internet para instalar as dependências. Baixe ou clone o repositório e abra o terminal na pasta raiz.

Crie um ambiente virtual:

```bash
python -m venv .venv
```

> No Linux/macOS, use `python3` se o comando `python` não estiver disponível.

**Windows — PowerShell ou Prompt de Comando**

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


## Estrutura

```text
.
├── prototipo/             # Aplicação, cálculos e registro de decisões
│   ├── app.py
│   ├── requirements.txt
│   ├── GUIA_DE_USO.md
│   └── contratos/
├── data-room/
│   ├── vendas.csv
│   └── atendimento.csv
└── .streamlit/
    └── config.toml        # Tema e configuração do servidor
```

Mantenha as pastas nessa disposição. As decisões são salvas localmente em `prototipo/runtime/`, criada ao executar, e não são compartilhadas automaticamente entre computadores.

**Stack:** Python · pandas · Streamlit · Plotly · SQLite · API de IA
