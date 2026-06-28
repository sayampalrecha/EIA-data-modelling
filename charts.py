
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from analytics import seasonal_range, with_week_of_year
from config import Brand, Series


def _apply_brand(fig: go.Figure, title: str, units: str) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=17, color=Brand.TEXT,
                                         family=Brand.FONT_DISPLAY)),
        paper_bgcolor=Brand.PANEL,
        plot_bgcolor=Brand.PANEL,
        font=dict(family=Brand.FONT_BODY, color=Brand.MUTED, size=12),
        margin=dict(l=56, r=24, t=52, b=40),
        hovermode="x unified",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        yaxis=dict(title=units, gridcolor=Brand.GRID, zeroline=False,
                   tickfont=dict(family=Brand.FONT_MONO)),
        xaxis=dict(gridcolor=Brand.GRID, zeroline=False),
    )
    return fig


def line_chart(df: pd.DataFrame, series: Series, lookback_days: int = 365) -> go.Figure:
    """Simple branded time series — used for prices, production, utilization."""
    fig = go.Figure()
    if not df.empty:
        cutoff = df.index.max() - pd.Timedelta(days=lookback_days)
        view = df[df.index >= cutoff]
        fig.add_trace(go.Scatter(
            x=view.index, y=view["value"], mode="lines", name=series.label,
            line=dict(color=series.color, width=2.2),
            hovertemplate="%{x|%b %d, %Y}<br>%{y:,.2f}<extra></extra>",
        ))
    return _apply_brand(fig, series.label, series.units)


def seasonal_chart(df: pd.DataFrame, series: Series, years: int = 5) -> go.Figure:
    """
    Signature visual: shade the 5-year min/max envelope, draw the 5-year average,
    then overlay the current year so deviations from normal pop immediately.
    """
    fig = go.Figure()
    band = seasonal_range(df, years=years)

    if not band.empty:
        # Range band (max then min with fill between).
        fig.add_trace(go.Scatter(
            x=band["woy"], y=band["max"], mode="lines", name=f"{years}-yr max",
            line=dict(width=0), hoverinfo="skip", showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=band["woy"], y=band["min"], mode="lines", name=f"{years}-yr range",
            line=dict(width=0), fill="tonexty", fillcolor=Brand.BAND,
            hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=band["woy"], y=band["avg"], mode="lines", name=f"{years}-yr avg",
            line=dict(color=Brand.MUTED, width=1.4, dash="dot"),
            hovertemplate="wk %{x}<br>avg %{y:,.0f}<extra></extra>",
        ))

    # Current calendar year overlay.
    if not df.empty:
        this_year = df.index.max().year
        cur = with_week_of_year(df[df.index.year == this_year])
        if not cur.empty:
            fig.add_trace(go.Scatter(
                x=cur["woy"], y=cur["value"], mode="lines", name=str(this_year),
                line=dict(color=series.color, width=2.6),
                hovertemplate="wk %{x}<br>%{y:,.0f}<extra></extra>",
            ))

    fig = _apply_brand(fig, f"{series.label} vs {years}-yr range", series.units)
    fig.update_xaxes(title="week of year", range=[1, 53])
    return fig
