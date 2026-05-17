"""
app.py - Dashboard Streamlit do MTG Price Watcher

Para rodar: uv run streamlit run src/dashboard/app.py
"""

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

# Adiciona src/ ao path para importar os módulos
sys.path.insert(0, str(Path(__file__).parents[1]))

from storage.duckdb_handler import (
    get_historico_carta,
    get_top_caras,
    listar_datas_disponiveis,
)

# ─────────────────────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="MTG Price Watcher",
    page_icon="assets/mtg_icon.png",
    layout="wide",  # usa largura completa da tela
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────────────────────
# SIDEBAR — FILTROS E CONFIGURAÇÕES
# ─────────────────────────────────────────────────────────────

st.sidebar.title(" Filtros")

# Filtro: moeda
moeda = st.sidebar.radio(
    "Moeda para análise:",
    options=["usd", "eur"],
    format_func=lambda x: "Dólar (USD)" if x == "usd" else "Euro (EUR)",
    index=0,
)

# Filtro: quantidade de cartas no ranking
n_cartas = st.sidebar.slider(
    "Cartas no ranking:",
    min_value=5,
    max_value=50,
    value=20,
    step=5,
)

# Informações sobre o dataset
st.sidebar.markdown("---")
st.sidebar.subheader("  Dataset Info")

try:
    datas = listar_datas_disponiveis()
    if datas:
        st.sidebar.write(f"**Primeira coleta:** {datas[0]}")
        st.sidebar.write(f"**Última coleta:** {datas[-1]}")
        st.sidebar.write(f"**Total de dias:** {len(datas)}")
    else:
        st.sidebar.warning("Nenhum dado coletado ainda.")
except Exception as e:
    st.sidebar.error(f"Erro ao carregar info do dataset: {e}")


# ─────────────────────────────────────────────────────────────
# HEADER PRINCIPAL
# ─────────────────────────────────────────────────────────────

st.header("  MTG Price Watcher")
st.markdown(
    """
    Dashboard de análise de preços de cartas ** Magic: The Gathering**.
    Dados coletados via [Scryfall API] (https://scryfall.com/docs/api),
    armazenado em Parquet e consultados com DuckDB.    
    """
)

st.markdown("---")


# ─────────────────────────────────────────────────────────────
# SEÇÃO 1 — RANKING DE CARTAS MAIS CARAS
# ─────────────────────────────────────────────────────────────

st.header(f" Top {n_cartas} Cartas Mais Caras")

try:
    # Busca os dados
    top_cartas = get_top_caras(n=n_cartas, coluna_preco=moeda)

    if not top_cartas:
        st.warning("Nenhum dado disponível. Execute a coleta primerio")
        st.stop()

    # Exibe como tabela interativa
    st.dataframe(
        top_cartas,
        use_container_width=True,
        hide_index=True,
        column_config={
            "card_name": st.column_config.TextColumn("Carta", width="large"),
            "set_name": st.column_config.TextColumn("Set", width="medium"),
            "rarity": st.column_config.TextColumn("Raridade", width="small"),
            "preco": st.column_config.NumberColumn(
                "Preço" if moeda == "usd" else "Preço",
                format="$%.2f" if moeda == "usd" else "€%.2f",
            ),
            "collected_at": st.column_config.DateColumn("Data da Coleta"),
        },
    )

    # Estatísticas rápidas em colunas
    col1, col2, col3 = st.columns(3)
    with col1:
        preco_max = top_cartas[0]["preco"]
        st.metric(
            "Carta mais cara",
            f"${preco_max:,.2f}" if moeda == "usd" else f"€{preco_max:,.2f}",
        )
    with col2:
        preco_medio = sum(c["preco"] for c in top_cartas) / len(top_cartas)
        st.metric(
            "Preço médio (top)",
            f"${preco_medio:,.2f}" if moeda == "usd" else f"€{preco_medio:,.2f}",
        )
    with col3:
        carta_mais_cara = top_cartas[0]["card_name"]
        st.metric("Carta #1", carta_mais_cara)

except Exception as e:
    st.error(f"Erro ao carregar ranking: {e}")
    st.stop()

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# SEÇÃO 2 — HISTÓRICO DE PREÇO DE UMA CARTA ESPECÍFICA
# ─────────────────────────────────────────────────────────────

st.header(" Histórico de Preço")

# Input: nome da carta
carta_selecionada = st.text_input(
    "Digite o nome exato da carta:",
    value=top_cartas[0]["card_name"] if top_cartas else "Black Lotus",
    help="Nome exato como aparece no ranking acima",
)

if st.button("Buscar Histórico", type="primary"):
    try:
        historico = get_historico_carta(carta_selecionada)

        if not historico:
            st.warning(f"Nenhum histórico encontrado para '{carta_selecionada}1.")
        else:
            # Filtro pela moeda selecionada
            coluna_preco = moeda
            dados_grafico = [
                {"Data": h["collected_at"], "Preço": h[coluna_preco]}
                for h in historico
                if h[coluna_preco] is not None
            ]

            if not dados_grafico:
                st.warning(f"Sem dados de preço em {moeda.upper()} para esta carta.")
            else:
                # Gráfico com Plotly
                fig = px.line(
                    dados_grafico,
                    x="Data",
                    y="Preço",
                    title=f"Evolução do Preço - {carta_selecionada}",
                    markers=True,
                    labels={"Preço": f"Preço ({'USD' if moeda == 'usd' else 'EUR'})"},
                )

                # Customização visual
                fig.update_traces(
                    line_color="#1f77b4",
                    marker=dict(size=8, line=dict(width=1, color="white")),
                )
                fig.update_layout(
                    hovermode="x unified",
                    template="plotly_white",
                    height=500,
                )

                st.plotly_chart(fig, use_container_width=True)

                # Estatícas do histórico
                precos = [d["Preço"] for d in dados_grafico]
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(
                        "Preço inicial",
                        f"${precos[0]:,.2f}"
                        if moeda == "usd"
                        else f"€{precos[0]:,.2f}",
                    )
                with col2:
                    st.metric(
                        "Preco atual",
                        f"${precos[-1]:,.2f}"
                        if moeda == "usd"
                        else f"€{precos[-1]:,.2f}",
                    )
                with col3:
                    variacao = precos[-1] - precos[0]
                    st.metric(
                        "Variação absoluta",
                        f"${variacao:,.2f}" if moeda == "usd" else f"€{variacao:,.2f}",
                    )
                with col4:
                    variacao_pct = ((precos[-1] - precos[0]) / precos[0]) * 100
                    st.metric("Variação %", f"{variacao_pct:.2f}%")

    except Exception as e:
        st.error(f"Erro ao buscar histórico: {e}")

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────

st.markdown("---")
st.caption(
    "**Projeto:** MTG Price Watcher | "
    "**Desenvolvedor:** Leonardo José Poletti | "
    "**Stack:** Python · httpx · DuckDB · Parquet · Streamlit"
)
