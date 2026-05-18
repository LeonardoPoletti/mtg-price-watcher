# MTG Price Watcher

Pipeline de dados para análise de preços de cartas Magic: The Gathering.

## Sobre o Projeto

Sistema completo de coleta, armazenamento e visualização de preços históricos de cartas MTG, consumindo dados da Scryfall API e armazenando em formato Parquet particionado por data.

**Stack:** Python · httpx · DuckDB · Parquet · Streamlit · Pydantic · Ruff · UV

## Arquitetura

```
mtg-price-watcher/
├── src/
│   ├── collector/
│   │   ├── scryfall_client.py   # Cliente HTTP da Scryfall API
│   │   └── models.py            # Modelos Pydantic de validação
│   ├── storage/
│   │   └── duckdb_handler.py    # Armazenamento Parquet + queries DuckDB
│   └── dashboard/
│       └── app.py               # Dashboard Streamlit
└── data/
    └── raw/prices/YYYY-MM-DD/   # Parquet particionado por data
```

**Fluxo de dados:**
```
Scryfall API → Validação Pydantic → Parquet → DuckDB → Streamlit
```

## Como Usar

### Pré-requisitos

- Python 3.12+
- [UV](https://github.com/astral-sh/uv) instalado

### Instalação

```bash
# Clone o repositório
git clone git@github.com:LeonardoPoletti/mtg-price-watcher.git
cd mtg-price-watcher

# Instale as dependências
uv sync
```

### Executar o Dashboard

```bash
uv run streamlit run src/dashboard/app.py
```

O dashboard abrirá automaticamente em `http://localhost:8501`.

## Funcionalidades

- ✅ Coleta automatizada de preços via Scryfall bulk data API
- ✅ Armazenamento em Parquet com particionamento por data
- ✅ Consultas analíticas com DuckDB (sem servidor!)
- ✅ Dashboard interativo com Streamlit
- ✅ Ranking de cartas mais caras (USD/EUR)
- ✅ Histórico de preço por carta com gráfico temporal
- ✅ Validação de dados com Pydantic

## 🛠Tecnologias

| Ferramenta | Papel |
|------------|-------|
| **httpx** | Cliente HTTP moderno para consumir a API |
| **DuckDB** | Banco analítico embarcado — processa Parquet sem servidor |
| **Parquet** | Formato colunar comprimido para armazenamento eficiente |
| **Pandas** | Bridge entre modelos Pydantic e DuckDB |
| **Streamlit** | Framework para dashboards em Python puro |
| **Pydantic** | Validação de dados na entrada do pipeline |
| **Ruff** | Linter e formatter ultra-rápido |
| **UV** | Gerenciador de projetos e dependências moderno |

## Decisões Técnicas

### Por que Full Load diário?

A Scryfall não expõe endpoint de mudanças incrementais. Preços atualizam 1x por dia via bulk data — a abordagem recomendada pela própria API. O incrementalismo está no **storage** (particionamento por data), não na coleta.

### Por que DuckDB?

- Sem servidor — roda direto no processo Python
- Processa Parquet nativamente com queries SQL
- Ideal para hardware limitado (HDD + 7GB RAM)
- Consulta múltiplos arquivos Parquet com wildcard: `FROM 'data/*/*.parquet'`

### Por que Parquet particionado por data?

- Cada dia fica isolado — reprocessar um dia não afeta os outros
- DuckDB lê todos os dias de uma vez para análises históricas
- Compressão eficiente (~90% menor que JSON)

## Desenvolvimento

```bash
# Rodar linter
uv run ruff check src/

# Corrigir automaticamente
uv run ruff check src/ --fix

# Formatar código
uv run ruff format src/

# Rodar testes (quando implementados)
uv run pytest
```

## Roadmap

- [ ] Testes com pytest
- [ ] Coleta automatizada via GitHub Actions
- [ ] API REST com FastAPI (Fase 2)
- [ ] Integração com dbt para transformações (Fase 2)
- [ ] Deploy do dashboard (Streamlit Cloud)

## Autor

**Leonardo José Poletti**  
Engenheiro de Dados | Portfólio KyberCorax

- LinkedIn: [leonardojosepoletti](https://www.linkedin.com/in/leonardojosepoletti/)
- GitHub: [@LeonardoPoletti](https://github.com/LeonardoPoletti)

## Licença

Projeto de portfólio — livre para uso educacional.