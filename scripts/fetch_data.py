# script to fetch all the EIA data
from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow imports from the project root
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from dotenv import load_dotenv

from config import SERIES_BY_KEY
from eia_client import EIAClient, EIAError

load_dotenv()

DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Fetch 12 years so the dashboard never needs to hit the API
START = (pd.Timestamp.today() - pd.DateOffset(years=12)).strftime("%Y-%m-%d")


def main() -> None:
    api_key = os.getenv("EIA_API_KEY", "")
    if not api_key:
        print("ERROR: EIA_API_KEY not set.")
        sys.exit(1)

    client = EIAClient(api_key=api_key)
    errors = []

    for key, series in SERIES_BY_KEY.items():
        path = DATA_DIR / f"{key}.csv"
        try:
            df = client.fetch(series.eia_id, start=START)
            df.to_csv(path)
            print(f"  OK  {key} → {len(df)} rows → {path.name}")
        except EIAError as e:
            errors.append(key)
            print(f"  FAIL {key}: {e}")

    if errors:
        print(f"\nFailed series: {errors}")
        sys.exit(1)
    else:
        print(f"\nAll {len(SERIES_BY_KEY)} series written to {DATA_DIR}/")


if __name__ == "__main__":
    main()
