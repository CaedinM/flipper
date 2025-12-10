import os
import psycopg2
import pandas as pd
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv(".env.local")

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        cursor_factory=RealDictCursor,
    )

def run_query(sql: str, params=None) -> pd.DataFrame:
    """Return query results as a pandas DataFrame."""
    if params is None:
        params = ()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return pd.DataFrame(rows)

orders_df = run_query("""
    SELECT 
    order_date AS "Date",
    order_num AS "Order Number",
    seller AS "Retailer",
    order_cost AS "Value"
    FROM orders
    ORDER BY order_date DESC;
""")

sales_df = run_query("""
    SELECT
    sale_date AS "Date",
    items.description AS "Item",
    quantity AS "Quantity",
    payout_amount AS "Value",
    platform AS "Platform"
    FROM sales
    JOIN items ON items.item_id = sales.item_id
    ORDER BY sale_date DESC;
""")

order_items_df = run_query("""
    SELECT 
    o.order_date AS "Date",
    i.description AS "Item", 
    oi.quantity AS "Quantity", 
    (i.retail_value * 1.0975) + oi.pas_fee_per_item AS "Price",
    i.category AS "Category", 
    i.retail_value AS "Retail Value"
    FROM order_items oi
    JOIN items i ON oi.item_id = i.item_id
    INNER JOIN orders o ON o.order_num = oi.order_num
    ORDER BY order_date DESC;
""")

inventory_df = run_query("""
    WITH purchased AS (
    SELECT item_id, SUM(quantity) AS total_purchased
    FROM order_items
    GROUP BY item_id
    ),
    sold AS (
    SELECT item_id, SUM(quantity) AS total_sold
    FROM sales
    GROUP BY item_id
    ),
    returns AS (
    SELECT item_id, SUM(quantity) AS total_returned
    FROM returns
    GROUP BY item_id
    )
    SELECT
    i.description AS "Item",
    i.category AS "Category",
    i.retail_value AS "Retail Value",
    COALESCE(p.total_purchased, 0) - COALESCE(s.total_sold, 0) - COALESCE(r.total_returned, 0) AS "Stock"
    FROM items i
    LEFT JOIN purchased p ON p.item_id = i.item_id
    LEFT JOIN sold s ON s.item_id = i.item_id
    LEFT JOIN returns r ON r.item_id = i.item_id
    WHERE (COALESCE(p.total_purchased, 0) - COALESCE(s.total_sold, 0) - COALESCE(r.total_returned, 0)) > 0;
""")

monthly_revenue_df = run_query("""
WITH month_series AS (
    SELECT generate_series(
        date_trunc('month', CURRENT_DATE) - interval '5 months',  -- start 6 months ago
        date_trunc('month', CURRENT_DATE),                        -- end this month
        interval '1 month'
    )::date AS month
),
monthly_revenue AS (
    SELECT
        DATE_TRUNC('month', s.sale_date)::date AS month,
        SUM(s.payout_amount - ((i.retail_value * 1.0975) + COALESCE(oi.pas_fee_per_item, 0))) AS revenue
    FROM sales s
    JOIN items i ON i.item_id = s.item_id
    LEFT JOIN order_items oi ON oi.item_id = s.item_id
    GROUP BY 1
)
SELECT
    m.month,
    COALESCE(r.revenue, 0) AS revenue
FROM month_series m
LEFT JOIN monthly_revenue r ON r.month = m.month
ORDER BY m.month;
""")

total_revenue_df = run_query("""
SELECT
    SUM(s.payout_amount - ((i.retail_value * 1.0975) + COALESCE(oi.pas_fee_per_item, 0))) AS total_revenue
FROM sales s
JOIN items i ON i.item_id = s.item_id
LEFT JOIN order_items oi ON oi.item_id = s.item_id;
""")

current_month_kpi_df = run_query("""
WITH this_month AS (
    SELECT
        s.sale_id,
        s.sale_date,
        s.payout_amount,
        i.retail_value,
        COALESCE(oi.pas_fee_per_item, 0) AS pas_fee,
        (i.retail_value * 1.0975 + COALESCE(oi.pas_fee_per_item, 0)) AS total_cost,
        (s.payout_amount - (i.retail_value * 1.0975 + COALESCE(oi.pas_fee_per_item, 0))) AS gross_item_revenue
    FROM sales s
    JOIN items i ON i.item_id = s.item_id
    LEFT JOIN order_items oi ON oi.item_id = s.item_id
    WHERE s.sale_date >= date_trunc('month', CURRENT_DATE)
      AND s.sale_date < date_trunc('month', CURRENT_DATE) + interval '1 month'
)
SELECT
    COUNT(*) AS number_of_sales,
    COALESCE(SUM(payout_amount), 0) AS gross_revenue,
    COALESCE(SUM(gross_item_revenue), 0) AS item_profit
FROM this_month;
""")