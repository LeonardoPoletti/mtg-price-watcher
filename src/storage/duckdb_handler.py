"""
duckdb_handler.py - Armazenamento e consulta de dados com DuckDB e Parquet

Responsabilidade: salvar dados coletados em Parquet e consultar histórico.
Não sabe nada sobre a Scryfall API - Recebe registros prontos e os persiste.
"""

from datetime import date
from pathlib import Path

import duckdb

from collector.models import CardPriceRecord

# ─────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────

# Diretório raiz dos dados brutos
# Path(__file__) = caminho deste arquivo (duckdb_handler.py)
# .parents[2] = sobe 2 níveis: storage/ -> src/ -> raiz do projeto
DATA_DIR = Path(__file__).parents[2] / "data" / "raw" / "prices"

# ─────────────────────────────────────────────────────────────
# FUNÇÕES DE ESCRITA
# ─────────────────────────────────────────────────────────────


def salvar_parquet(
    records: list[CardPriceRecord], coleta_date: date | None = None
) -> Path:
    """
    Salva lista de CardPriceRecord em arquivo Parquet parcticionado por data.

    Estrutura gerada:
        data/raw/prices/2026-05-13/cards.parquet

    Por que particionar por data?
    Cada dia de coleta fica em seu próprio diretório.
    DuckDB consegue ler todos os dias de uma vez com wildcard.
    Se precisar reprocessar um dia específico, você só substitui aquela pasta.

    Args:
        records: lista de registros validados pelo Pydantic
        coleta_date: data da coleta (padrão: hoje)

    Returns:
        Path do arquivo Parquet salvo
    """
    import pandas as pd

    if coleta_date is None:
        coleta_date = date.today()

    # Cria o diretório da partição se não existir
    # ex: data/raw/prices/2026-05-13/
    partition_dir = DATA_DIR / coleta_date.strftime("%Y-%m-%d")
    partition_dir.mkdir(parents=True, exist_ok=True)

    output_path = partition_dir / "cards.parquet"

    # Converte lista de modelos Pydantic -> lista de dicts -> DataFrame
    # DuckDB consegue ler DataFrame diretamente no SQL (via variável local)
    df = pd.DataFrame([record.model_dump() for record in records])

    # DuckDB detecta a variável 'df' do escopo local e lê como tabela
    # O 'conn' aqui é uma conexão temporária - só para essa operação
    conn = duckdb.connect()

    # Registra o DataFrame explicitamente com um nome que o SQL vai usar
    # Isso é melhor que depender do DuckDB buscar variáveis no escopo local
    conn.register("df", df)

    # Escreve a tabela como arquivo Parquet com compressão snappy
    # Snappy é o padrão: boa compressão com descompressão rápida
    conn.execute(
        f"COPY (SELECT * FROM df) TO '{output_path}' (FORMAT PARQUET, COMPRESSION SNAPPY)"
    )

    conn.close()

    total = len(records)
    tamanho_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"Parquet salvo: {output_path}")
    print(f"Registros: {total} | Tamanho: {tamanho_mb:.2f} MB")

    return output_path


# ─────────────────────────────────────────────────────────────
# FUNÇÕES DE LEITURA (SQL ANALÍTICO)
# ─────────────────────────────────────────────────────────────


def get_top_cartas(n: int = 20, coluna_preco: str = "usd") -> list[dict]:
    """
    Returna as N cartas mais caras da útima coleta disponível.

    Args:
        n: quantidade de cartas a retornar
        coluna_preco: coluna de preço a usar (usd, usd_foil, eur, eur_foil)

    Returns:
        Lista de dicionários com card_name, set_name, rarity, preco, collected_at
    """
    # Wildcard lê TODOS os arquivos Parquet de todas as datas
    parquet_glob = str(DATA_DIR / "*" / "cards.parquet")

    conn = duckdb.connect()

    resultado = conn.execute(f"""
                            -- Pega a data mais recente disponível
                            WITH ultima_data AS (
                               SELECT MAX(collected_at) AS data_max
                               FROM '{parquet_glob}'
                               ),
                            -- Filtra só os registros da data mais recente
                            dados_recentes AS(
                                SELECT *
                                FROM '{parquet_glob}'
                                WHERE collected_at = (SELECT data_max FROM ultima_data)
                                    AND {coluna_preco} IS NOT NULL
                                )
                            
                                -- Retorna as N mais caras ordenada por preço
                                SELECT 
                                    card_name,
                                    set_name,
                                    rarity,
                                    {coluna_preco} AS preco,
                                    collected_at
                                FROM dados_recentes
                                ORDER BY preco DESC
                                LIMIT {n}
    """).fetchall()

    conn.close()

    # Converte tuplas para dicionários para facilitar uso no Streamlit
    colunas = ["card_name", "set_name", "rarity", "preco", "collected_at"]
    return [dict(zip(colunas, row)) for row in resultado]

    def get_historico_carta(card_name: str) -> list[dict]:
        """
        Retorna o histórico de preços de uma carta específica ao longo do tempo.

        Args:
            card_name: nome exato da carta (ex: "Black Lotus")

        Returns:
            Lista de dicionários com collected_at, usd, usd_foil, eur ordenados por data
        """
        parquet_glob = str(DATA_DIR / "*" / "cards.parquet")

        conn = duckdb.connect()

        resultado = conn.execute(
            f"""
                                SELECT
                                 collectec_at,
                                 usd,
                                 usd_foil,
                                 eur,
                                 eur_foil
                                FROM '{parquet_glob}'
                                WHERE card_name = ?
                                ORDER BY collected_at ASC
        """,
            [card_name],
        ).fetchall()

        conn.close()

        colunas = ["collected_at", "usd", "usd_foil", "eur", "eur_foil"]
        return [dict(zip(colunas, row)) for row in resultado]

    def get_variacao_preco(card_name: str) -> dict | None:
        """
        Returna a variação de preço de uma carta entre a primeira e a última coleta.

        Returns:
            Dicionário com preco_inicial, preco_final, variacao_absoluta,
            variacao_percentual e datas. Retorna None se não houver dados suficientes.
        """
        historico = get_historico_carta(card_name)

        # Precisa de pelo menos 2 pontos no tempo para calcular variação
        if len(historico) < 2:
            return None

        primeiro = historico[0]
        ultimo = historico[-1]

        preco_inicial = primeiro["usd"]
        preco_final = ultimo["usd"]

        # Ambos precisam ter preço USD para calcular variação
        if preco_inicial is None or preco_final is None:
            return None

        variacao_abs = preco_final = preco_inicial
        variacao_pct = ((preco_final - preco_inicial) / preco_inicial) * 100

        return {
            "card_name": card_name,
            "data_inicial": primeiro["collected_at"],
            "data_final": ultimo["collected_at"],
            "preco_inicial": preco_inicial,
            "preco_final": preco_final,
            "variacao_absoluta": round(variacao_abs, 2),
            "variacao_percentual": round(variacao_pct, 2),
        }

    def listar_datas_disponiveis() -> list[date]:
        """
        Retorna todas as datas com dados coletados disponíveis.

        Útil para o dashboard mostrar o ranking histórico disponível.
        """
        parquet_glob = str(DATA_DIR / "*" / "cards.parquet")

        conn = duckdb.connect()

        resultado = conn.execute(f"""
            SELECT DISTINCT collected_at
            FROM '{parquet_glob}'
            ORDER BY collected_at ASC
        """).fetchall()

        conn.close()

        return [row[0] for row in resultado]
