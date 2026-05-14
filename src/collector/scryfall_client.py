"""
scryfall_client.py - Cliente HTTP para a Scryfall API

Responsabilidade: comunicação com a Scryfall API.
Faz as requisições, trata erros de rede, retorna dados validados pelos modelos.
Não sabe nada sobre armazenamento - isso é responsabilidade do duckdb_handler.
"""

import time
from datetime import date
from pathlib import Path

import httpx

from collector.models import CardPriceRecord, ScryfallCard

# ─────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────

# URL base da Scryfall API
BASE_URL = "https://api.scryfall.com"

# Intervalo mínimo entre requisições (segundos)
# Scryfall pede: não mais que 10 req/s. Usamos 0.1s = 10 req/s no máximo.
# Para o bulk data fazemos apenas 1-2 requisições, então isso é formalidade.
REQUEST_DELAY = 0.1

# Timeout em segundos para requsições normais
TIMEOUT_SECONDS = 30

# Timeout para o download do bulk data (arquivo grande - pode demorar)
BULK_DOWNLOAD_TIMEOUT = 300  # 5 minutos


# ─────────────────────────────────────────────────────────────
# CLIENTE PRINCIPAL
# ─────────────────────────────────────────────────────────────


class ScryfallClient:
    """
    Cliente para a Scryfall API.

    Encapsula toda comunicação com a API em uma classe.
    Por que uma classe e não funções soltas?
    Porque o cliente precisa de estado: headers padrão, configuração
    de timeout, e no futuro - rate limiting com estado compartilhado.
    """

    def __init__(self):
        # Headers padrão para todas as requisições
        # Scryfall pede que você identifique seu projeto no User-Agent
        self.headers = {
            "User-Agent": "mtg-price-watcher/0.1.0 (portfolio project)",
            "Accept": "application/json",
        }

    def _get(self, url: str, timeout: int = TIMEOUT_SECONDS) -> dict:
        """
        Faz uma requisição GET e retorna o JSON como dicionário.

        Por que método privado (prefixo _)?
        É um detalhe de implementação interno da classe.
        Quem usa o ScryfallClient não precisa chamar _get diretamente.

        Args:
            url: URL completa para requisitar
            timeout: segundos até desistir da requisição

        Returns:
            Dicionário com o JSON de resposta

        Raises:
            httpx.HTTPStatusError: se a API retornar 4xx ou 5xx
            htppx.TimeoutException: se a requisição demorar demais
        """
        # Respeita o rate limit antes de cada requisição
        time.sleep(REQUEST_DELAY)

        response = httpx.get(url, headers=self.headers, timeout=timeout)

        # Levanta exeção automaticamente se status >= 400
        # Sem isso, uma resposta 404 será tratada como sucesso
        response.raise_for_status()

        return response.json()

    def get_bulk_data_url(self) -> str:
        """
        Consulta a Scryfall para obter a URL tual do arquivo bulk 'default_cards'.

        Por que não hardcodar a URL do arquivo?
        A Scryfall atualiza o arquivo diariamente e a URL muda.
        Este endpoint /bulk-data sempre aponta para a versão mais recente.

        Returns:
            URL do arquivo JSON com todas as cartas
        """

        print("Consultando emdpoint de bulk data...")
        data = self._get(f"{BASE_URL}/bulk-data")

        # O endpoint retorna uma lista de tipos de bulk data disponíveis
        # Precisamos do 'default_cards": todas as cartas, uma impressão por carta
        for item in data["data"]:
            if item["type"] == "default_cards":
                url = item["download_uri"]
                size_mb = item["size"] / (1024 * 1024)
                print(f"Arquivo encontrado: {size_mb:.1f} MB")
                return url

        raise ValueError("Tipo 'default_cards' não encontrado no bulk data endpoint")

    def download_bulk_data(self, download_path: Path) -> Path:
        """
        Baixa o arquivo bulk data da Scryfall e salva localmente.

        Usa streaming para não carregar o arquivo inteiro na memória.
        O arquivo tem ~250mb descomprimedo - importante para o seu hardware.

        Args:
            download_path: diretório onde o arquivo será salvo

        Returns:
            Path do arquivo salvo
        """
        url = self.get_bulk_data_url()
        today = date.today().strftime("%Y-%m-%d")
        output_file = download_path / f"scryfall_bulk_{today}.json"

        # Não baixa de novo se já existe oarquivo de hoje
        if output_file.exists():
            print(f"Arquivo de hoje já existe: {output_file}")
            return output_file

        print(f"Baixanod bulk data pra {output_file}...")

        # stream=True -> baixa em pedaçõs, não carrega tudo na memória
        with httpx.stream(
            "GET", url, headers=self.headers, timeout=BULK_DOWNLOAD_TIMEOUT
        ) as response:
            response.raise_for_status()

            total = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(output_file, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Monstra progress a cada 10MB
                    if total and downloaded % (10 * 1024 * 1024) < 8192:
                        pct = (downloaded / total) * 100
                        print(
                            f"  {pct:0f}% ({downloaded / 1024 / 1024:.0f}MB / {total / 1024 / 1024:.0f}MB)"
                        )

        print(f"Download concluído: {output_file}")
        return output_file

    def parse_bulk_file(self, file_path: Path) -> list[CardPriceRecord]:
        """
        Lê o arquivo bulk JSON e converte para lista de CardPriceRecord.

        Esta função é o ponto de integração entre:
        - O arquivo bruto da Scryfall (JSON gigante)
        - Os modelos Pydantic (validação)
        - O CardPrinceRecord (formato para Parquet)

        Args:
            file_path: caminho do arquivo JSON baixado

        Returns:
            Lista de CardPriceRecord prontos para salvar em Parquet
        """
        import json

        today = date.today()
        records = []
        erros = 0

        print(f"Processando arquivo: {file_path}")

        with open(file_path, encoding="utf-8") as f:
            cartas_brutas = json.load(f)

        print(f"Total de cartas no arquivo: {len(cartas_brutas)}")

        for carta_bruta in cartas_brutas:
            try:
                # Valida com Pydantic - descarta cartas com dados inválidos
                carta = ScryfallCard(**carta_bruta)

                # Só processa cartas que têm pelo menos um preço registrado
                tem_preco = any(
                    [
                        carta.prices.usd,
                        carta.prices.usd_foil,
                        carta.prices.eur,
                        carta.prices.eur_foil,
                    ]
                )
                if not tem_preco:
                    continue

                # Converte para o formato de armazenamento
                record = CardPriceRecord.from_scryfall_card(carta, today)
                records.append(record)

            except Exception:
                # Carta com problema - conta o erro mas não para o pipeline
                erros += 1
                continue

        print(f"Cartas com preço: {len(records)}")
        print(f"Catas ignoradas (sem preço ou erro): {erros}")

        return records
