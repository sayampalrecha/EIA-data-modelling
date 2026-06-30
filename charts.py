
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from analytics import seasonal_range, trajectory_projection, with_week_of_year
from config import Brand, Series


def _apply_brand(fig: go.Figure, title: str, units: str) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=17, color=Brand.TEXT,
                                         family=Brand.FONT_DISPLAY)),
        paper_bgcolor=Brand.INK,
        plot_bgcolor=Brand.INK,
        font=dict(family=Brand.FONT_BODY, color=Brand.TEXT, size=12),
        margin=dict(l=56, r=24, t=52, b=40),
        hovermode="x unified",
        showlegend=True,
        legend=dict(orientation="v", yanchor="top", y=0.99, x=0.99,
                    xanchor="right", bgcolor="rgba(247,249,252,0.92)",
                    bordercolor=Brand.GRID, borderwidth=1, font=dict(size=11,
                    color=Brand.TEXT)),
        yaxis=dict(title=dict(text=units, font=dict(color=Brand.TEXT)),
                   gridcolor=Brand.GRID, zeroline=False,
                   tickfont=dict(family=Brand.FONT_MONO, color=Brand.TEXT)),
        xaxis=dict(gridcolor=Brand.GRID, zeroline=False,
                   tickfont=dict(color=Brand.TEXT)),
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


def seasonal_chart(
    df: pd.DataFrame,
    series: Series,
    years: int = 5,
    exclude_years: list[int] | None = None,
) -> go.Figure:
    """
    Signature visual: shade the 5-year min/max envelope, draw the 5-year average,
    then overlay the current year so deviations from normal pop immediately.
    """
    fig = go.Figure()
    band = seasonal_range(df, years=years, exclude_years=exclude_years)

    # Current calendar year overlay — computed first so we can cap the band
    # at the latest week that actually has data, avoiding spurious edge spikes.
    latest_woy = 53
    if not df.empty:
        this_year = df.index.max().year
        cur = with_week_of_year(df[df.index.year == this_year])
        if not cur.empty:
            latest_woy = int(cur["woy"].max())
            fig.add_trace(go.Scatter(
                x=cur["woy"], y=cur["value"], mode="lines", name=str(this_year),
                line=dict(color=series.color, width=2.6),
                hovertemplate="wk %{x}<br>%{y:,.0f}<extra></extra>",
            ))

            proj = trajectory_projection(cur)
            if not proj.empty:
                # Connect projection to last observed point so the line is continuous
                last_point = cur[["woy", "value"]].dropna().iloc[[-1]]
                proj_plot = pd.concat([last_point, proj], ignore_index=True)
                fig.add_trace(go.Scatter(
                    x=proj_plot["woy"], y=proj_plot["value"], mode="lines",
                    name="at-current-pace est.",
                    line=dict(color=series.color, width=1.6, dash="dash"),
                    hovertemplate="wk %{x}<br>proj %{y:,.0f}<extra></extra>",
                ))

    if not band.empty:
        # Cap band to weeks already observed this year — no point benchmarking
        # future weeks against a noisy average the reader can't act on yet.
        b = band[band["woy"] <= latest_woy]
        fig.add_trace(go.Scatter(
            x=b["woy"], y=b["max"], mode="lines", name=f"{years}-yr max",
            line=dict(width=0), hoverinfo="skip", showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=b["woy"], y=b["min"], mode="lines", name=f"{years}-yr range",
            line=dict(width=0), fill="tonexty", fillcolor=Brand.BAND,
            hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=b["woy"], y=b["avg"], mode="lines", name=f"{years}-yr avg",
            line=dict(color=Brand.MUTED, width=1.4, dash="dot"),
            hovertemplate="wk %{x}<br>avg %{y:,.0f}<extra></extra>",
        ))

    fig = _apply_brand(fig, f"{series.label} vs {years}-yr range", series.units)
    fig.update_xaxes(title="week of year", range=[1, 53])
    return fig
