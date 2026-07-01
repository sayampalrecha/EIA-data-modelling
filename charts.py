
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from analytics import rolling_mean, seasonal_range, trajectory_projection, with_week_of_year
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


def line_chart_with_ma(
    df: pd.DataFrame,
    series: Series,
    lookback_days: int = 365,
    ma_window: int = 4,
) -> go.Figure:
    """
    Line chart with an optional rolling moving average overlay.
    Used for Total Products Supplied to smooth weekly shipping/reporting noise.
    Raw weekly series is shown faint; the MA line is the analytical signal.
    """
    fig = go.Figure()
    if not df.empty:
        cutoff = df.index.max() - pd.Timedelta(days=lookback_days)
        view = rolling_mean(df[df.index >= cutoff], window=ma_window)

        # Raw series — lighter, thinner so MA reads as the primary line
        fig.add_trace(go.Scatter(
            x=view.index, y=view["value"], mode="lines",
            name=f"{series.label} (weekly)",
            line=dict(color=series.color, width=1.2,
                      dash="dot"),
            opacity=0.45,
            hovertemplate="%{x|%b %d, %Y}<br>raw %{y:,.0f}<extra></extra>",
        ))
        # Rolling MA — bold primary line
        fig.add_trace(go.Scatter(
            x=view.index, y=view["rolling"], mode="lines",
            name=f"{ma_window}-wk avg",
            line=dict(color=series.color, width=2.4),
            hovertemplate="%{x|%b %d, %Y}<br>{ma_window}-wk avg %{{y:,.0f}}<extra></extra>".replace("{ma_window}", str(ma_window)),
        ))
    return _apply_brand(fig, f"{series.label} + {ma_window}-wk Rolling Avg", series.units)


def seasonal_chart(
    df: pd.DataFrame,
    series: Series,
    years: int = 5,
    exclude_years: list[int] | None = None,
) -> go.Figure:
    """
    Signature visual: shade the N-year min/max envelope across all 52 weeks,
    draw the N-year average, then overlay the current year and an at-current-pace
    projection. The historical band always spans weeks 1–52 so the seasonal
    pattern is fully visible regardless of where the current year is.
    """
    fig = go.Figure()
    band = seasonal_range(df, years=years, exclude_years=exclude_years)

    # ── Historical band — always full 52 weeks ──────────────────────────────
    if not band.empty:
        fig.add_trace(go.Scatter(
            x=band["woy"], y=band["max"], mode="lines",
            name=f"{years}-yr max",
            line=dict(width=0), hoverinfo="skip", showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=band["woy"], y=band["min"], mode="lines",
            name=f"{years}-yr range",
            line=dict(width=0), fill="tonexty", fillcolor=Brand.BAND,
            hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=band["woy"], y=band["avg"], mode="lines",
            name=f"{years}-yr avg",
            line=dict(color=Brand.MUTED, width=1.4, dash="dot"),
            hovertemplate="wk %{x}<br>avg %{y:,.0f}<extra></extra>",
        ))

    # ── Current year + projection ───────────────────────────────────────────
    if not df.empty:
        this_year = df.index.max().year
        cur = with_week_of_year(df[df.index.year == this_year])
        if not cur.empty:
            fig.add_trace(go.Scatter(
                x=cur["woy"], y=cur["value"], mode="lines", name=str(this_year),
                line=dict(color=series.color, width=2.6),
                hovertemplate="wk %{x}<br>%{y:,.0f}<extra></extra>",
            ))

            proj = trajectory_projection(cur)
            if not proj.empty:
                last_point = cur[["woy", "value"]].dropna().iloc[[-1]]
                proj_plot = pd.concat([last_point, proj], ignore_index=True)
                fig.add_trace(go.Scatter(
                    x=proj_plot["woy"], y=proj_plot["value"], mode="lines",
                    name="at-current-pace est.",
                    line=dict(color=series.color, width=1.6, dash="dash"),
                    hovertemplate="wk %{x}<br>proj %{y:,.0f}<extra></extra>",
                ))

    fig = _apply_brand(fig, f"{series.label} vs {years}-yr range", series.units)
    # Fixed x-axis 1–52 so the full seasonal pattern is always visible
    fig.update_xaxes(title="week of year", range=[1, 52])
    return fig


def crack_spread_chart(
    crack_df: pd.DataFrame,
    years: int = 5,
    exclude_years: list[int] | None = None,
) -> go.Figure:
    """
    3-2-1 crack spread seasonal band chart.
    Plots the current year's weekly crack spread against its own N-year
    min/max/avg envelope — the same seasonal analysis applied to inventory
    but for refinery margins.
    """
    from config import Series as S
    # Build a synthetic Series object just for styling
    crack_series = S(
        key="crack_321", eia_id="", label="3-2-1 Crack Spread",
        units="$/bbl", color=Brand.CRACK, group="price", decimals=2,
    )
    return seasonal_chart(crack_df, crack_series, years=years,
                          exclude_years=exclude_years)
