"""
collect.py - Script de coleta diária de preços MTG

Executa o pipeline completo:
1. Baixa bulk data da Scryfall
2. Valida com Pydantic
3. Salva em Parquet particionado por data

Uso: uv run python collect.py
"""

import sys
from datetime import date
from pathlib import Path

# Adiciona src/ ao path
sys.path.insert(0, "src")

from collector.scryfall_client import ScryfallClient
from storage.duckdb_handler import salvar_parquet

# ─────────────────────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────────────────────

# Diretória onde o bulk data será baixado temporariamente
DOWNLOAD_DIR = Path("data/raw")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────
# PIPELINE PRINCIPAL
# ─────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("MTG PRICE WATCHER - COLETA DE DADOS")
    print("=" * 60)
    print()

    # Etapa 1: Inicializa o cliente
    print("[1/4] Inicializando cliente Scryfall...")
    client = ScryfallClient()
    print(" Cliente pronto")
    print()

    # Etapa 2: Baixa o bulk data
    print("[2/4] Baixando bulk data da Scryfall...")
    print(" Este arquivo tem ~500MB. O download pode demorar alguns minutos.")
    try:
        arquivo_json = client.download_bulk_data(DOWNLOAD_DIR)
        print(f" Download concluído: {arquivo_json}")
    except Exception as e:
        print(f" Erro no download: {e}")
        return 1
    print()

    # Etapa 3: Parseeia e valida os dados
    print("[3/4] Parseando e validando dados com Pydantic...")
    print(" Processando -30.000 cartas. Isso pode demorar 1-2 minutos.")
    try:
        registros = client.parse_bulk_file(arquivo_json)
        print(f" Processamento concluído: {len(registros)} registros válidos")
    except Exception as e:
        print(f" Erro no processamento: {e}")
        return 1
    print()

    # Etapa 4: Salvar em Parquet
    print("[4/4] Salvando em Parquet particionado por data...")
    try:
        hoje = date.today()
        caminho_parquet = salvar_parquet(registros, coleta_date=hoje)
        print(f" Dados salvos: {caminho_parquet}")
    except Exception as e:
        print(f" Erro ao salvar: {e}")
        return 1
    print()

    print("=" * 60)
    print(" COLETA CONCLUÍDA COM SUCESSO!")
    print("=" * 60)
    print()
    print(f"Total de cartas coletadas: {len(registros)}")
    print(f"Data coleta: {hoje}")
    print(f"Arquivo: {caminho_parquet}")
    print()
    print("Execute o dashboard:")
    print(" uv run streamlit run src/dashboard/app.py")
    print()

    return 0

if __name__ == "__main__":
    exit(main())
