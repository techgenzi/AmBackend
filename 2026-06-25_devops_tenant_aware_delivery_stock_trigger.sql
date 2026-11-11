-- Migration script: Make update_product_count_on_delivery_items trigger tenant-aware.
-- This ensures that if a tenant has disabled stock management (manage_stock = false)
-- in the custome_config table, the trigger will not alter the products.product_count values.

CREATE OR REPLACE FUNCTION public.update_product_count_on_delivery_items()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_compcode bigint;
    v_manage_stock boolean := true;
BEGIN
    -- 1. Identify tenant code (compcode) from customer purchase items
    SELECT compcode INTO v_compcode 
    FROM customer_purchase_items 
    WHERE items_id = COALESCE(NEW."workOrderLineId", OLD."workOrderLineId");

    -- 2. Check if this tenant has stock management disabled in custome_config
    SELECT COALESCE((config_data->>'manage_stock')::boolean, true) INTO v_manage_stock
    FROM custome_config
    WHERE compcode = v_compcode 
      AND module_name = 'inventory' 
      AND config_type = 'settings' 
      AND deleted IS NOT TRUE;

    -- 3. If stock management is disabled for this tenant, skip modifying the stock count
    IF v_manage_stock = false THEN
        RETURN NEW;
    END IF;

    -- Case 1: New delivery item is inserted
    IF TG_OP = 'INSERT' THEN
        -- If the item is marked as deleted, increase the product count
        IF NEW.deleted = TRUE THEN
            UPDATE products  
            SET product_count = product_count + NEW.quantity  
            FROM customer_purchase_items  
            WHERE products.product_id = customer_purchase_items.product_id  
            AND customer_purchase_items.items_id = NEW."workOrderLineId";
        -- Otherwise, decrease the product count
        ELSE
            UPDATE products  
            SET product_count = product_count - NEW.quantity  
            FROM customer_purchase_items  
            WHERE products.product_id = customer_purchase_items.product_id  
            AND customer_purchase_items.items_id = NEW."workOrderLineId";
        END IF;

    -- Case 2: Quantity is updated (adjust the difference)
    ELSIF TG_OP = 'UPDATE' AND NEW.quantity IS DISTINCT FROM OLD.quantity THEN
        UPDATE products  
        SET product_count = product_count + (NEW.quantity - OLD.quantity)  
        FROM customer_purchase_items  
        WHERE products.product_id = customer_purchase_items.product_id  
        AND customer_purchase_items.items_id = NEW."workOrderLineId"
        AND NEW.deleted = FALSE; -- Only affect active items

    -- Case 3: Marking as deleted (increase product_count back)
    ELSIF TG_OP = 'UPDATE' AND OLD.deleted = FALSE AND NEW.deleted = TRUE THEN
        UPDATE products  
        SET product_count = product_count + OLD.quantity  
        FROM customer_purchase_items  
        WHERE products.product_id = customer_purchase_items.product_id  
        AND customer_purchase_items.items_id = OLD."workOrderLineId";
    END IF;

    RETURN NEW;
END;
$function$;
