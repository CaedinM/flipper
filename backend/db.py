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

# query with caching
def run_query(sql: str, params=None) -> pd.DataFrame:
    """Return query results as a pandas DataFrame."""
    if params is None:
        params = ()
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return pd.DataFrame(rows)

# query with no caching (Use for live updates)
@st.cache_data(show_spinner=False)
def run_query_df(sql: str, refresh_token: int=0, params=None) -> pd.DataFrame:
    with get_connection() as conn:
        if params is None:
            return pd.read_sql_query(sql, conn)
        return pd.read_sql_query(sql, conn, params=params)

def get_orders_df(refresh_token: int):
    return run_query_df("""
        SELECT 
        order_date AS "Date",
        order_num AS "Order Number",
        seller AS "Retailer",
        total_cost AS "Cost"
        FROM orders
        ORDER BY order_date DESC;
        """, refresh_token)

def get_sales_df(refresh_token: int):
    return run_query_df("""
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
        """, refresh_token)

def get_order_items_df(refresh_token: int):
    return run_query_df("""
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
        """, refresh_token)

def get_inventory_df(refresh_token: int):
    return run_query_df("""
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
        """, refresh_token)

def get_monthly_profit_df(refresh_token: int):
    return run_query_df("""
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
        """, refresh_token)

def get_sale_items_by_sale_id(sale_id: int, refresh_token: int) -> pd.DataFrame:
    """
    Get all items for a specific sale.
    Returns a DataFrame with item details and quantities.
    """
    return run_query_df("""
        SELECT 
            si.quantity,
            i.item_id,
            i.description AS item_description,
            i.category
        FROM sale_items si
        JOIN items i ON si.item_id = i.item_id
        WHERE si.sale_id = %s
        ORDER BY i.description
        """, refresh_token, params=(sale_id,))

def get_total_profit_df(refresh_token: int):
    return run_query_df("""
        WITH sale_profit AS (
            SELECT
                s.sale_id,
                s.sale_revenue - COALESCE(SUM(si.quantity * si.unit_cost_basis_at_sale), 0) AS profit
            FROM sales s
            LEFT JOIN sale_items si ON si.sale_id = s.sale_id
            GROUP BY s.sale_id, s.sale_revenue
        )
        SELECT SUM(profit) AS total_profit FROM sale_profit;
        """, refresh_token)

def get_current_month_kpi_df(refresh_token: int):
    return run_query_df("""
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
        """, refresh_token)

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

def insert_sale_with_items(sale_data: dict, items_rows: list[dict]):
    """
    sale_data: dict for sales table (sale_date, platform, sale_revenue)
    items_rows: list of dicts for sale_items table rows (item_id, quantity)
    unit_cost_basis_at_sale is automatically fetched from items.avg_unit_cost_basis
    """
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            # insert into sales and get the sale_id
            cur.execute(
                """
                INSERT INTO sales (sale_date, platform, sale_revenue)
                VALUES (%s, %s, %s)
                RETURNING sale_id
                """,
                (
                    sale_data["sale_date"],
                    sale_data["platform"],
                    sale_data["sale_revenue"]
                ),
            )
            sale_id = cur.fetchone()["sale_id"]
            
            # Get avg_unit_cost_basis for each item from the items table
            item_ids = [r["item_id"] for r in items_rows]
            if item_ids:
                # Use tuple for IN clause
                placeholders = ','.join(['%s'] * len(item_ids))
                cur.execute(
                    f"""
                    SELECT item_id, COALESCE(avg_unit_cost_basis, 0) AS avg_unit_cost_basis
                    FROM items
                    WHERE item_id IN ({placeholders})
                    """,
                    tuple(item_ids)
                )
                cost_basis_map = {row["item_id"]: row["avg_unit_cost_basis"] for row in cur.fetchall()}
            else:
                cost_basis_map = {}
            
            # insert into sale_items with cost basis from items table
            values = [
                (
                    sale_id,
                    r["item_id"],
                    r["quantity"],
                    cost_basis_map.get(r["item_id"], 0)  # Use avg_unit_cost_basis from items table
                )
                for r in items_rows
            ]

            execute_values(
                cur,
                """
                INSERT INTO sale_items (sale_id, item_id, quantity, unit_cost_basis_at_sale)
                VALUES %s
                """,
                values,
            )

            # commits automatically when exiting "with get_conn() as conn:" if no exception

def upsert_item(description: str, category: str | None = None) -> int:
    """
    Insert a new item or get existing item_id.
    Returns the item_id.
    """
    description = (description or "").strip()
    if not description:
        raise ValueError("Item description cannot be empty.")
    
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO items (description, category)
                VALUES (%s, COALESCE(%s, ''))
                ON CONFLICT (description)
                DO UPDATE SET
                    category = CASE
                        WHEN items.category = '' AND EXCLUDED.category <> '' THEN EXCLUDED.category
                        ELSE items.category
                    END
                RETURNING item_id;
                """,
                (description, category or "")
            )
            result = cur.fetchone()
            return result["item_id"]


