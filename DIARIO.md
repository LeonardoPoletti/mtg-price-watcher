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
│   │   ├── scryfall_client.py   ← cliente HTTP da Scryfall API
│   │   └── models.py            ← modelos Pydantic para validação
│   ├── storage/
│   │   ├── __init__.py
│   │   └── duckdb_handler.py    ← leitura e escrita DuckDB + Parquet
│   └── dashboard/
│       ├── __init__.py
│       └── app.py               ← Streamlit dashboard
├── data/
│   └── raw/prices/YYYY-MM-DD/  ← Parquet particionado por data (não vai ao Git)
├── docs/                        ← MkDocs (a implementar)
├── tests/
│   └── __init__.py
├── .env                         ← variáveis de ambiente locais (não vai ao Git)
├── .env.example                 ← template de variáveis (vai ao Git)
├── .gitignore
├── pyproject.toml               ← configuração UV e dependências
├── uv.lock                      ← lock de dependências (vai ao Git)
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

## FASE ATUAL: CONFIGURAÇÃO DO AMBIENTE

### ✅ CONCLUÍDO

#### Ambiente base
- [x] UV atualizado para 0.11.13
- [x] Git instalado (2.43.0) e configurado
  - user.name = Leonardo Jose Poletti
  - user.email = leonardojpoletti@gmail.com
  - core.editor = code --wait
  - init.defaultBranch = main
- [x] Chave SSH gerada (ed25519) e adicionada ao GitHub
- [x] Conexão SSH com GitHub testada e funcionando

#### Projeto
- [x] Diretório base criado: `/home/kybercorax/Documentos/kybercorax-datahub/`
- [x] Projeto inicializado com UV: `uv init mtg-price-watcher`
- [x] Estrutura de pastas criada (src/, data/, docs/, tests/)
- [x] Arquivos Python criados (todos vazios por enquanto)
- [x] Dependências instaladas:
  - httpx
  - duckdb
  - streamlit
  - plotly
  - python-dotenv
  - pydantic
  - pytest (dev)
  - ruff (dev)
- [x] .gitignore configurado (exclui: .venv/, data/, .env, __pycache__, etc.)
- [x] Repositório criado no GitHub: `LeonardoPoletti/mtg-price-watcher`
- [x] Primeiro commit enviado: `chore: project scaffold with UV, folder structure and dependencies`
- [x] main.py padrão do UV removido
- [x] VSCode configurado com extensões essenciais

---

### 🔄 EM ANDAMENTO

#### Próxima etapa: Revisar pyproject.toml
- Adicionar metadados do projeto
- Configurar Ruff com as regras certas

---

### 📋 PRÓXIMOS PASSOS (em ordem)

#### Etapa 2 — pyproject.toml e configuração do Ruff
- [ ] Revisar e completar metadados no pyproject.toml
- [ ] Configurar Ruff (linting + formatting)
- [ ] Criar commit: `chore: configure ruff and project metadata`

#### Etapa 3 — Modelos Pydantic (models.py)
- [ ] Criar modelo `ScryfallCard` com os campos necessários
- [ ] Criar modelo `CardPrice` para histórico de preços
- [ ] Entender: o que é Pydantic e por que validar dados na entrada

#### Etapa 4 — Cliente HTTP (scryfall_client.py)
- [ ] Entender a Scryfall API (estrutura, endpoints, rate limits)
- [ ] Implementar função de busca de cartas
- [ ] Implementar paginação
- [ ] Tratar erros de HTTP

#### Etapa 5 — Storage (duckdb_handler.py)
- [ ] Entender DuckDB + Parquet na prática
- [ ] Implementar escrita de dados em Parquet
- [ ] Implementar leitura com SQL analítico
- [ ] Entender particionamento por data

#### Etapa 6 — Dashboard (app.py)
- [ ] Estrutura básica do Streamlit
- [ ] Gráfico de histórico de preços
- [ ] Tabela top cartas mais caras
- [ ] Filtros interativos

#### Etapa 7 — Testes e qualidade
- [ ] Escrever ao menos 1 teste com pytest
- [ ] Garantir que o Ruff passa sem erros
- [ ] Revisar README.md

#### Etapa 8 — Publicação
- [ ] README.md completo com arquitetura e como rodar
- [ ] Screenshot do dashboard no README
- [ ] Tag de versão v1.0.0
- [ ] Post no LinkedIn

---

## DECISÕES TÉCNICAS REGISTRADAS

| Data       | Decisão                              | Motivo                                              |
|------------|--------------------------------------|-----------------------------------------------------|
| 2026-05-12 | Usar SSH ao invés de HTTPS no Git    | Elimina autenticação repetida no terminal           |
| 2026-05-12 | Branch padrão `main` (não `master`)  | Padrão atual do GitHub desde 2020                  |
| 2026-05-12 | data/ no .gitignore                  | Dados são artefatos, não código fonte               |
| 2026-05-12 | Loguru adiado para Fase 2            | Fase 1 usa fundamentos; Loguru entra no P07+        |
| 2026-05-12 | uv.lock commitado no Git             | Garante reprodutibilidade do ambiente               |
| 2026-05-12 | Remover main.py padrão do UV         | Não faz parte da arquitetura do projeto             |

---

## COMMITS REALIZADOS

```
528334a  chore: project scaffold with UV, folder structure and dependencies
```

---

## CONVENCIONAL COMMITS — REFERÊNCIA

Padrão usado neste projeto para mensagens de commit:

| Prefixo  | Quando usar                                      |
|----------|--------------------------------------------------|
| feat:    | Nova funcionalidade                              |
| fix:     | Correção de bug                                  |
| chore:   | Tarefa de manutenção, configuração, build        |
| docs:    | Alteração em documentação                        |
| test:    | Adição ou modificação de testes                  |
| refactor:| Refatoração sem mudança de comportamento         |
| style:   | Formatação, ponto e vírgula, sem mudança lógica  |

---

## OBSERVAÇÕES E APRENDIZADOS

- Espaços em nomes de diretórios no Linux causam problemas em scripts e automações.
  Padrão correto: `kebab-case` (letras minúsculas com hífen).

- `src/` é versionado porque é código que você criou.
  `data/` não é versionado porque são artefatos gerados pela execução.

- `uv.lock` deve ser commitado — garante que todos os colaboradores usem
  exatamente as mesmas versões de dependências.

---

*Atualizado em: 2026-05-12 | Projeto: MTG Price Watcher | KyberCorax*