CREATE TABLE items (
    item_id SERIAL PRIMARY KEY,
    description TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    retail_value NUMERIC(12,2),
    avg_unit_cost_basis NUMERIC(12,2)
);

CREATE TABLE orders (
    order_num VARCHAR(50) PRIMARY KEY,
    order_date DATE NOT NULL,
    seller TEXT,
    total_cost NUMERIC(10,2) NOT NULL,
    shipping_cost NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    tax_rate NUMERIC(5,4) DEFAULT 0.0975
);

CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    item_id INT REFERENCES items(item_id),
    quantity INT NOT NULL,
    purchase_price_per_item NUMERIC(12,2),
    order_num VARCHAR(50) NOT NULL REFERENCES orders(order_num),
    pas_fee_per_item NUMERIC(10,2) NOT NULL
);

CREATE TABLE sales (
    sale_id SERIAL PRIMARY KEY,
    sale_date DATE NOT NULL,
    platform TEXT NOT NULL,
    sale_revenue NUMERIC(12,2) NOT NULL,
);

CREATE TABLE sale_items (
    sale_item_id SERIAL PRIMARY KEY,
    sale_id INT REFERENCES sales(sale_id),
    item_id INT REFERENCES items(item_id),
    quantity INT NOT NULL CHECK (quantity > 0)
    unit_cost_basis_at_sale NUMERIC(12,2)
);

CREATE TABLE returns (
    return_id SERIAL PRIMARY KEY,
    return_date DATE NOT NULL,
    order_num VARCHAR(50) NOT NULL REFERENCES orders(order_num),
    refund_value NUMERIC(10,2)
);

CREATE TABLE return_items (
    return_item_id SERIAL PRIMARY KEY,
    return_id INT NOT NULL REFERENCES returns(return_id) ON DELETE CASCADE,
    item_id INT NOT NULL REFERENCES items(item_id),
    quantity INT NOT NULL CHECK (quantity > 0),
    UNIQUE (return_id, item_id)
)

CREATE TABLE other_expenses (
    expense_id SERIAL PRIMARY KEY,
    expense_date DATE NOT NULL,
    description TEXT NOT NULL,
    expense_cost NUMERIC(12,2) NOT NULL
);

CREATE OR REPLACE VIEW cost_basis AS
WITH item_totals AS (
    SELECT
        order_num,
        SUM(quantity) AS num_items
    FROM order_items
    GROUP BY order_num
),
unit_costs AS (
    SELECT
        o.order_num,
        oi.item_id,
        oi.quantity,
        ROUND(
            oi.purchase_price_per_item * (1 + o.tax_rate)
            + oi.pas_fee_per_item
            + (o.shipping_cost / NULLIF(it.num_items, 0)),
            2
        ) AS unit_cost_basis
    FROM order_items oi
    JOIN orders o ON o.order_num = oi.order_num
    JOIN item_totals it ON it.order_num = oi.order_num
)
SELECT
    uc.order_num,
    uc.item_id,
    uc.quantity,
    uc.unit_cost_basis,
    ROUND(
        SUM(uc.quantity * uc.unit_cost_basis)
            OVER (PARTITION BY uc.item_id)
        / NULLIF(SUM(uc.quantity)
            OVER (PARTITION BY uc.item_id), 0),
        2
    ) AS avg_unit_cost_basis
FROM unit_costs uc;

