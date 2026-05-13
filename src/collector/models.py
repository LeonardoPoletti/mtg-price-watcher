"""
models.py - Modelos Pydantic para dados da Scryfall API

Responsabilidade: definir e validar o formato dos dados que entram no pipeline
Nada que vem da API entra no sistema sem passar por aqui.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, field_validator

# ─────────────────────────────────────────────────────────────
# MODELO 1: Preços de uma carta
# Representa o objeto "prices" dentro de cada carta da Scryfall
# ─────────────────────────────────────────────────────────────

class CardPrices(BaseModel):
    """Preços de uma carta em diferentes versões e moedas."""

    usd: Optional[float] = None       # preço normal em dólar
    usd_foil: Optional[float] = None  # preço foil em dólar 
    eur: Optional[float] = None       # preço normal em euro
    eur_foil: Optional[float] = None  # preço foil em euro

    @field_validator("usd", "usd_foil", "eur", "eur_foil", mode="before")
    @classmethod
    def coverter_preco(cls, valor):
        """
        Converte string para float antes da validação.

        Por que isso é necessário?
        A Scryfall retorna preços como strings: "45000.00"
        Pydantic v2 não converte string -> float automaticamente por padrão.
        Este validator roda ANTES da validação de tipo (mode="before").
        """
        if valor is None or valor == "":
            return None
        try:
            return float(valor)
        except (ValueError, TypeError):
            return None   # se vier algo inesperado, trata como sem preço

# ─────────────────────────────────────────────────────────────
# MODELO 2: Carta completa da Scryfall
# Representa os campos de uma carta que nos interessam
# Ignoramos os outros 70+ campos que a API retorna
# ─────────────────────────────────────────────────────────────

class ScryfallCard(BaseModel):
    """
    Representa uma carta MTG conforme retornada pela Scryfall API.
    Contém apenas os campos relevantes para o pipeline de preços.
    """

    id: str                           # UUID único da carta na Scryfall
    name: str                         # nome da carta
    set: str                          # código do set (ex: "lea", "m21")
    set_name: str                     # nome completo do set
    rarity: str                       # common, uncommon, rare, mythic
    mana_cost: Optional[str] = None   # custo de mana (ex: "{2}{B}{B}")
    cmc: float = 0.0                  # custo de mana convertido (número)
    type_line: str = ""               # tipo da carta (ex: "Creature — Dragon")
    colors: list[str] = []            # cores da carta (ex: ["B", "R"])
    prices: CardPrices                # preços — usa o modelo acima

    class Config:
        # Permite que campos extras da API sejam ignorados silenciosamente
        # Sem isso, Pydantic v2 levanta erro para campos desconhecidos
        extra = "ignore"

# ─────────────────────────────────────────────────────────────
# MODELO 3: Registro de preço para armazenamento
# Representa uma linha no arquivo Parquet — achatado, sem aninhamento
# ─────────────────────────────────────────────────────────────
class CardPriceRecord(BaseModel):
    """
    Representa um registro de preço achatado para salvar em Parquet.

    Por que um modelo separado do ScryfallCard?
    ScryfallCard tem estrutura aninhada (prices dentro de card).
    Parquet trabalha melhor com estrutura plana (uma tabela com colunas simples).
    Este modelo 'achata' os dados para armazenamento eficiente.
    """

    card_id: str                      # UUID da carta (chave de relacionamento)
    card_name: str                    # nome da carta
    set_code: str                     # código do set
    set_name: str                     # nome do set
    rarity: str                       # raridade
    collected_at: date                # data da coleta — base do particionamento
    usd: Optional[float] = None       # preço normal USD
    usd_foil: Optional[float] = None  # preço foil USD
    eur: Optional[float] = None       # preço normal EUR
    eur_foil: Optional[float] = None  # preço foil EUR

    @classmethod
    def from_scryfall_card(cls, card: ScryfallCard, collected_at: date) -> "CardPriceRecord":
        """
        Cria um CardPriceRecord a partir de um ScryfallCard.

        Por que este método existe?
        Centraliza a lógica de conversão em um único lugar.
        Se a estrutura da Scryfall mudar, você muda só aqui.
        """
        return cls(
            card_id=card.id,
            card_name=card.name,
            set_code=card.set,
            set_name=card.set_name,
            rarity=card.rarity,
            collected_at=collected_at,
            usd=card.prices.usd,
            usd_foil=card.prices.usd_foil,
            eur=card.prices.eur,
            eur_foil=card.prices.eur_foil,
        )    