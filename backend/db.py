import os
from pathlib import Path
import psycopg2
import pandas as pd
from psycopg2.extras import RealDictCursor, execute_values
from dotenv import load_dotenv
import streamlit as st

# Load .env only if it exists (Docker injects env vars directly)
env_file = Path(".env")
if env_file.exists():
    load_dotenv(str(env_file))

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

# Cached by Streamlit; pass a different refresh_token to bust the cache.
@st.cache_data(show_spinner=False)
def run_query_df(sql: str, refresh_token: int = 0, params=None) -> pd.DataFrame:
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
            i.era AS "Era",
            i.set AS "Set",
            i.product AS "Product",
            oi.quantity AS "Quantity",
            oi.cost_basis AS "Cost (Per Unit)"
        FROM order_items oi
        JOIN items i ON oi.item_id = i.item_id
        INNER JOIN orders o ON o.order_num = oi.order_num
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
            i.item_id,
            i.category AS "Category",
            i.era AS "Era",
            i.set AS "Set",
            i.product AS "Product",
            i.avg_cost_basis AS "Cost Basis",
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

def get_monthly_items_sold_df(refresh_token: int):
    return run_query_df("""
        WITH month_series AS (
            SELECT generate_series(
                date_trunc('month', CURRENT_DATE) - interval '5 months',
                date_trunc('month', CURRENT_DATE),
                interval '1 month'
            )::date AS month
        ),
        monthly_sold AS (
            SELECT
                date_trunc('month', s.sale_date)::date AS month,
                SUM(si.quantity) AS items_sold
            FROM sales s
            JOIN sale_items si ON si.sale_id = s.sale_id
            GROUP BY date_trunc('month', s.sale_date)::date
        )
        SELECT
            m.month,
            COALESCE(ms.items_sold, 0) AS items_sold
        FROM month_series m
        LEFT JOIN monthly_sold ms ON ms.month = m.month
        ORDER BY m.month;
        """, refresh_token)

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
                # WAC: pricetag + even shipping share + weighted tax remainder + pas_fee
                total_pricetag_value = sum(r["pricetag"] * r["quantity"] for r in items_rows)
                total_qty = sum(r["quantity"] for r in items_rows)
                shipping_cost = order_data["shipping_cost"]
                tax_remainder = order_data["total_cost"] - shipping_cost - total_pricetag_value
                values = []
                for r in items_rows:
                    if total_pricetag_value > 0:
                        weighted_tax = (r["pricetag"] / total_pricetag_value) * tax_remainder
                    else:
                        weighted_tax = tax_remainder / total_qty if total_qty > 0 else 0
                    cost_basis = round(
                        r["pricetag"]
                        + shipping_cost / total_qty
                        + weighted_tax
                        + r["pas_fee_per_item"],
                        2,
                    )
                    values.append((
                        order_data["order_num"],
                        r["item_id"],
                        r["quantity"],
                        r["pricetag"],
                        r["pas_fee_per_item"],
                        cost_basis,
                    ))

                execute_values(
                    cur,
                    """
                    INSERT INTO order_items (order_num, item_id, quantity, pricetag, pas_fee_per_item, cost_basis)
                    VALUES %s
                    """,
                    values,
                )


def insert_sale_with_items(sale_data: dict, items_rows: list[dict]):
    """
    sale_data: dict with sale_date, platform, sale_revenue.
    items_rows: list of dicts with item_id and quantity.
    unit_cost_basis_at_sale is snapshotted from items.avg_cost_basis at sale time.
    """
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
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

            item_ids = [r["item_id"] for r in items_rows]
            if item_ids:
                # Use tuple for IN clause
                placeholders = ','.join(['%s'] * len(item_ids))
                cur.execute(
                    f"""
                    SELECT item_id, COALESCE(avg_cost_basis, 0) AS avg_cost_basis
                    FROM items
                    WHERE item_id IN ({placeholders})
                    """,
                    tuple(item_ids)
                )
                cost_basis_map = {row["item_id"]: row["avg_cost_basis"] for row in cur.fetchall()}
            else:
                cost_basis_map = {}

            values = [
                (
                    sale_id,
                    r["item_id"],
                    r["quantity"],
                    cost_basis_map.get(r["item_id"], 0)
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

def upsert_item(category: str | None = None, era: str | None = None, set: str | None = None, product: str | None = None) -> int:
    """
    Insert a new item or return the existing item_id for the given (era, set, product).
    """
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT item_id FROM items
                WHERE era IS NOT DISTINCT FROM %s
                  AND set IS NOT DISTINCT FROM %s
                  AND product IS NOT DISTINCT FROM %s
                """,
                (era, set, product)
            )
            result = cur.fetchone()
            if result:
                return result["item_id"]
            cur.execute(
                """
                INSERT INTO items (category, era, set, product)
                VALUES (%s, %s, %s, %s)
                RETURNING item_id
                """,
                (category or "", era, set, product)
            )
            return cur.fetchone()["item_id"]

def get_order_items_by_order_num(order_num: str, refresh_token: int) -> pd.DataFrame:
    """
    Get all items for a specific order by order_num.
    Returns a DataFrame with item details, quantities, and current PAS fees.
    """
    return run_query_df(
        """
        SELECT
            oi.order_item_id,
            oi.item_id,
            i.era AS "Era",
            i.set AS "Set",
            i.product AS "Product",
            i.category AS "Category",
            oi.quantity AS "Quantity",
            oi.pricetag AS "Price Tag",
            oi.pas_fee_per_item AS "PAS Fee Per Item",
            oi.cost_basis AS "Cost Basis"
        FROM order_items oi
        JOIN items i ON oi.item_id = i.item_id
        WHERE oi.order_num = %s
        ORDER BY i.set, i.product
        """,
        refresh_token,
        (order_num,)
    )

def update_pas_fees_for_order(order_num: str, pas_fee_updates: list[dict]):
    """
    Update PAS fees for order items.
    
    Args:
        order_num: The order number
        pas_fee_updates: List of dicts with 'order_item_id' and 'pas_fee_per_item'
    """
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            for update in pas_fee_updates:
                cur.execute(
                    """
                    UPDATE order_items
                    SET pas_fee_per_item = %s
                    WHERE order_item_id = %s AND order_num = %s
                    """,
                    (
                        update["pas_fee_per_item"],
                        update["order_item_id"],
                        order_num
                    )
                )

def get_inventory_count_df(refresh_token: int):
    """Returns count of unsold items in inventory."""
    return run_query_df("""
        WITH purchased AS (
            SELECT item_id, SUM(quantity) AS total_purchased FROM order_items GROUP BY item_id
        ),
        sold AS (
            SELECT item_id, SUM(quantity) AS total_sold FROM sale_items GROUP BY item_id
        ),
        returns AS (
            SELECT item_id, SUM(quantity) AS total_returned FROM return_items GROUP BY item_id
        )
        SELECT COALESCE(SUM(
            COALESCE(p.total_purchased, 0) - COALESCE(s.total_sold, 0) - COALESCE(r.total_returned, 0)
        ), 0) AS inventory_count
        FROM items i
        LEFT JOIN purchased p ON p.item_id = i.item_id
        LEFT JOIN sold s ON s.item_id = i.item_id
        LEFT JOIN returns r ON r.item_id = i.item_id
        """, refresh_token)

def get_inventory_value_df(refresh_token: int):
    """Returns total cost value of unsold inventory."""
    return run_query_df("""
        WITH purchased AS (
            SELECT item_id, SUM(quantity) AS total_purchased FROM order_items GROUP BY item_id
        ),
        sold AS (
            SELECT item_id, SUM(quantity) AS total_sold FROM sale_items GROUP BY item_id
        ),
        returns AS (
            SELECT item_id, SUM(quantity) AS total_returned FROM return_items GROUP BY item_id
        )
        SELECT COALESCE(SUM(
            (COALESCE(p.total_purchased, 0) - COALESCE(s.total_sold, 0) - COALESCE(r.total_returned, 0))
            * i.avg_cost_basis
        ), 0) AS inventory_value
        FROM items i
        LEFT JOIN purchased p ON p.item_id = i.item_id
        LEFT JOIN sold s ON s.item_id = i.item_id
        LEFT JOIN returns r ON r.item_id = i.item_id
        WHERE (COALESCE(p.total_purchased, 0) - COALESCE(s.total_sold, 0) - COALESCE(r.total_returned, 0)) > 0
        """, refresh_token)

def get_profit_margin_by_platform_df(refresh_token: int):
    """Returns profit margin % grouped by selling platform."""
    return run_query_df("""
        WITH sale_profit AS (
            SELECT
                s.platform,
                s.sale_revenue,
                s.sale_revenue - COALESCE(SUM(si.quantity * si.unit_cost_basis_at_sale), 0) AS profit
            FROM sales s
            LEFT JOIN sale_items si ON si.sale_id = s.sale_id
            GROUP BY s.sale_id, s.platform, s.sale_revenue
        )
        SELECT
            platform,
            COUNT(*)                                                     AS num_sales,
            ROUND(SUM(profit) / NULLIF(SUM(sale_revenue), 0) * 100, 1) AS profit_margin,
            ROUND(SUM(profit), 2)                                       AS total_profit,
            ROUND(SUM(sale_revenue), 2)                                 AS total_revenue
        FROM sale_profit
        GROUP BY platform
        ORDER BY profit_margin DESC NULLS LAST;
        """, refresh_token)

def get_expense_breakdown_df(refresh_token: int):
    """Returns a breakdown of money lost to PAS fees, shipping, and other expenses."""
    return run_query_df("""
        SELECT
            (SELECT COALESCE(SUM(pas_fee_per_item * quantity), 0) FROM order_items) AS total_pas_fees,
            (SELECT COALESCE(SUM(shipping_cost), 0) FROM orders)                    AS total_shipping,
            (SELECT COALESCE(SUM(expense_cost), 0) FROM other_expenses)             AS total_other_expenses
    """, refresh_token)

def get_profit_margin_by_category_df(refresh_token: int):
    """Returns profit margin % grouped by item category, using actual sale revenue allocated by quantity."""
    return run_query_df("""
        WITH per_sale_qty AS (
            SELECT sale_id, SUM(quantity) AS total_qty
            FROM sale_items
            GROUP BY sale_id
        ),
        item_revenue AS (
            SELECT
                si.sale_id,
                COALESCE(NULLIF(i.category, ''), 'Uncategorized') AS category,
                s.sale_revenue * si.quantity / psq.total_qty AS allocated_revenue,
                si.quantity * si.unit_cost_basis_at_sale AS cost
            FROM sale_items si
            JOIN items i ON si.item_id = i.item_id
            JOIN sales s ON si.sale_id = s.sale_id
            JOIN per_sale_qty psq ON psq.sale_id = si.sale_id
        )
        SELECT
            category,
            COUNT(DISTINCT sale_id)                                                            AS num_sales,
            ROUND(SUM(allocated_revenue - cost) / NULLIF(SUM(allocated_revenue), 0) * 100, 1) AS profit_margin,
            ROUND(SUM(allocated_revenue - cost), 2)                                            AS total_profit,
            ROUND(SUM(allocated_revenue), 2)                                                   AS total_revenue
        FROM item_revenue
        GROUP BY category
        ORDER BY profit_margin DESC NULLS LAST;
        """, refresh_token)

def get_cost_basis_vs_profit_df(refresh_token: int):
    """Returns avg cost basis and avg profit per unit for every sold item, for scatter plot."""
    return run_query_df("""
        WITH per_sale_qty AS (
            SELECT sale_id, SUM(quantity) AS total_qty
            FROM sale_items
            GROUP BY sale_id
        ),
        item_sales AS (
            SELECT
                i.item_id,
                COALESCE(i.set, '') || ' – ' || COALESCE(i.product, i.category) AS item_label,
                i.era,
                i.category,
                si.unit_cost_basis_at_sale                          AS cost_basis,
                s.sale_revenue * si.quantity / psq.total_qty        AS allocated_revenue,
                si.quantity
            FROM sale_items si
            JOIN items  i   ON si.item_id  = i.item_id
            JOIN sales  s   ON si.sale_id  = s.sale_id
            JOIN per_sale_qty psq ON psq.sale_id = si.sale_id
            WHERE i.category = 'Pokemon'
        )
        SELECT
            item_label,
            era,
            ROUND(AVG(cost_basis), 2)                                            AS avg_cost_basis,
            ROUND(
                SUM(allocated_revenue - quantity * cost_basis)
                / NULLIF(SUM(quantity), 0), 2
            )                                                                    AS avg_profit_per_unit,
            SUM(quantity)::int                                                   AS units_sold
        FROM item_sales
        GROUP BY item_label, era, category
        ORDER BY avg_cost_basis;
    """, refresh_token)

def get_pokemon_profit_by_set_df(refresh_token: int):
    """Returns total profit and ROI per Pokemon set, only for sets that have been sold."""
    return run_query_df("""
        WITH per_sale_qty AS (
            SELECT sale_id, SUM(quantity) AS total_qty
            FROM sale_items
            GROUP BY sale_id
        ),
        item_revenue AS (
            SELECT
                i.set,
                s.sale_revenue * si.quantity / psq.total_qty AS allocated_revenue,
                si.quantity * si.unit_cost_basis_at_sale       AS cost
            FROM sale_items si
            JOIN items i  ON si.item_id  = i.item_id
            JOIN sales s  ON si.sale_id  = s.sale_id
            JOIN per_sale_qty psq ON psq.sale_id = si.sale_id
            WHERE i.category = 'Pokemon' AND i.set IS NOT NULL
        )
        SELECT
            set                                                                    AS "Set",
            ROUND(SUM(allocated_revenue), 2)                                       AS "Revenue",
            ROUND(SUM(cost), 2)                                                    AS "Cost Basis",
            ROUND(SUM(allocated_revenue - cost), 2)                                AS "Profit",
            ROUND(SUM(allocated_revenue - cost) / NULLIF(SUM(cost), 0) * 100, 1)  AS "ROI (%)"
        FROM item_revenue
        GROUP BY set
        ORDER BY "Profit" DESC NULLS LAST;
    """, refresh_token)

def get_avg_profit_margin_df(refresh_token: int):
    """Returns overall profit margin as a percentage: total profit / total revenue * 100."""
    return run_query_df("""
        WITH sale_data AS (
            SELECT
                s.sale_revenue,
                s.sale_revenue - COALESCE(SUM(si.quantity * si.unit_cost_basis_at_sale), 0) AS profit
            FROM sales s
            LEFT JOIN sale_items si ON si.sale_id = s.sale_id
            GROUP BY s.sale_id, s.sale_revenue
        )
        SELECT
            CASE WHEN SUM(sale_revenue) > 0
                 THEN ROUND(SUM(profit) / SUM(sale_revenue) * 100, 1)
                 ELSE 0
            END AS avg_profit_margin
        FROM sale_data;
        """, refresh_token)

def get_net_profit_df(refresh_token: int):
    """Returns total profit minus all other_expenses."""
    return run_query_df("""
        WITH sale_profit AS (
            SELECT s.sale_id, s.sale_revenue - COALESCE(SUM(si.quantity * si.unit_cost_basis_at_sale), 0) AS profit
            FROM sales s
            LEFT JOIN sale_items si ON si.sale_id = s.sale_id
            GROUP BY s.sale_id, s.sale_revenue
        ),
        total_expenses AS (
            SELECT COALESCE(SUM(expense_cost), 0) AS expenses FROM other_expenses
        )
        SELECT COALESCE((SELECT SUM(profit) FROM sale_profit), 0) - (SELECT expenses FROM total_expenses) AS net_profit
        """, refresh_token)

def get_sales_velocity_df(refresh_token: int):
    """Returns average items sold per week (last 4 weeks)."""
    return run_query_df("""
        SELECT COALESCE(ROUND(SUM(si.quantity) / 4.0, 2), 0) AS items_per_week
        FROM sales s
        LEFT JOIN sale_items si ON si.sale_id = s.sale_id
        WHERE s.sale_date >= CURRENT_DATE - INTERVAL '28 days'
        """, refresh_token)

def get_current_month_items_purchased_df(refresh_token: int):
    return run_query_df("""
        SELECT COALESCE(SUM(oi.quantity), 0) AS items_purchased
        FROM order_items oi
        JOIN orders o ON o.order_num = oi.order_num
        WHERE o.order_date >= date_trunc('month', CURRENT_DATE)
        AND o.order_date < date_trunc('month', CURRENT_DATE) + interval '1 month'
    """, refresh_token)


def insert_expense(expense_date, description: str, expense_cost: float):
    """Insert a new row into other_expenses."""
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO other_expenses (expense_date, description, expense_cost)
                VALUES (%s, %s, %s)
                """,
                (expense_date, description.strip(), expense_cost),
            )


def recalculate_all_cost_basis():
    """
    One-time migration that rewrites cost data across all three tables
    using the canonical WAC formula:

      order_items.cost_basis  = pricetag
                               + shipping_cost / total_qty_in_order
                               + (pricetag / sum_pricetags) * tax_remainder
                               + pas_fee_per_item

      items.avg_cost_basis    = WAC over all purchases (all time)

      sale_items.unit_cost_basis_at_sale
                              = WAC of purchases on or before the sale date
                                (temporal WAC — only what was known at sale time)
    """
    with get_dict_connection() as conn:
        with conn.cursor() as cur:

            # ── Step 1: recalculate order_items.cost_basis ────────────────────
            cur.execute("""
                WITH order_totals AS (
                    SELECT
                        oi.order_num,
                        SUM(oi.pricetag * oi.quantity) AS sum_pricetags,
                        SUM(oi.quantity)               AS total_qty,
                        o.total_cost,
                        o.shipping_cost
                    FROM order_items oi
                    JOIN orders o ON o.order_num = oi.order_num
                    GROUP BY oi.order_num, o.total_cost, o.shipping_cost
                ),
                new_costs AS (
                    SELECT
                        oi.order_item_id,
                        ROUND(
                            oi.pricetag
                            + ot.shipping_cost / NULLIF(ot.total_qty, 0)
                            + (oi.pricetag / NULLIF(ot.sum_pricetags, 0))
                              * (ot.total_cost - ot.shipping_cost - ot.sum_pricetags)
                            + oi.pas_fee_per_item,
                            2
                        ) AS new_cost_basis
                    FROM order_items oi
                    JOIN order_totals ot ON ot.order_num = oi.order_num
                )
                UPDATE order_items
                SET cost_basis = new_costs.new_cost_basis
                FROM new_costs
                WHERE order_items.order_item_id = new_costs.order_item_id;
            """)

            # ── Step 2: recalculate items.avg_cost_basis (WAC, all time) ─────
            # The trigger on order_items also does this, but we update explicitly
            # here to guarantee consistency after the bulk step 1 above.
            cur.execute("""
                UPDATE items
                SET avg_cost_basis = subq.wac
                FROM (
                    SELECT
                        item_id,
                        ROUND(
                            SUM(quantity * cost_basis) / NULLIF(SUM(quantity), 0),
                            2
                        ) AS wac
                    FROM order_items
                    GROUP BY item_id
                ) subq
                WHERE items.item_id = subq.item_id;
            """)

            # ── Step 3: recalculate sale_items.unit_cost_basis_at_sale ───────
            # Use temporal WAC: only purchases on or before each sale's date
            # are included so the snapshot reflects what was actually known then.
            cur.execute("""
                UPDATE sale_items si
                SET unit_cost_basis_at_sale = subq.wac_at_sale
                FROM (
                    SELECT
                        si2.sale_item_id,
                        ROUND(
                            SUM(oi.quantity * oi.cost_basis)
                                / NULLIF(SUM(oi.quantity), 0),
                            2
                        ) AS wac_at_sale
                    FROM sale_items si2
                    JOIN sales s  ON s.sale_id   = si2.sale_id
                    JOIN order_items oi ON oi.item_id = si2.item_id
                    JOIN orders o  ON o.order_num = oi.order_num
                    WHERE o.order_date <= s.sale_date
                    GROUP BY si2.sale_item_id
                ) subq
                WHERE si.sale_item_id = subq.sale_item_id;
            """)


def create_calculate_cost_basis_trigger():
    """
    Re-apply the calculate_order_item_cost_basis trigger.
    On INSERT, uses the application-provided cost_basis (from total_cost allocation).
    On UPDATE, falls back to the pricetag-based formula.
    """
    trigger_function_sql = """
    CREATE OR REPLACE FUNCTION calculate_order_item_cost_basis()
    RETURNS TRIGGER AS $$
    DECLARE
        order_total_cost    NUMERIC(12,2);
        order_shipping_cost NUMERIC(10,2);
        sum_pricetags       NUMERIC(12,2);
        total_qty           INT;
        tax_remainder       NUMERIC(12,2);
    BEGIN
        -- INSERT: application always supplies cost_basis; use it as-is.
        IF TG_OP = 'INSERT' THEN
            RETURN NEW;
        END IF;

        -- UPDATE: recalculate using the canonical formula.
        -- Aggregate over the order, replacing the OLD row's contribution with NEW values.
        SELECT
            o.total_cost,
            o.shipping_cost,
            COALESCE(SUM(oi.pricetag * oi.quantity), 0)
                - OLD.pricetag * OLD.quantity
                + NEW.pricetag * NEW.quantity,
            COALESCE(SUM(oi.quantity), 0)
                - OLD.quantity
                + NEW.quantity
        INTO order_total_cost, order_shipping_cost, sum_pricetags, total_qty
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_num = NEW.order_num
        WHERE o.order_num = NEW.order_num
        GROUP BY o.total_cost, o.shipping_cost;

        tax_remainder := order_total_cost - order_shipping_cost - sum_pricetags;

        NEW.cost_basis := ROUND(
            NEW.pricetag
            + order_shipping_cost / NULLIF(total_qty, 0)
            + (NEW.pricetag / NULLIF(sum_pricetags, 0)) * tax_remainder
            + NEW.pas_fee_per_item,
            2
        );

        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """
    trigger_sql = """
    DROP TRIGGER IF EXISTS trigger_calculate_cost_basis ON order_items;
    CREATE TRIGGER trigger_calculate_cost_basis
        BEFORE INSERT OR UPDATE ON order_items
        FOR EACH ROW
        EXECUTE FUNCTION calculate_order_item_cost_basis();
    """
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(trigger_function_sql)
            cur.execute(trigger_sql)

