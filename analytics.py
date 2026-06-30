
from __future__ import annotations

import numpy as np
import pandas as pd


def latest_change(df: pd.DataFrame) -> dict:
    """Latest value plus change vs the previous observation."""
    if df.empty:
        return {"value": np.nan, "delta": np.nan, "pct": np.nan, "date": None}
    s = df["value"].dropna()
    if len(s) < 2:
        v = s.iloc[-1] if len(s) else np.nan
        return {"value": v, "delta": np.nan, "pct": np.nan,
                "date": s.index[-1] if len(s) else None}
    latest, prev = s.iloc[-1], s.iloc[-2]
    return {
        "value": latest,
        "delta": latest - prev,
        "pct": (latest - prev) / prev * 100 if prev else np.nan,
        "date": s.index[-1],
    }


def seasonal_range(
    df: pd.DataFrame,
    years: int = 5,
    exclude_years: list[int] | None = None,
) -> pd.DataFrame:
    """
    Build a week-of-year min/max/avg envelope from the last `years` complete
    years, indexed 1..53. This is the classic "is storage above or below the
    5-year range?" visual that EIA, IEA, and every gas desk uses.

    exclude_years: calendar years to drop before computing the envelope.
    Industry convention is to exclude 2020 (COVID demand collapse) so one
    anomalous year doesn't distort the "normal" band.
    """
    if df.empty:
        return pd.DataFrame(columns=["woy", "min", "max", "avg"])

    s = df["value"].dropna().copy()
    cutoff = s.index.max() - pd.DateOffset(years=years)
    hist = s[(s.index >= cutoff) & (s.index < s.index.max().normalize())]
    if exclude_years:
        hist = hist[~hist.index.year.isin(exclude_years)]
    if hist.empty:
        return pd.DataFrame(columns=["woy", "min", "max", "avg"])

    woy = hist.index.isocalendar().week.astype(int)
    grouped = hist.groupby(woy)
    out = pd.DataFrame({
        "min": grouped.min(),
        "max": grouped.max(),
        "avg": grouped.mean(),
    })
    out.index.name = "woy"
    return out.reset_index()


def trajectory_projection(
    cur: pd.DataFrame,
    weeks_ahead: int = 12,
    fit_weeks: int = 6,
) -> pd.DataFrame:
    """
    Fit a linear trend to the last `fit_weeks` of the current year and project
    it forward `weeks_ahead` weeks. Returns a DataFrame with columns [woy, value]
    starting from the week after the last observed point.

    This is the "at current draw/build rate, where do we end up?" question that
    analysts ask heading into summer driving season or winter withdrawal season.
    Linear extrapolation is intentionally simple — it reflects recent momentum,
    not a structural forecast.
    """
    if cur.empty or "woy" not in cur.columns:
        return pd.DataFrame(columns=["woy", "value"])

    recent = cur.dropna(subset=["value"]).tail(fit_weeks)
    if len(recent) < 2:
        return pd.DataFrame(columns=["woy", "value"])

    x = recent["woy"].values
    y = recent["value"].values
    slope, intercept = np.polyfit(x, y, 1)

    last_woy = int(cur["woy"].max())
    future_woys = list(range(last_woy + 1, min(last_woy + weeks_ahead + 1, 54)))
    if not future_woys:
        return pd.DataFrame(columns=["woy", "value"])

    projected = [slope * w + intercept for w in future_woys]
    return pd.DataFrame({"woy": future_woys, "value": projected})


def days_of_supply(stocks_df: pd.DataFrame, demand_df: pd.DataFrame) -> dict:
    """
    Days of Supply = latest crude stocks (thsd bbl) / latest demand (thsd bbl/d).
    Result is in days. This is the metric API headlines in their weekly bulletin
    because it normalises raw barrels for economy size and demand level.
    """
    if stocks_df.empty or demand_df.empty:
        return {"value": np.nan, "date": None}

    latest_stocks = stocks_df["value"].dropna().iloc[-1]
    latest_demand = demand_df["value"].dropna().iloc[-1]
    date = stocks_df["value"].dropna().index[-1]

    if latest_demand == 0:
        return {"value": np.nan, "date": date}

    return {"value": latest_stocks / latest_demand, "date": date}


def with_week_of_year(df: pd.DataFrame) -> pd.DataFrame:
    """Attach an ISO week-of-year column for overlaying the current year."""
    if df.empty:
        return df.assign(woy=pd.Series(dtype=int))
    out = df.copy()
    out["woy"] = out.index.isocalendar().week.astype(int)
    return out
