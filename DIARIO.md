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
│   │   └── duckdb_handler.py    ← leitura e escrita DuckDB + Parquet  🔄 PRÓXIMO
│   └── dashboard/
│       ├── __init__.py
│       └── app.py               ← Streamlit dashboard                 📋 PENDENTE
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

| Ferramenta    | Papel                          | Por que esta e não outra                          |
|---------------|--------------------------------|---------------------------------------------------|
| Python        | Linguagem principal            | Padrão de mercado em dados                        |
| UV            | Gerenciador de projeto/deps    | Mais rápido que pip/poetry, padrão moderno        |
| httpx         | Cliente HTTP para a API        | Moderno, suporta async, substitui requests        |
| DuckDB        | Banco analítico embarcado      | Sem servidor, processa Parquet, rápido em HDD     |
| Parquet       | Formato de armazenamento       | Colunar, comprimido, padrão em engenharia de dados|
| Streamlit     | Dashboard / visualização       | Python puro, rápido de construir, portfólio visual|
| Pydantic      | Validação de dados             | Garante integridade dos dados na entrada          |
| Ruff          | Linter e formatter             | Substitui flake8 + black + isort em uma ferramenta|
| Pytest        | Testes                         | Padrão de mercado em Python                       |
| Git + GitHub  | Controle de versão             | Obrigatório em qualquer empresa                   |

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
- [x] .gitignore configurado
- [x] Repositório criado no GitHub e primeiro commit enviado
- [x] main.py padrão do UV removido
- [x] VSCode configurado com extensões essenciais

---

### ✅ ETAPA 2 — pyproject.toml e Ruff (CONCLUÍDA)

- [x] Metadados do projeto preenchidos (nome, versão, descrição, autor)
- [x] Ruff configurado: line-length=88, regras E/F/I/UP, quote-style=double
- [x] Pytest configurado: testpaths=["tests"], addopts="-v"

---

### ✅ ETAPA 3 — Modelos Pydantic — models.py (CONCLUÍDA)

**O que foi implementado:**

`CardPrices` — objeto de preços aninhado da Scryfall
- Campos: usd, usd_foil, eur, eur_foil (todos Optional[float])
- Validator `converter_preco`: converte string→float (API retorna preços como string)

`ScryfallCard` — carta completa vinda da API
- Campos selecionados: id, name, set, set_name, rarity, mana_cost, cmc, type_line, colors, prices
- `extra = "ignore"`: campos desconhecidos da API são descartados silenciosamente

`CardPriceRecord` — registro achatado para armazenamento em Parquet
- Estrutura plana (sem aninhamento) — ideal para formato tabular
- Campo `collected_at`: injetado pelo pipeline, não vem da API
- Método `from_scryfall_card()`: centraliza a conversão ScryfallCard → registro

**Conceitos aprendidos:**
- Separação de responsabilidades entre modelos
- `@field_validator` com `mode="before"` para conversão de tipos
- `extra = "ignore"` para tolerância a campos desconhecidos da API
- `**dict` (unpacking) para instanciar modelos a partir de dicionários
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
- Preços atualizam 1x por dia — bulk data é a abordagem recomendada pela própria Scryfall
- Incrementalismo está no storage (Parquet particionado por data), não na coleta
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
- `response.raise_for_status()` para tratamento automático de erros HTTP
- Download por chunks: arquivo de 513MB é baixado em pedaços de 8KB
  Sem streaming, os 513MB seriam carregados inteiros na RAM antes de salvar
- `User-Agent` como boa prática ao consumir APIs públicas
- Por que a Scryfall usa `/bulk-data` em vez de requisição por carta

---

### 🔄 ETAPA 5 — Storage — duckdb_handler.py (EM ANDAMENTO)

**O que será implementado:**
- [ ] Salvar lista de `CardPriceRecord` como arquivo Parquet particionado por data
- [ ] Criar/conectar banco DuckDB
- [ ] Query: top cartas mais caras
- [ ] Query: histórico de preço de uma carta específica
- [ ] Query: variação de preço entre duas datas

---

### 📋 ETAPA 6 — Dashboard — app.py (PENDENTE)

- [ ] Estrutura básica Streamlit com múltiplas páginas
- [ ] Gráfico de histórico de preços (Plotly)
- [ ] Tabela top cartas mais caras
- [ ] Filtros interativos por set, raridade, cor

---

### 📋 ETAPA 7 — Testes e Qualidade (PENDENTE)

- [ ] Escrever ao menos 1 teste pytest em tests/
- [ ] Garantir que Ruff passa sem erros em src/
- [ ] README.md completo

---

### 📋 ETAPA 8 — Publicação (PENDENTE)

- [ ] README.md com arquitetura e instruções de execução
- [ ] Screenshot do dashboard no README
- [ ] Tag v1.0.0
- [ ] Post no LinkedIn

---

## DECISÕES TÉCNICAS REGISTRADAS

| Data       | Decisão                                  | Motivo                                                    |
|------------|------------------------------------------|-----------------------------------------------------------|
| 2026-05-12 | Usar SSH ao invés de HTTPS no Git        | Elimina autenticação repetida no terminal                 |
| 2026-05-12 | Branch padrão `main` (não `master`)      | Padrão atual do GitHub desde 2020                         |
| 2026-05-12 | `data/` no .gitignore                    | Dados são artefatos, não código fonte                     |
| 2026-05-12 | Loguru adiado para Fase 2                | Fase 1 usa fundamentos; Loguru entra no P07+              |
| 2026-05-12 | `uv.lock` commitado no Git               | Garante reprodutibilidade do ambiente                     |
| 2026-05-12 | Remover `main.py` padrão do UV           | Não faz parte da arquitetura do projeto                   |
| 2026-05-12 | `notebooks/` no .gitignore               | Exploração local, não é código de produção                |
| 2026-05-13 | Full Load diário via bulk data           | Scryfall não expõe diff — bulk é a abordagem recomendada  |
| 2026-05-13 | Download via streaming (chunks de 8192B) | Arquivo de 513MB — streaming evita estouro de RAM (7.7GB) |
| 2026-05-13 | Descartar cartas sem preço no parse      | Cartas sem preço não contribuem para análise de mercado   |

---

## CONVENCIONAL COMMITS — REFERÊNCIA

| Prefixo   | Quando usar                                      |
|-----------|--------------------------------------------------|
| feat:     | Nova funcionalidade                              |
| fix:      | Correção de bug                                  |
| chore:    | Tarefa de manutenção, configuração, build        |
| docs:     | Alteração em documentação                        |
| test:     | Adição ou modificação de testes                  |
| refactor: | Refatoração sem mudança de comportamento         |
| style:    | Formatação, ponto e vírgula, sem mudança lógica  |

---

## OBSERVAÇÕES E APRENDIZADOS

- Espaços em nomes de diretórios no Linux causam problemas em scripts.
  Padrão correto: `kebab-case` (letras minúsculas com hífen).

- `src/` é versionado — é código criado pelo desenvolvedor.
  `data/` não é versionado — são artefatos gerados pela execução.

- `tests/` é exclusivo para arquivos pytest (`test_*.py`).
  Notebooks de exploração ficam em `notebooks/` (fora do Git).

- `collected_at` não vem da API — é metadado de controle injetado pelo pipeline.

- Pydantic v2 não converte string→float automaticamente.
  Usar `@field_validator(mode="before")` para conversões de tipo na entrada.

- Scryfall retorna preços como strings ("45000.00"), não como números.
  Sempre valide o tipo dos dados na entrada — nunca assuma o formato da fonte.

- Download de arquivos grandes: nunca use `response.json()` ou `response.content`
  para arquivos grandes. Use `httpx.stream()` + chunks para preservar RAM.

---

*Atualizado em: 2026-05-13 | Projeto: MTG Price Watcher | KyberCorax*