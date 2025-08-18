import sqlite3
from services import log_service


def setup_db(db_path: str):
    con = sqlite3.connect(db_path)
    with open("db/migrations/001_inventory_logs.sql") as f:
        con.executescript(f.read())
    # create users and lookup_items tables
    con.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT
        );
        CREATE TABLE lookup_items (
            id INTEGER PRIMARY KEY,
            type TEXT,
            name TEXT
        );
        """
    )
    return con


def test_inventory_log_returns_joined_names(tmp_path):
    db_file = tmp_path / "envanter.db"
    con = setup_db(db_file)
    cur = con.cursor()
    cur.execute("INSERT INTO users VALUES (1, 'u1', 'Ali', 'Veli')")
    cur.execute("INSERT INTO users VALUES (2, 'u2', 'Ayse', 'Fatma')")
    cur.execute("INSERT INTO lookup_items VALUES (10, 'lokasyon', 'Depo')")
    cur.execute("INSERT INTO lookup_items VALUES (20, 'lokasyon', 'Ofis')")
    cur.execute(
        "INSERT INTO inventory_logs (inventory_type, inventory_id, old_user_id, new_user_id, old_location, new_location, action, changed_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("pc", 1, 1, 2, 10, 20, "move", 1),
    )
    con.commit()
    con.close()

    log_service.DB_PATH = str(db_file)
    rows = log_service.get_inventory_logs(inventory_type="pc", inventory_id=1)
    assert rows
    row = rows[0]
    assert row["old_user_name"] == "Ali Veli"
    assert row["new_user_name"] == "Ayse Fatma"
    assert row["old_location"] == "Depo"
    assert row["new_location"] == "Ofis"
