# U.S. Energy Markets Dashboard

Check the Deployed app here - [Link](https://eia-data.streamlit.app/) 

A live dashboard for U.S. crude oil, natural gas, and refined product
fundamentals, pulled straight from the **EIA Open Data API** and rendered as
branded, interactive charts.

## What it shows

- **KPI** - WTI, Henry Hub, crude stocks, gas storage, refinery
  utilization, and product supplied, each with a week-over-week change. Stock
  deltas are color-coded by market impact (a draw reads green).
- **Crude tab** — stocks vs. 5-year range, field production, refinery runs.
- **Natural gas tab** — Lower-48 working gas in storage vs. the 5-year range,
  the single most-watched gas chart of the week.
- **Products & demand tab** — gasoline and distillate stocks vs. range, plus
  total product supplied as a demand proxy.
- **Prices tab** — WTI and Henry Hub spot.

## The signature visual: the 5-year range band

Storage and inventory series are seasonal, so a raw line tells you little. The
analyst's question is *"where are we versus normal for this week of year?"* The
seasonal chart shades the 5-year weekly min–max envelope, draws the 5-year
average, and overlays the current year — so deviations jump out instantly.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env          # then paste your free key into .env
streamlit run app.py
```

Get a free API key: https://www.eia.gov/opendata/register.php

## Architecture

The code is layered so each piece is independently reusable and testable:

| File            | Responsibility                                              |
|-----------------|-------------------------------------------------------------|
| `config.py`     | Series definitions + brand tokens — the single source of truth |
| `eia_client.py` | EIA API wrapper: retries, error handling, tidy DataFrames (no UI) |
| `analytics.py`  | Pure pandas: seasonal range, week-over-week change (no I/O, no UI) |
| `charts.py`     | Branded Plotly figure builders                              |
| `app.py`        | Streamlit layout, caching, KPI strip                        |
| `tests/`        | Smoke tests for the analytics + chart layers                |

Want to track another series? Add one row to `SERIES` in `config.py` and it
flows through the KPIs, tabs, and caching automatically.


