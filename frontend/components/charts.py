import altair as alt
import pandas as pd
import streamlit as st
import sys
from pathlib import Path

# Add project root to path for backend imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.db import *

# --- Theme constants (match theme.py palette) ---
_BG       = "#111D16"
_AXIS     = "#2A4A35"
_LABEL    = "#5A8070"
_ACCENT   = "#C8FF00"
_NEGATIVE = "#FF5555"
_FONT_UI  = "Chakra Petch"
_FONT_DATA = "JetBrains Mono"


def _theme(chart):
    """Apply dark terminal config to any Altair chart."""
    return (
        chart
        .configure(background=_BG, padding={"top": 20, "bottom": 16, "left": 16, "right": 16})
        .configure_axis(
            labelColor=_LABEL,
            titleColor=_LABEL,
            labelFont=_FONT_DATA,
            titleFont=_FONT_UI,
            gridColor=_AXIS,
            tickColor="transparent",
            domainColor=_AXIS,
            labelFontSize=10,
            titleFontSize=10,
            titleFontWeight="normal",
            titlePadding=10,
        )
        .configure_title(
            color=_LABEL,
            font=_FONT_UI,
            fontSize=10,
            fontWeight="bold",
            anchor="start",
            offset=8,
        )
        .configure_view(stroke=_AXIS)
        .configure_legend(labelColor=_LABEL, titleColor=_LABEL)
    )


def get_monthly_profit_chart(refresh_token: int):
    monthly_profit_df = get_monthly_profit_df(st.session_state["refresh_token"])
    monthly_profit_df["month"] = pd.to_datetime(monthly_profit_df["month"], utc=True)
    monthly_profit_df["profit"] = pd.to_numeric(monthly_profit_df["profit"], errors="coerce")
    monthly_profit_df["month_label"] = (
        monthly_profit_df["month"].dt.to_period("M").dt.strftime("%b %Y")
    )

    chart = (
        alt.Chart(monthly_profit_df)
        .mark_bar(cornerRadiusTopLeft=0, cornerRadiusTopRight=0)
        .encode(
            x=alt.X(
                "month_label:N",
                title="Month",
                sort=list(monthly_profit_df["month_label"]),
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y(
                "profit:Q",
                title="Profit ($)",
                axis=alt.Axis(format="$.0f"),
            ),
            tooltip=[
                alt.Tooltip("month_label:N", title="Month"),
                alt.Tooltip("profit:Q", title="Profit", format="$.2f"),
            ],
            color=alt.condition(
                "datum.profit >= 0",
                alt.value(_ACCENT),
                alt.value(_NEGATIVE),
            ),
        )
        .properties(width="container", height=320, title="MONTHLY PROFIT")
    )
    return _theme(chart)


def get_monthly_items_sold_chart(refresh_token: int):
    df = get_monthly_items_sold_df(refresh_token)
    df["month"] = pd.to_datetime(df["month"], utc=True)
    df["items_sold"] = pd.to_numeric(df["items_sold"], errors="coerce")
    df["month_label"] = df["month"].dt.to_period("M").dt.strftime("%b %Y")

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(
                "month_label:N",
                title="Month",
                sort=list(df["month_label"]),
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y(
                "items_sold:Q",
                title="Items Sold",
                axis=alt.Axis(format="d"),
            ),
            tooltip=[
                alt.Tooltip("month_label:N", title="Month"),
                alt.Tooltip("items_sold:Q", title="Items Sold"),
            ],
            color=alt.value(_ACCENT),
        )
        .properties(width="container", height=320, title="ITEMS SOLD / MONTH")
    )
    return _theme(chart)
