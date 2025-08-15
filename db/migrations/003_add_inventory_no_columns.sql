-- Add columns to track inventory number changes
ALTER TABLE inventory_logs ADD COLUMN old_inventory_no TEXT;
ALTER TABLE inventory_logs ADD COLUMN new_inventory_no TEXT;
