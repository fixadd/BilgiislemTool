-- Envanter hareket log tablosu
CREATE TABLE IF NOT EXISTS inventory_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  inventory_type TEXT NOT NULL,           -- 'pc' | 'license' | 'accessory' | 'stock' ...
  inventory_id INTEGER NOT NULL,          -- ilgili tablonun ID'si
  old_user_id INTEGER,                    -- önceki kullanıcı (NULL olabilir)
  new_user_id INTEGER,                    -- yeni kullanıcı (NULL olabilir, iade ise NULL)
  old_location TEXT,                      -- önceki konum
  new_location TEXT,                      -- yeni konum
  action TEXT NOT NULL,                   -- 'assign' | 'return' | 'move' | 'relabel' ...
  note TEXT,                              -- opsiyonel açıklama
  changed_by INTEGER NOT NULL,            -- işlemi yapan admin / user ID
  change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sorgu hızları için index'ler
CREATE INDEX IF NOT EXISTS idx_inventory_logs_inv
  ON inventory_logs (inventory_type, inventory_id);

CREATE INDEX IF NOT EXISTS idx_inventory_logs_date
  ON inventory_logs (change_date DESC);

CREATE INDEX IF NOT EXISTS idx_inventory_logs_users
  ON inventory_logs (old_user_id, new_user_id);
