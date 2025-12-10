CREATE TABLE items (
    item_id SERIAL PRIMARY KEY,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    retail_value NUMERIC(12,2)
);

CREATE TABLE orders (
    order_num VARCHAR(50) PRIMARY KEY,
    order_date DATE NOT NULL,
    seller TEXT,
    order_cost NUMERIC(10,2) NOT NULL,
    shipping_cost NUMERIC(10,2) NOT NULL
);

CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    item_id INT REFERENCES items(item_id),
    quantity INT NOT NULL,
    order_num VARCHAR(50) NOT NULL REFERENCES orders(order_num)
    pas_fee_per_item NUMERIC(10,2) NOT NULL
);

CREATE TABLE sales (
    sale_id SERIAL PRIMARY KEY,
    sale_date DATE NOT NULL,
    item_id INT NOT NULL REFERENCES items(item_id),
    quantity INT NOT NULL,
    platform TEXT NOT NULL,
    payout_amount NUMERIC(12,2) NOT NULL
);

CREATE TABLE other_expenses (
    expense_id SERIAL PRIMARY KEY,
    expense_date DATE NOT NULL,
    description TEXT NOT NULL,
    cost NUMERIC(12,2) NOT NULL
);

CREATE TABLE returns (
    return_id SERIAL PRIMARY KEY,
    return_date DATE NOT NULL,
    order_num VARCHAR(50) NOT NULL REFERENCES orders(order_num),
    item_id INT NOT NULL REFERENCES items(item_id),
    quantity INT NOT NULL CHECK (quantity > 0),
    reason TEXT,
    refund_amount NUMERIC(10,2)
);