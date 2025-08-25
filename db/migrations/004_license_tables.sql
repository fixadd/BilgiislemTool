-- Create license table and log table
CREATE TABLE IF NOT EXISTS license (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  adi TEXT NOT NULL,
  anahtar TEXT,
  sorumlu_personel TEXT,
  ifs_no TEXT,
  tarih DATE,
  islem_yapan TEXT,
  mail_adresi TEXT,
  inventory_id INTEGER REFERENCES hardware_inventory(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_license_inventory_id ON license(inventory_id);

CREATE TABLE IF NOT EXISTS license_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  license_id INTEGER NOT NULL REFERENCES license(id) ON DELETE CASCADE,
  field TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT,
  changed_by TEXT,
  changed_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_license_log_license_id ON license_log(license_id);
