"""
U.S. Energy Markets Dashboard — Streamlit front end.

Run locally:
    streamlit run app.py

It reads EIA_API_KEY from the environment (or a .env file). Data is cached for
an hour so re-runs and widget changes don't re-hit the API.
"""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from analytics import days_of_supply, latest_change
from charts import line_chart, line_chart_with_ma, seasonal_chart
from config import SERIES_BY_KEY, Brand, Series
from eia_client import EIAClient, EIAError

load_dotenv()

st.set_page_config(page_title="U.S. Energy Markets Dashboard",
                   page_icon="▲", layout="wide")


# --------------------------------------------------------------------------
# Brand: inject fonts + dark "energy desk" theme. Keeps the look consistent
# even though Streamlit's native theming is limited.
# --------------------------------------------------------------------------
def inject_brand() -> None:
    st.markdown(f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500&family=IBM+Plex+Mono:wght@500&display=swap');
      .stApp {{ background: {Brand.INK}; color: {Brand.TEXT}; }}
      [data-testid="stSidebar"] {{ background: {Brand.PANEL}; border-right: 1px solid {Brand.GRID}; color: {Brand.TEXT}; }}
      [data-testid="stSidebar"] * {{ color: {Brand.TEXT} !important; background: transparent !important; }}
      h1, h2, h3 {{ font-family: '{Brand.FONT_DISPLAY}', sans-serif !important;
                    color: {Brand.TEXT}; letter-spacing: -0.01em; }}
      .block-container {{ padding-top: 4.5rem; max-width: 1280px; }}
      .kpi {{ background: {Brand.INK}; border: 1px solid {Brand.GRID};
              border-left: 3px solid {Brand.CRUDE};
              border-radius: 6px; padding: 14px 16px; height: 100%; }}
      .kpi .name {{ color: {Brand.MUTED}; font-size: 11px; font-weight: 600;
                    text-transform: uppercase; letter-spacing: 0.06em; }}
      .kpi .val {{ font-family: '{Brand.FONT_MONO}', monospace; font-size: 26px;
                   color: {Brand.TEXT}; margin: 4px 0 2px; }}
      .kpi .unit {{ color: {Brand.MUTED}; font-size: 12px; }}
      .kpi .delta {{ font-family: '{Brand.FONT_MONO}', monospace; font-size: 13px; }}
      .up {{ color: {Brand.UP}; }} .down {{ color: {Brand.DOWN}; }}
      .eyebrow {{ color: {Brand.CRUDE}; font-family: '{Brand.FONT_MONO}', monospace;
                  font-size: 12px; letter-spacing: 0.12em; text-transform: uppercase; }}
      button[data-baseweb="tab"] {{ color: {Brand.MUTED} !important; font-weight: 500; }}
      button[data-baseweb="tab"][aria-selected="true"] {{ color: {Brand.CRUDE} !important; font-weight: 600; }}
      div.stSlider > div[data-baseweb="slider"] > div:first-child > div {{ background: {Brand.CRUDE} !important; }}
      #MainMenu {{visibility: hidden;}} header {{visibility: visible;}} footer {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)


@st.cache_resource
def get_client() -> EIAClient:
    return EIAClient(api_key=os.getenv("EIA_API_KEY", ""))


@st.cache_data(ttl=3600, show_spinner=False)
def load_series(eia_id: str, start: str) -> pd.DataFrame:
    """Cached fetch. Cache key is (eia_id, start), so each series caches once/hr."""
    return get_client().fetch(eia_id, start=start)


def download_button(keys: list[str], data: dict, filename: str) -> None:
    """Merge selected series into one CSV and render a Streamlit download button."""
    frames = []
    for k in keys:
        df = data[k]
        if not df.empty:
            frames.append(df["value"].rename(SERIES_BY_KEY[k].label))
    if not frames:
        return
    combined = pd.concat(frames, axis=1).sort_index()
    combined.index.name = "date"
    csv = combined.to_csv()
    st.download_button(
        label="Download data (CSV)",
        data=csv,
        file_name=filename,
        mime="text/csv",
    )


def kpi_card(series: Series, df: pd.DataFrame) -> str:
    info = latest_change(df)
    if pd.isna(info["value"]):
        return f"<div class='kpi'><div class='name'>{series.label}</div>" \
               f"<div class='val'>—</div></div>"

    val = f"{info['value']:,.{series.decimals}f}"
    delta_html = ""
    if not pd.isna(info["delta"]):
        # For stocks, a draw (negative) is the bullish/notable move — flip the
        # color so "good for price" reads green regardless of sign.
        raw = info["delta"]
        positive = raw > 0
        if series.invert_delta:
            positive = not positive
        cls = "up" if positive else "down"
        arrow = "▲" if raw > 0 else "▼"
        delta_html = (f"<div class='delta {cls}'>{arrow} "
                      f"{abs(raw):,.{series.decimals}f} "
                      f"({info['pct']:+.1f}% w/w)</div>")
    date_str = info["date"].strftime("%b %d, %Y") if info["date"] is not None else ""
    return (f"<div class='kpi'><div class='name'>{series.label}</div>"
            f"<div class='val'>{val}</div>"
            f"<div class='unit'>{series.units} · {date_str}</div>{delta_html}</div>")


def render():
    inject_brand()
    st.title("U.S. Energy Markets Dashboard")
    st.caption("Weekly fundamentals and spot prices, sourced live from the U.S. "
               "Energy Information Administration (EIA) Open Data API.")

    # Controls
    with st.sidebar:
        st.header("Controls")
        years_back = st.slider("History (years)", 2, 12, 6)
        st.button("Refresh data", on_click=st.cache_data.clear)

    start = (pd.Timestamp.today() - pd.DateOffset(years=years_back)).strftime("%Y-%m-%d")

    try:
        data = {k: load_series(s.eia_id, start) for k, s in SERIES_BY_KEY.items()}
    except EIAError as err:
        st.error(str(err))
        st.info("Set your key:  export EIA_API_KEY='your-key-here'  (or add it "
                "to a .env file), then rerun.")
        st.stop()

    # ---- KPI strip ----
    kpi_row1 = ["wti", "henry_hub", "crude_stocks"]
    kpi_row2 = ["ng_storage", "refinery_util", "product_supplied"]
    for row in [kpi_row1, kpi_row2]:
        cols = st.columns(3)
        for col, key in zip(cols, row):
            s = SERIES_BY_KEY[key]
            col.markdown(kpi_card(s, data[key]), unsafe_allow_html=True)

    # Days of Supply — API's headline metric
    
    tab_crude, tab_gas, tab_prod, tab_price = st.tabs(
        ["Crude Oil", "Natural Gas", "Products & Demand", "Prices"])

    lookback_days = years_back * 365

    with tab_crude:
        c1, c2 = st.columns(2)
        c1.plotly_chart(seasonal_chart(data["crude_stocks"],
                        SERIES_BY_KEY["crude_stocks"], years=years_back,
                        exclude_years=[2020]),
                        use_container_width=True)
        c2.plotly_chart(line_chart(data["crude_prod"],
                        SERIES_BY_KEY["crude_prod"], lookback_days=lookback_days),
                        use_container_width=True)
        st.plotly_chart(line_chart(data["refinery_util"],
                        SERIES_BY_KEY["refinery_util"], lookback_days=lookback_days),
                        use_container_width=True)
        download_button(["crude_stocks", "crude_prod", "refinery_util"],
                        data, "crude_oil_data.csv")

    with tab_gas:
        st.plotly_chart(seasonal_chart(data["ng_storage"],
                        SERIES_BY_KEY["ng_storage"], years=years_back,
                        exclude_years=[2020]),
                        use_container_width=True)
        st.caption(f"The shaded band is the {years_back}-year weekly min–max range; the dotted "
                   f"line is the {years_back}-year average. Position vs. the band is the first "
                   "thing a gas analyst checks each Thursday.")
        download_button(["ng_storage"], data, "natural_gas_storage.csv")

    with tab_prod:
        c1, c2 = st.columns(2)
        c1.plotly_chart(seasonal_chart(data["gasoline_stocks"],
                        SERIES_BY_KEY["gasoline_stocks"], years=years_back,
                        exclude_years=[2020]),
                        use_container_width=True)
        c2.plotly_chart(seasonal_chart(data["distillate_stocks"],
                        SERIES_BY_KEY["distillate_stocks"], years=years_back,
                        exclude_years=[2020]),
                        use_container_width=True)
        st.plotly_chart(line_chart_with_ma(data["product_supplied"],
                        SERIES_BY_KEY["product_supplied"],
                        lookback_days=lookback_days, ma_window=4),
                        use_container_width=True)
        st.caption("Dotted line = raw weekly EIA report. Solid line = 4-week rolling "
                   "average, smoothing shipping and reporting noise to show the "
                   "underlying demand trend.")
        download_button(["gasoline_stocks", "distillate_stocks", "product_supplied"],
                        data, "products_demand_data.csv")

    with tab_price:
        c1, c2 = st.columns(2)
        c1.plotly_chart(line_chart(data["wti"], SERIES_BY_KEY["wti"],
                        lookback_days=lookback_days), use_container_width=True)
        c2.plotly_chart(line_chart(data["henry_hub"], SERIES_BY_KEY["henry_hub"],
                        lookback_days=lookback_days), use_container_width=True)
        download_button(["wti", "henry_hub"], data, "prices_data.csv")

        # 3-2-1 Crack Spread — refinery margin proxy
    st.divider()
    st.caption("Source: U.S. Energy Information Administration.")


if __name__ == "__main__":
    render()
