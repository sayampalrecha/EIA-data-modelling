"""
Central configuration: the EIA series we track and the visual brand.

Keeping series IDs and styling in one place means the data layer, chart layer,
and app never disagree about what "crude inventories" means or what color
"natural gas" should be. Add a row here and it flows through the whole app.
"""
from dataclasses import dataclass
from typing import Optional


# --------------------------------------------------------------------------
# Brand tokens — API house style: white background, navy primary, blue accents.
# Matches the American Petroleum Institute's published chart visual language.
# --------------------------------------------------------------------------
class Brand:
    INK = "#FFFFFF"          # page background
    PANEL = "#F7F9FC"        # cards / chart backgrounds
    GRID = "#DDE3EA"         # gridlines, hairline borders
    TEXT = "#0D1B2A"         # primary text — deep navy
    MUTED = "#5A6A7A"        # secondary text, captions

    CRUDE = "#1B4F8A"        # primary accent — API navy blue (crude)
    GAS = "#2E86C1"          # secondary accent — mid blue (natural gas)
    PRODUCT = "#1A6B5A"      # petroleum products — teal-green

    UP = "#1A7A3C"           # positive WoW
    DOWN = "#C0392B"         # negative WoW / draw
    BAND = "rgba(30,90,160,0.10)"  # historical range fill — light blue wash

    FONT_DISPLAY = "Space Grotesk"
    FONT_BODY = "Inter"
    FONT_MONO = "IBM Plex Mono"


@dataclass
class Series:
    """One EIA data series and how we want to present it."""
    key: str                 # internal short name
    eia_id: str              # EIA series ID (works with /v2/seriesid/)
    label: str               # human-readable title
    units: str               # axis / KPI unit label
    color: str               # line color
    group: str               # "crude" | "gas" | "product" | "price"
    seasonal: bool = False   # show 5-year range band?
    invert_delta: bool = False  # for stocks, a draw (negative) is bullish
    decimals: int = 0


# Well-known, stable EIA series IDs. The /v2/seriesid/{id} endpoint accepts
# these v1-style IDs directly, so we don't have to navigate the v2 route tree.
SERIES = [
    # --- Crude oil ---
    Series("crude_stocks", "PET.WCESTUS1.W",
           "U.S. Crude Oil Stocks (ex-SPR)", "thsd bbl",
           Brand.CRUDE, "crude", seasonal=True, invert_delta=True),
    Series("crude_prod", "PET.WCRFPUS2.W",
           "U.S. Crude Oil Field Production", "thsd bbl/d",
           Brand.CRUDE, "crude"),
    Series("refinery_util", "PET.WPULEUS3.W",
           "Refinery Utilization", "% capacity",
           Brand.CRUDE, "crude", decimals=1),
    Series("product_supplied", "PET.WRPUPUS2.W",
           "Total Products Supplied (demand proxy)", "thsd bbl/d",
           Brand.PRODUCT, "product"),
    Series("gasoline_stocks", "PET.WGTSTUS1.W",
           "Motor Gasoline Stocks", "thsd bbl",
           Brand.PRODUCT, "product", seasonal=True, invert_delta=True),
    Series("distillate_stocks", "PET.WDISTUS1.W",
           "Distillate Stocks", "thsd bbl",
           Brand.PRODUCT, "product", seasonal=True, invert_delta=True),

    # --- Natural gas ---
    Series("ng_storage", "NG.NW2_EPG0_SWO_R48_BCF.W",
           "Lower 48 Working Gas in Storage", "Bcf",
           Brand.GAS, "gas", seasonal=True),

    # --- Prices (daily) ---
    Series("wti", "PET.RWTC.D",
           "WTI Spot (Cushing)", "$/bbl",
           Brand.CRUDE, "price", decimals=2),
    Series("henry_hub", "NG.RNGWHHD.D",
           "Henry Hub Spot", "$/MMBtu",
           Brand.GAS, "price", decimals=2),
]

SERIES_BY_KEY = {s.key: s for s in SERIES}


def get_series(key: str) -> Optional[Series]:
    return SERIES_BY_KEY.get(key)
