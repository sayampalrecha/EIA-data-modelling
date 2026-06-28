"""Smoke test: imports, analytics math, and chart generation with fake data."""
import numpy as np
import pandas as pd

# 1. Modules import cleanly?
from config import SERIES, SERIES_BY_KEY, Brand
from analytics import latest_change, seasonal_range, with_week_of_year
from charts import line_chart, seasonal_chart
print(f"OK imports — {len(SERIES)} series configured")

# 2. Build ~6 years of synthetic weekly storage data with seasonality.
dates = pd.date_range("2019-01-01", "2025-06-20", freq="W")
seasonal = 1500 + 900 * np.sin(2 * np.pi * dates.isocalendar().week.values / 52)
noise = np.random.RandomState(0).normal(0, 60, len(dates))
df = pd.DataFrame({"value": seasonal + noise}, index=dates)
df.index.name = "date"

# 3. Analytics
chg = latest_change(df)
print(f"OK latest_change — value={chg['value']:.0f} delta={chg['delta']:+.0f} "
      f"pct={chg['pct']:+.2f}%")

band = seasonal_range(df, years=5)
assert {"woy", "min", "max", "avg"}.issubset(band.columns)
assert (band["max"] >= band["min"]).all(), "max must be >= min everywhere"
print(f"OK seasonal_range — {len(band)} weeks, "
      f"min={band['min'].min():.0f} max={band['max'].max():.0f}")

# 4. Charts return real figures with traces
s = SERIES_BY_KEY["ng_storage"]
fig1 = seasonal_chart(df, s, years=5)
fig2 = line_chart(df, SERIES_BY_KEY["wti"])
assert len(fig1.data) >= 3, "seasonal chart should have band+avg+current"
assert len(fig2.data) >= 1
print(f"OK seasonal_chart — {len(fig1.data)} traces; line_chart — {len(fig2.data)} traces")

# 5. Edge case: empty frame shouldn't crash
empty = pd.DataFrame(columns=["value"]).rename_axis("date")
_ = latest_change(empty); _ = seasonal_range(empty); _ = seasonal_chart(empty, s)
print("OK empty-frame handling")

print("\nALL CHECKS PASSED")
