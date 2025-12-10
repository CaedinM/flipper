import altair as alt
import pandas as pd

from db import orders_df, order_items_df, inventory_df, sales_df, monthly_revenue_df

monthly_revenue_df = pd.DataFrame(monthly_revenue_df)

# Ensure month is a datetime
monthly_revenue_df["month"] = pd.to_datetime(monthly_revenue_df["month"], utc=True)

# Ensure revenue is numeric
monthly_revenue_df["revenue"] = pd.to_numeric(monthly_revenue_df["revenue"], errors="coerce")

monthly_revenue_df["month_label"] = (monthly_revenue_df["month"].dt.to_period("M").dt.strftime("%b %Y"))

monthly_revenue_chart = (
    alt.Chart(monthly_revenue_df)
    .mark_bar()
    .encode(
        x=alt.X(
            "month_label:N",
            title="Month",
            sort=list(monthly_revenue_df["month_label"]),
            axis=alt.Axis(labelAngle=0)
            ),
        y=alt.Y(
            "revenue:Q",
            title="Revenue ($)",
            axis=alt.Axis(format="$.0f")
            ),
        tooltip=[
            alt.Tooltip("month_label:N", title="Month"),
            alt.Tooltip("revenue:Q", title="Revenue", format="$.2f"),
        ],
        color=alt.condition(
            "datum.revenue >= 0",
            alt.value("#042600"), # positive
            alt.value("#4F0101")  # negative
        )
    )
    .properties(
        width="container",
        height=350,
        title="Revenue Trends",
    )
)
