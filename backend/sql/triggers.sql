-- ============================================
-- TRIGGER: calculate_order_item_cost_basis
-- ============================================
-- Automatically calculates and stores cost_basis in order_items table
-- when rows are inserted or updated.
-- 
-- Cost basis formula: pricetag * (1 + tax_rate) + pas_fee_per_item + (shipping_cost / num_items_in_order)

CREATE OR REPLACE FUNCTION calculate_order_item_cost_basis()
RETURNS TRIGGER AS $$
DECLARE
    order_tax_rate NUMERIC(5,4);
    order_shipping_cost NUMERIC(10,2);
    num_items_in_order INT;
    calculated_cost_basis NUMERIC(12,2);
BEGIN
    -- Get order details
    SELECT o.tax_rate, o.shipping_cost, 
           (SELECT COALESCE(SUM(quantity), 0) FROM order_items WHERE order_num = COALESCE(NEW.order_num, OLD.order_num))
           + CASE WHEN TG_OP = 'INSERT' THEN NEW.quantity ELSE 0 END
           - CASE WHEN TG_OP = 'UPDATE' AND OLD.order_num = NEW.order_num THEN OLD.quantity ELSE 0 END
    INTO order_tax_rate, order_shipping_cost, num_items_in_order
    FROM orders o
    WHERE o.order_num = COALESCE(NEW.order_num, OLD.order_num);
    
    -- Calculate cost basis
    calculated_cost_basis := ROUND(
        COALESCE(NEW.pricetag, OLD.pricetag) * (1 + order_tax_rate)
        + COALESCE(NEW.pas_fee_per_item, OLD.pas_fee_per_item)
        + (order_shipping_cost / NULLIF(num_items_in_order, 0)),
        2
    );
    
    -- Set the cost_basis value
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        NEW.cost_basis := calculated_cost_basis;
        RETURN NEW;
    ELSE
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_calculate_cost_basis ON order_items;
CREATE TRIGGER trigger_calculate_cost_basis
    BEFORE INSERT OR UPDATE ON order_items
    FOR EACH ROW
    EXECUTE FUNCTION calculate_order_item_cost_basis();


-- ============================================
-- TRIGGER: update_item_avg_cost_basis
-- ============================================
-- Automatically updates avg_cost_basis in the items table when order_items
-- are inserted, updated, or deleted. Uses the precalculated cost_basis column.
-- 
-- Only updates the affected item(s) for efficiency.

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

DROP TRIGGER IF EXISTS trigger_update_item_avg_cost_basis ON order_items;
CREATE TRIGGER trigger_update_item_avg_cost_basis
    AFTER INSERT OR UPDATE OR DELETE ON order_items
    FOR EACH ROW
    EXECUTE FUNCTION update_item_avg_cost_basis();
