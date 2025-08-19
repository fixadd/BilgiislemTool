import os
import sys
import sqlite3

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import services.log_service as log_service


def test_get_inventory_items_handles_mixed_number_types(tmp_path):
    db_path = tmp_path / "inv.db"
    con = sqlite3.connect(db_path)
    con.execute(
        "CREATE TABLE hardware_inventory (id INTEGER PRIMARY KEY, bilgisayar_adi TEXT, no TEXT)"
    )
    con.execute(
        "CREATE TABLE stock_tracking (id INTEGER PRIMARY KEY, urun_adi TEXT)"
    )
    con.execute(
        "INSERT INTO hardware_inventory (id, bilgisayar_adi, no) VALUES (1, 'Laptop', 'ABC123')"
    )
    con.execute(
        "INSERT INTO stock_tracking (id, urun_adi) VALUES (2, 'Mouse')"
    )
    con.commit()
    con.close()

    original_path = log_service.DB_PATH
    log_service.DB_PATH = str(db_path)
    try:
        items = log_service.get_inventory_items()
    finally:
        log_service.DB_PATH = original_path

    assert items == [
        {"type": "stock", "id": 2, "name": "Mouse", "inv_no": "2"},
        {"type": "pc", "id": 1, "name": "Laptop", "inv_no": "ABC123"},
    ]
