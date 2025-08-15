-- Her envanter için en güncel (son) log satırını dönen VIEW
DROP VIEW IF EXISTS v_inventory_latest;
CREATE VIEW v_inventory_latest AS
SELECT id, inventory_type, inventory_id, old_user_id, new_user_id,
       old_location, new_location, action, note, changed_by, change_date
FROM (
  SELECT il.*,
         ROW_NUMBER() OVER (
           PARTITION BY inventory_type, inventory_id
           ORDER BY change_date DESC, id DESC
         ) AS rn
  FROM inventory_logs il
)
WHERE rn = 1;

-- Sorgu hızlandırma (window partition taraması için yardımcı index’ler)
CREATE INDEX IF NOT EXISTS idx_il_partition
  ON inventory_logs (inventory_type, inventory_id, change_date DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_il_changed_by ON inventory_logs (changed_by);

-- Not: SQLite sürümü çok eskiyse ve ROW_NUMBER() desteklemiyorsa, aşağıdaki fallback VIEW kullanılabilir:
-- DROP VIEW IF EXISTS v_inventory_latest;
-- CREATE VIEW v_inventory_latest AS
-- SELECT il.*
-- FROM inventory_logs il
-- WHERE NOT EXISTS (
--   SELECT 1 FROM inventory_logs nx
--   WHERE nx.inventory_type = il.inventory_type
--     AND nx.inventory_id   = il.inventory_id
--     AND (nx.change_date > il.change_date OR (nx.change_date = il.change_date AND nx.id > il.id))
-- );
