import os
import psycopg2
import pandas as pd
from psycopg2.extras import RealDictCursor, execute_values
from dotenv import load_dotenv
import streamlit as st

load_dotenv(".env.local")

def get_dict_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        cursor_factory=RealDictCursor,
    )

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

def run_query(sql: str, params=None) -> pd.DataFrame:
    """Return query results as a pandas DataFrame."""
    if params is None:
        params = ()
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return pd.DataFrame(rows)

orders_df = run_query("""
    SELECT 
    order_date AS "Date",
    order_num AS "Order Number",
    seller AS "Retailer",
    total_cost AS "Cost"
    FROM orders
    ORDER BY order_date DESC;
""")


sales_df = run_query("""
WITH item_totals AS (
    SELECT
        sale_id,
        SUM(quantity) AS num_items
    FROM sale_items
    GROUP BY sale_id
    )
    SELECT
        sale_date AS "Date",
        platform AS "Platform",
        num_items AS "Number of Items",
        sale_revenue AS "Revenue"
    FROM sales s
    LEFT JOIN item_totals it ON it.sale_id = s.sale_id;
    """)

order_items_df = run_query("""
    SELECT 
        o.order_date AS "Date",
        i.category AS "Category", 
        i.description AS "Item", 
        oi.quantity AS "Quantity", 
        cb.unit_cost_basis AS "Cost (Per Unit)"
    FROM order_items oi
    JOIN items i ON oi.item_id = i.item_id
    INNER JOIN orders o ON o.order_num = oi.order_num
    JOIN cost_basis cb ON cb.order_num = oi.order_num AND cb.item_id = oi.item_id
    ORDER BY o.order_date DESC;
""")

inventory_df = run_query("""
    WITH purchased AS (
        SELECT item_id, SUM(quantity) AS total_purchased
        FROM order_items
        GROUP BY item_id
        ),
    sold AS (
        SELECT item_id, SUM(quantity) AS total_sold
        FROM sale_items
        GROUP BY item_id
        ),
    returns AS (
        SELECT item_id, SUM(quantity) AS total_returned
        FROM return_items
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

monthly_profit_df = run_query("""
WITH month_series AS (
    SELECT generate_series(
        date_trunc('month', CURRENT_DATE) - interval '5 months',
        date_trunc('month', CURRENT_DATE),
        interval '1 month'
    )::date AS month
),
sale_profit AS (
    SELECT
        date_trunc('month', s.sale_date)::date AS month,
        s.sale_id,
        s.sale_revenue
          - COALESCE(SUM(si.quantity * si.unit_cost_basis_at_sale), 0) AS profit
    FROM sales s
    LEFT JOIN sale_items si ON si.sale_id = s.sale_id
    GROUP BY date_trunc('month', s.sale_date)::date, s.sale_id, s.sale_revenue
),
monthly_profit AS (
    SELECT
        month,
        SUM(profit) AS revenue
    FROM sale_profit
    GROUP BY month
)
SELECT
    m.month,
    COALESCE(mp.revenue, 0) AS profit
FROM month_series m
LEFT JOIN monthly_profit mp ON mp.month = m.month
ORDER BY m.month;
""")

total_profit_df = run_query("""
WITH sale_profit AS (
    SELECT
        s.sale_id,
        s.sale_revenue - COALESCE(SUM(si.quantity * si.unit_cost_basis_at_sale), 0) AS profit
    FROM sales s
    LEFT JOIN sale_items si ON si.sale_id = s.sale_id
    GROUP BY s.sale_id, s.sale_revenue
)
SELECT SUM(profit) AS total_profit FROM sale_profit;
""")

current_month_kpi_df = run_query("""
WITH this_month AS (
    SELECT
        s.sale_id,
        s.sale_date,
        s.sale_revenue,
        COALESCE(SUM(si.quantity), 0) AS quantity,
        s.sale_revenue - COALESCE(SUM(si.quantity * si.unit_cost_basis_at_sale), 0) AS item_profit
    FROM sales s
    LEFT JOIN sale_items si ON si.sale_id = s.sale_id
    WHERE s.sale_date >= date_trunc('month', CURRENT_DATE)
      AND s.sale_date < date_trunc('month', CURRENT_DATE) + interval '1 month'
    GROUP BY
    s.sale_id,
    s.sale_date,
    s.sale_revenue
)
SELECT
    COALESCE(SUM(quantity), 0) AS items_sold,
    COALESCE(SUM(sale_revenue), 0) AS gross_revenue,
    COALESCE(SUM(item_profit), 0) AS item_profit
FROM this_month;
""")

def run_query_df(sql: str, params=None) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query(sql, conn, params=params)

def insert_order_with_items(order_data: dict, items_rows: list[dict]):
    """
    order_data: dict for orders table
    items_rows: list of dicts for order_items table rows
    """
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
                # insert into orders
                cur.execute(
                    """
                    INSERT INTO orders (order_num, order_date, seller, total_cost, shipping_cost, tax_rate)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        order_data["order_num"],
                        order_data["order_date"],
                        order_data["seller"],
                        order_data["total_cost"],
                        order_data["shipping_cost"],
                        order_data["tax_rate"]
                    ),
                )
                # insert into order_items
                values = [
                    (
                        order_data["order_num"],
                        r["item_id"],
                        r["quantity"],
                        r["purchase_price_per_item"],
                        r["pas_fee_per_item"]
                    )
                    for r in items_rows
                ]

                execute_values(
                    cur,
                    """
                    INSERT INTO order_items (order_num, item_id, quantity, purchase_price_per_item, pas_fee_per_item)
                    VALUES %s
                    """,
                    values,
                )

                # commits automatically when exiting "with get_conn() as conn:" if no exception