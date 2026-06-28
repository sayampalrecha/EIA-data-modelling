
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


def seasonal_range(df: pd.DataFrame, years: int = 5) -> pd.DataFrame:
    """
    Build a week-of-year min/max/avg envelope from the last `years` complete
    years, indexed 1..53. This is the classic "is storage above or below the
    5-year range?" visual that EIA, IEA, and every gas desk uses.
    """
    if df.empty:
        return pd.DataFrame(columns=["woy", "min", "max", "avg"])

    s = df["value"].dropna().copy()
    cutoff = s.index.max() - pd.DateOffset(years=years)
    hist = s[(s.index >= cutoff) & (s.index < s.index.max().normalize())]
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


def with_week_of_year(df: pd.DataFrame) -> pd.DataFrame:
    """Attach an ISO week-of-year column for overlaying the current year."""
    if df.empty:
        return df.assign(woy=pd.Series(dtype=int))
    out = df.copy()
    out["woy"] = out.index.isocalendar().week.astype(int)
    return out
