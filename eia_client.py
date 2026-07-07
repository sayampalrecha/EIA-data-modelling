
from __future__ import annotations

import time
from typing import Optional

import pandas as pd
import requests

BASE_URL = "https://api.eia.gov/v2/seriesid/"


class EIAError(RuntimeError):
    """Raised for any non-recoverable problem talking to the EIA API."""


class EIAClient:
    def __init__(self, api_key: str, timeout: int = 30, max_retries: int = 3):
        if not api_key:
            raise EIAError(
                "No EIA API key provided. Register for a free key at "
                "https://www.eia.gov/opendata/register.php and set EIA_API_KEY."
            )
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = requests.Session()

    def fetch(
        self,
        eia_id: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch a single series. `start`/`end` are 'YYYY-MM-DD' (optional)."""
        params = {
            "api_key": self.api_key,
            "data[0]": "value",
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "length": 5000,
        }
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        payload = self._get_with_retries(BASE_URL + eia_id, params)
        return self._to_frame(payload, eia_id)

    # ----------------------------------------------------------------- internal
    def _get_with_retries(self, url: str, params: dict) -> dict:
        last_err: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self._session.get(url, params=params, timeout=self.timeout)
                if resp.status_code == 403:
                    raise EIAError(
                        "EIA rejected the request (403). Your API key is likely "
                        "invalid or missing."
                    )
                if resp.status_code == 404:
                    raise EIAError(
                        f"Series not found (404). Check the EIA ID in config.py: "
                        f"{params.get('series', url)}"
                    )
                resp.raise_for_status()
                return resp.json()
            except EIAError:
                raise  # don't retry auth / not-found errors
            except (requests.RequestException, ValueError) as err:
                last_err = err
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)  # 2s, 4s, ...
        raise EIAError(f"EIA request failed after {self.max_retries} tries: {last_err}")

    @staticmethod
    def _to_frame(payload: dict, eia_id: str) -> pd.DataFrame:
        try:
            rows = payload["response"]["data"]
        except (KeyError, TypeError):
            raise EIAError(f"Unexpected response shape for {eia_id}: {payload}")

        if not rows:
            return pd.DataFrame(columns=["value"]).rename_axis("date")

        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["period"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = (
            df[["date", "value"]]
            .dropna(subset=["value"])
            .sort_values("date")
            .set_index("date")
        )
        return df
