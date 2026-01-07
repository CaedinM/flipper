import altair as alt
import pandas as pd
import streamlit as st
import sys
from pathlib import Path

# Add project root to path for backend imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.db import *

def get_monthly_profit_chart(refresh_token: int):
    monthly_profit_df = get_monthly_profit_df(st.session_state["refresh_token"])
    # Ensure month is a datetime
    monthly_profit_df["month"] = pd.to_datetime(monthly_profit_df["month"], utc=True)
    # Ensure revenue is numeric
    monthly_profit_df["profit"] = pd.to_numeric(monthly_profit_df["profit"], errors="coerce")
    monthly_profit_df["month_label"] = (monthly_profit_df["month"].dt.to_period("M").dt.strftime("%b %Y"))

    chart = (
        alt.Chart(monthly_profit_df)
        .mark_bar()
        .encode(
            x=alt.X(
                "month_label:N",
                title="Month",
                sort=list(monthly_profit_df
            ["month_label"]),
                axis=alt.Axis(labelAngle=0)
                ),
            y=alt.Y(
                "profit:Q",
                title="Profit ($)",
                axis=alt.Axis(format="$.0f")
                ),
            tooltip=[
                alt.Tooltip("month_label:N", title="Month"),
                alt.Tooltip("profit:Q", title="Profit", format="$.2f"),
            ],
            color=alt.condition(
                "datum.profit >= 0",
                alt.value("#042600"), # positive
                alt.value("#4F0101")  # negative
            )
        )
        .properties(
            width="container",
            height=350,
            title=" Trends",
        )
    )
    return chart
