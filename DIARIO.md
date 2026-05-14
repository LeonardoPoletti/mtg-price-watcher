# DIARIO.md — MTG Price Watcher

> Projeto: P01 do portfólio KyberCorax
> Repositório: https://github.com/LeonardoPoletti/mtg-price-watcher
> Início: 2026-05-12
> Stack: Python · httpx · DuckDB · Parquet · Streamlit · UV · Git

---

## OBJETIVO DO PROJETO

Construir um pipeline de dados que coleta preços de cartas MTG via Scryfall API,
armazena histórico em Parquet particionado por data, consulta com DuckDB
e exibe em dashboard Streamlit.

**Resultado esperado:** projeto publicado no GitHub com README, dashboard funcional
e post no LinkedIn demonstrando o pipeline completo.

---

## ARQUITETURA DO PROJETO

```
mtg-price-watcher/
├── src/
│   ├── __init__.py
│   ├── collector/
│   │   ├── __init__.py
│   │   ├── scryfall_client.py   ← cliente HTTP da Scryfall API       ✅ FEITO
│   │   └── models.py            ← modelos Pydantic para validação     ✅ FEITO
│   ├── storage/
│   │   ├── __init__.py
│   │   └── duckdb_handler.py    ← leitura e escrita DuckDB + Parquet  ✅ FEITO
│   └── dashboard/
│       ├── __init__.py
│       └── app.py               ← Streamlit dashboard                 🔄 PRÓXIMO
├── data/
│   └── raw/prices/YYYY-MM-DD/  ← Parquet particionado por data (não vai ao Git)
├── notebooks/                   ← exploração e testes manuais (não vai ao Git)
├── docs/                        ← MkDocs (a implementar)
├── tests/
│   └── __init__.py
├── .env
├── .env.example
├── .gitignore
├── pyproject.toml               ← configuração UV, Ruff, Pytest       ✅ FEITO
├── uv.lock
└── README.md
```

**Fluxo de dados:**
```
Scryfall API → scryfall_client.py → Parquet (data/raw/) → DuckDB → Streamlit
```

---

## STACK E JUSTIFICATIVAS

| Ferramenta    | Papel                           | Por que esta e não outra                           |
|---------------|---------------------------------|----------------------------------------------------|
| Python        | Linguagem principal             | Padrão de mercado em dados                         |
| UV            | Gerenciador de projeto/deps     | Mais rápido que pip/poetry, padrão moderno         |
| httpx         | Cliente HTTP para a API         | Moderno, suporta async, substitui requests         |
| DuckDB        | Banco analítico embarcado       | Sem servidor, processa Parquet, rápido em HDD      |
| Parquet       | Formato de armazenamento        | Colunar, comprimido, padrão em engenharia de dados |
| Pandas        | Conversão de dados para DuckDB  | Bridge entre modelos Pydantic e DuckDB             |
| Streamlit     | Dashboard / visualização        | Python puro, rápido de construir, portfólio visual |
| Pydantic      | Validação de dados              | Garante integridade dos dados na entrada           |
| Ruff          | Linter e formatter              | Substitui flake8 + black + isort em uma ferramenta |
| Pytest        | Testes                          | Padrão de mercado em Python                        |
| Git + GitHub  | Controle de versão              | Obrigatório em qualquer empresa                    |

---

## PROGRESSO POR ETAPA

### ✅ ETAPA 1 — Configuração do Ambiente (CONCLUÍDA)

- [x] UV atualizado para 0.11.13
- [x] Git instalado (2.43.0) e configurado (user, email, editor, branch padrão)
- [x] Chave SSH gerada (ed25519) e adicionada ao GitHub
- [x] Diretório base: `/home/kybercorax/Documentos/kybercorax-datahub/`
- [x] Projeto inicializado com UV: `uv init mtg-price-watcher`
- [x] Estrutura de pastas criada (src/, data/, docs/, tests/, notebooks/)
- [x] Dependências instaladas e lockfile gerado
- [x] .gitignore configurado (exclui: .venv/, data/, .env, notebooks/, __pycache__)
- [x] Repositório criado no GitHub e primeiro commit enviado
- [x] main.py padrão do UV removido
- [x] VSCode configurado com extensões essenciais

---

### ✅ ETAPA 2 — pyproject.toml e Ruff (CONCLUÍDA)

- [x] Metadados preenchidos: nome, versão, descrição, autor, keywords
- [x] Dependências de produção: httpx, duckdb, streamlit, plotly, python-dotenv, pydantic, pandas
- [x] Dependências de dev: pytest, ruff
- [x] Ruff configurado: line-length=88, regras E/F/I/UP, quote-style=double
- [x] Pytest configurado: testpaths=["tests"], addopts="-v"

---

### ✅ ETAPA 3 — Modelos Pydantic — models.py (CONCLUÍDA)

**O que foi implementado:**

`CardPrices` — objeto de preços aninhado da Scryfall
- Campos: usd, usd_foil, eur, eur_foil (todos `float | None`)
- Validator `converter_preco`: converte string→float (API retorna preços como string)
- Usa `mode="before"`: roda ANTES da validação de tipo do Pydantic

`ScryfallCard` — carta completa vinda da API
- Campos: id, name, set, set_name, rarity, mana_cost, cmc, type_line, colors, prices
- `extra = "ignore"`: campos desconhecidos da API são descartados silenciosamente

`CardPriceRecord` — registro achatado para armazenamento em Parquet
- Estrutura plana (sem aninhamento) — ideal para formato tabular
- Campo `collected_at`: injetado pelo pipeline, não vem da API
- Método `from_scryfall_card()`: centraliza a conversão ScryfallCard → registro

**Conceitos aprendidos:**
- Separação de responsabilidades entre modelos (entrada / domínio / armazenamento)
- `@field_validator` com `mode="before"` para conversão de tipos na entrada
- `extra = "ignore"` para tolerância a campos desconhecidos da API
- `**dict` (unpacking): expande dicionário em argumentos nomeados
- `collected_at` é metadado de controle — responsabilidade do pipeline, não da fonte

**Teste realizado com sucesso:**
```
Nome: Black Lotus
Preço USD: 45000.0
Tipo do preço: <class 'float'>
collected_at: datetime.date(2026, 05, 12)
```

---

### ✅ ETAPA 4 — Cliente HTTP — scryfall_client.py (CONCLUÍDA)

**O que foi implementado:**

`ScryfallClient` — classe que encapsula toda comunicação com a Scryfall API

- `_get()` — método privado para GET com rate limit (0.1s entre chamadas)
- `get_bulk_data_url()` — consulta `/bulk-data`, extrai URL do arquivo `default_cards`
- `download_bulk_data()` — baixa arquivo via streaming em chunks de 8192 bytes
  - Verifica se arquivo do dia já existe (evita download duplo)
  - Exibe progresso a cada 10MB
- `parse_bulk_file()` — lê JSON, valida com Pydantic, retorna lista de CardPriceRecord
  - Descarta cartas sem nenhum preço registrado
  - Trata erros por carta sem interromper o pipeline

**Estratégia de coleta: Full Load diário**
```
Por que Full Load e não Incremental?
- Scryfall não expõe endpoint "só o que mudou hoje"
- Preços atualizam 1x por dia — bulk data é a abordagem recomendada
- Incrementalismo está no storage (Parquet particionado por data)
- Incremental load entra na Fase 2
```

**Teste realizado com sucesso:**
```
Consultando endpoint de bulk data...
Arquivo encontrado: 513.7 MB
URL obtida: https://data.scryfall.io/default-cards/default-cards-20260513090849.json
```

**Conceitos aprendidos:**
- `httpx.stream()` para download de arquivos grandes sem estourar memória RAM
- Download por chunks: 513MB baixado em pedaços de 8KB — pico de memória é 8KB
- `response.raise_for_status()` para tratamento automático de erros HTTP
- `User-Agent` como boa prática ao consumir APIs públicas
- JSON da Scryfall: `data["data"]` é lista de tipos de bulk; `item["type"] == "default_cards"` identifica o correto
- Sempre inspecionar o JSON da API antes de escrever código

---

### ✅ ETAPA 5 — Storage — duckdb_handler.py (CONCLUÍDA)

**O que foi implementado:**

`salvar_parquet()` — salva lista de CardPriceRecord em Parquet particionado por data
- Converte modelos Pydantic → DataFrame pandas → DuckDB → Parquet
- Usa `conn.register("df", df)` para registrar explicitamente (melhor que escopo implícito)
- Compressão Snappy: boa compressão com descompressão rápida
- Particionamento: `data/raw/prices/YYYY-MM-DD/cards.parquet`

`get_top_caras()` — retorna as N cartas mais caras da última coleta
- Usa CTE `ultima_data` para encontrar a data mais recente
- Wildcard `*` lê todos os arquivos Parquet de todas as datas

`get_historico_carta()` — histórico de preços de uma carta ao longo do tempo
- Parâmetro `?` para evitar SQL injection

`get_variacao_preco()` — variação absoluta e percentual entre primeira e última coleta

`listar_datas_disponiveis()` — datas com dados disponíveis (para o dashboard)

**Conceitos aprendidos:**
- DuckDB lê múltiplos Parquet com wildcard: `FROM 'data/raw/prices/*/*.parquet'`
- CTE (Common Table Expression): bloco nomeado que funciona como tabela temporária
  - Necessária porque `MAX()` não pode ser usado diretamente no `WHERE`
- `conn.register()`: registra DataFrame explicitamente para uso no SQL
- `zip(colunas, row)`: costura nome de coluna com valor da tupla → dict
- Ruff F841: variável atribuída mas não usada — resolvido com `conn.register()` explícito
- `Optional[float]` é sintaxe antiga — Ruff UP045 moderniza para `float | None`

---

### 🔄 ETAPA 6 — Dashboard — app.py (PRÓXIMO)

- [ ] Estrutura básica do Streamlit (página única)
- [ ] Tabela: top cartas mais caras
- [ ] Gráfico: histórico de preço de uma carta (Plotly)
- [ ] Filtros: moeda (usd/eur), quantidade de resultados

---

### 📋 ETAPA 7 — Testes e Qualidade (PENDENTE)

- [ ] Escrever ao menos 1 teste com pytest em tests/
- [ ] Garantir que Ruff passa em 100% dos arquivos
- [ ] README.md completo com arquitetura e como rodar

---

### 📋 ETAPA 8 — Publicação (PENDENTE)

- [ ] README.md com screenshot do dashboard
- [ ] Tag v1.0.0
- [ ] Post no LinkedIn

---

## DECISÕES TÉCNICAS REGISTRADAS

| Data       | Decisão                                     | Motivo                                                      |
|------------|---------------------------------------------|-------------------------------------------------------------|
| 2026-05-12 | Usar SSH ao invés de HTTPS no Git           | Elimina autenticação repetida no terminal                   |
| 2026-05-12 | Branch padrão `main` (não `master`)         | Padrão atual do GitHub desde 2020                           |
| 2026-05-12 | `data/` no .gitignore                       | Dados são artefatos, não código fonte                       |
| 2026-05-12 | Loguru adiado para Fase 2                   | Fase 1 usa fundamentos; Loguru entra no P07+                |
| 2026-05-12 | `uv.lock` commitado no Git                  | Garante reprodutibilidade do ambiente                       |
| 2026-05-12 | Remover `main.py` padrão do UV              | Não faz parte da arquitetura do projeto                     |
| 2026-05-12 | `notebooks/` no .gitignore                  | Exploração local, não é código de produção                  |
| 2026-05-13 | Full Load diário via bulk data              | Scryfall não expõe diff — bulk é a abordagem recomendada    |
| 2026-05-13 | Download via streaming (chunks de 8192B)    | Arquivo de 513MB — streaming evita estouro de RAM (7.7GB)   |
| 2026-05-13 | Descartar cartas sem preço no parse         | Cartas sem preço não contribuem para análise de mercado     |
| 2026-05-13 | Pandas como bridge Pydantic → DuckDB        | DuckDB não lê lista Python diretamente; DataFrame é o canal |
| 2026-05-13 | `conn.register()` explícito no DuckDB       | Evitar dependência de escopo implícito — explícito é melhor |
| 2026-05-13 | Particionamento por data no Parquet         | Permite reprocessar dia específico sem afetar os outros     |

---

## HISTÓRICO DE COMMITS

```
528334a  chore: project scaffold with UV, folder structure and dependencies
5033a81  chore: remove UV default main.py, not part of project architecture
7f8cfbb  docs: add project diary with architecture and progress tracking
de003d8  chore: add project metadata and configure ruff and pytest
c5187bb  chore: create folder notebooks/, add to gitignore
c23ceab  feat: add scryfall http client with bulk data download
fe580d6  docs: update project diary with progress through etapa 4
9853265  style: apply ruff fixes - use X|None syntax and sort imports
3c7138d  chore: add pandas as dependency for dataframe support
70b24f9  feat: add duckdb handler for parquet storage and price queries
(próximo) docs: update project diary with full progress etapas 1-5
(próximo) feat: add streamlit dashboard
```

---

## CONVENCIONAL COMMITS — REFERÊNCIA

| Prefixo    | Quando usar                                      |
|------------|--------------------------------------------------|
| feat:      | Nova funcionalidade                              |
| fix:       | Correção de bug                                  |
| chore:     | Tarefa de manutenção, configuração, build        |
| docs:      | Alteração em documentação                        |
| test:      | Adição ou modificação de testes                  |
| refactor:  | Refatoração sem mudança de comportamento         |
| style:     | Formatação, linting, sem mudança de lógica       |

---

## OBSERVAÇÕES E APRENDIZADOS

- Espaços em nomes de diretórios no Linux causam problemas em scripts e automações.
  Padrão correto: `kebab-case` (letras minúsculas com hífen).

- `src/` é versionado — é código criado pelo desenvolvedor.
  `data/` não é versionado — são artefatos gerados pela execução.

- `tests/` é exclusivo para arquivos pytest (`test_*.py`).
  Notebooks de exploração ficam em `notebooks/` (fora do Git).

- `collected_at` não vem da API — é metadado de controle injetado pelo pipeline.

- Pydantic v2 não converte string→float automaticamente.
  Usar `@field_validator(mode="before")` para conversões de tipo na entrada.

- Scryfall retorna preços como strings ("45000.00"), não como números.
  Sempre inspecionar o JSON da API antes de escrever código: `curl URL | python3 -m json.tool`

- Download de arquivos grandes: nunca usar `response.json()` ou `response.content`.
  Usar `httpx.stream()` + chunks para preservar RAM.

- DuckDB não lê lista Python diretamente no SQL.
  Converter para DataFrame e usar `conn.register()` explicitamente.

- CTE é necessária quando se precisa usar resultado de aggregate no WHERE.
  `WHERE col = MAX(col)` é inválido em SQL — use CTE ou subquery.

- `Optional[float]` é sintaxe legada. Python 3.10+ usa `float | None`.
  Ruff regra UP045 corrige automaticamente com `--fix`.

- Ruff F841 (variável não usada) revelou código implícito: DuckDB buscava `df`
  no escopo local via "mágica". Solução correta: `conn.register()` explícito.

---

*Atualizado em: 2026-05-13 | Projeto: MTG Price Watcher | KyberCorax*