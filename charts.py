import altair as alt
import pandas as pd

from db import orders_df, order_items_df, inventory_df, sales_df, monthly_profit_df

monthly_profit_df = pd.DataFrame(monthly_profit_df)

# Ensure month is a datetime
monthly_profit_df["month"] = pd.to_datetime(monthly_profit_df["month"], utc=True)

# Ensure revenue is numeric
monthly_profit_df["profit"] = pd.to_numeric(monthly_profit_df["profit"], errors="coerce")

monthly_profit_df["month_label"] = (monthly_profit_df["month"].dt.to_period("M").dt.strftime("%b %Y"))

monthly_profit_chart = (
    alt.Chart(monthly_profit_df
)
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
            "Profit:Q",
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
