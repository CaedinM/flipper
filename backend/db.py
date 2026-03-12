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
        ),
        order_totals AS (
            SELECT
                oi.order_num,
                SUM(oi.pricetag * oi.quantity * (1 + o.tax_rate)) AS total_items_with_tax,
                SUM(oi.quantity)                                   AS total_qty
            FROM order_items oi
            JOIN orders o ON o.order_num = oi.order_num
            GROUP BY oi.order_num
        ),
        computed_cost AS (
            SELECT
                oi.item_id,
                oi.quantity,
                ROUND(
                    oi.pricetag * (1 + o.tax_rate)
                    + (o.total_cost - ot.total_items_with_tax) / NULLIF(ot.total_qty, 0)
                    + oi.pas_fee_per_item,
                    2
                ) AS unit_cost_basis
            FROM order_items oi
            JOIN orders o ON o.order_num = oi.order_num
            JOIN order_totals ot ON ot.order_num = oi.order_num
        ),
        avg_cost AS (
            SELECT
                item_id,
                ROUND(SUM(quantity * unit_cost_basis) / NULLIF(SUM(quantity), 0), 2) AS avg_cost_basis
            FROM computed_cost
            GROUP BY item_id
        )
        SELECT
            i.description AS "Item",
            i.category AS "Category",
            ac.avg_cost_basis AS "Cost Basis",
            i.retail_value AS "Retail Value",
            COALESCE(p.total_purchased, 0) - COALESCE(s.total_sold, 0) - COALESCE(r.total_returned, 0) AS "Stock"
        FROM items i
        LEFT JOIN purchased p ON p.item_id = i.item_id
        LEFT JOIN sold s ON s.item_id = i.item_id
        LEFT JOIN returns r ON r.item_id = i.item_id
        LEFT JOIN avg_cost ac ON ac.item_id = i.item_id
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
                # Compute cost_basis per item from total_cost (the actual amount paid),
                # allocated proportionally by pricetag so the sum equals total_cost.
                total_pricetag_value = sum(r["pricetag"] * r["quantity"] for r in items_rows)
                total_qty = sum(r["quantity"] for r in items_rows)
                values = []
                for r in items_rows:
                    if total_pricetag_value > 0:
                        cost_basis = round(
                            order_data["total_cost"] * r["pricetag"] / total_pricetag_value
                            + r["pas_fee_per_item"],
                            2,
                        )
                    else:
                        # Fallback: equal allocation when all pricetags are zero
                        cost_basis = round(
                            order_data["total_cost"] / total_qty + r["pas_fee_per_item"],
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

                # commits automatically when exiting "with get_conn() as conn:" if no exception

def insert_sale_with_items(sale_data: dict, items_rows: list[dict]):
    """
    sale_data: dict for sales table (sale_date, platform, sale_revenue)
    items_rows: list of dicts for sale_items table rows (item_id, quantity)
    unit_cost_basis_at_sale is automatically fetched from items.avg_cost_basis
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
            
            # Get avg_cost_basis for each item from the items table
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
            
            # insert into sale_items with cost basis from items table
            values = [
                (
                    sale_id,
                    r["item_id"],
                    r["quantity"],
                    cost_basis_map.get(r["item_id"], 0)  # Use avg_cost_basis from items table
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
            i.description AS "Item Description",
            i.category AS "Category",
            oi.quantity AS "Quantity",
            oi.pricetag AS "Price Tag",
            oi.pas_fee_per_item AS "PAS Fee Per Item",
            oi.cost_basis AS "Cost Basis"
        FROM order_items oi
        JOIN items i ON oi.item_id = i.item_id
        WHERE oi.order_num = %s
        ORDER BY i.description
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
            # commits automatically when exiting "with get_conn() as conn:" if no exception

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
        order_tax_rate NUMERIC(5,4);
        order_shipping_cost NUMERIC(10,2);
        num_items_in_order INT;
        calculated_cost_basis NUMERIC(12,2);
    BEGIN
        -- On INSERT, if cost_basis was already provided by the application, use it directly.
        IF TG_OP = 'INSERT' AND NEW.cost_basis IS NOT NULL THEN
            RETURN NEW;
        END IF;

        SELECT o.tax_rate, o.shipping_cost,
               (SELECT COALESCE(SUM(quantity), 0) FROM order_items WHERE order_num = COALESCE(NEW.order_num, OLD.order_num))
               + CASE WHEN TG_OP = 'INSERT' THEN NEW.quantity ELSE 0 END
               - CASE WHEN TG_OP = 'UPDATE' AND OLD.order_num = NEW.order_num THEN OLD.quantity ELSE 0 END
        INTO order_tax_rate, order_shipping_cost, num_items_in_order
        FROM orders o
        WHERE o.order_num = COALESCE(NEW.order_num, OLD.order_num);

        calculated_cost_basis := ROUND(
            COALESCE(NEW.pricetag, OLD.pricetag) * (1 + order_tax_rate)
            + COALESCE(NEW.pas_fee_per_item, OLD.pas_fee_per_item)
            + (order_shipping_cost / NULLIF(num_items_in_order, 0)),
            2
        );

        IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
            NEW.cost_basis := calculated_cost_basis;
            RETURN NEW;
        ELSE
            RETURN OLD;
        END IF;
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


def create_update_avg_cost_basis_trigger():
    """
    Create or replace the trigger function and trigger that automatically updates
    avg_cost_basis in the items table when order_items are inserted, updated, or deleted.
    """
    trigger_function_sql = """
    CREATE OR REPLACE FUNCTION update_item_avg_cost_basis()
    RETURNS TRIGGER AS $$
    DECLARE
        affected_item_id INT;
    BEGIN
        -- Determine which item_id was affected
        IF TG_OP = 'DELETE' THEN
            affected_item_id := OLD.item_id;
        ELSE
            affected_item_id := NEW.item_id;
        END IF;
        
        -- Update avg_cost_basis for only the affected item using precalculated cost_basis
        WITH item_avg_cost AS (
            SELECT
                ROUND(
                    SUM(quantity * cost_basis) / NULLIF(SUM(quantity), 0),
                    2
                ) AS avg_cost_basis
            FROM order_items
            WHERE item_id = affected_item_id
            AND cost_basis IS NOT NULL
        )
        -- Update avg_cost_basis (will be NULL if item has no order_items)
        UPDATE items
        SET avg_cost_basis = (
            SELECT avg_cost_basis FROM item_avg_cost
        )
        WHERE item_id = affected_item_id;
        
        RETURN COALESCE(NEW, OLD);
    END;
    $$ LANGUAGE plpgsql;
    """
    
    trigger_sql = """
    DROP TRIGGER IF EXISTS trigger_update_item_avg_cost_basis ON order_items;
    CREATE TRIGGER trigger_update_item_avg_cost_basis
        AFTER INSERT OR UPDATE OR DELETE ON order_items
        FOR EACH ROW
        EXECUTE FUNCTION update_item_avg_cost_basis();
    """
    
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            # Create the function
            cur.execute(trigger_function_sql)
            # Create the trigger
            cur.execute(trigger_sql)
            # commits automatically when exiting "with get_conn() as conn:" if no exception

