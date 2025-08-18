import os
from typing import Optional

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Integer,
    String,
    Text,
    Boolean,
    create_engine,
    func,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from passlib.context import CryptContext

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_FILE = os.path.join(BASE_DIR, "data", "envanter.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_FILE}")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
DB_FILE = engine.url.database if engine.url.drivername == "sqlite" else None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class HardwareInventory(Base):
    __tablename__ = "hardware_inventory"
    id = Column(Integer, primary_key=True, index=True)
    no = Column(String)
    fabrika = Column(String)
    blok = Column(String)
    departman = Column(String)
    donanim_tipi = Column(String)
    bilgisayar_adi = Column(String)
    marka = Column(String)
    model = Column(String)
    seri_no = Column(String)
    sorumlu_personel = Column(String)
    kullanim_alani = Column(String)
    bagli_makina_no = Column(String)
    ifs_no = Column(String)
    tarih = Column(Date)
    islem_yapan = Column(String)


class DeletedHardwareInventory(Base):
    __tablename__ = "deleted_hardware_inventory"
    id = Column(Integer, primary_key=True, index=True)
    no = Column(String)
    fabrika = Column(String)
    blok = Column(String)
    departman = Column(String)
    donanim_tipi = Column(String)
    bilgisayar_adi = Column(String)
    marka = Column(String)
    model = Column(String)
    seri_no = Column(String)
    sorumlu_personel = Column(String)
    kullanim_alani = Column(String)
    bagli_makina_no = Column(String)
    ifs_no = Column(String)
    tarih = Column(Date)
    islem_yapan = Column(String)
    deleted_at = Column(Date)


class DeletedPrinterInventory(Base):
    __tablename__ = "deleted_printer_inventory"
    id = Column(Integer, primary_key=True, index=True)
    envanter_no = Column(String)
    yazici_markasi = Column(String)
    yazici_modeli = Column(String)
    kullanim_alani = Column(String)
    ip_adresi = Column(String)
    mac = Column(String)
    hostname = Column(String)
    tarih = Column(Date)
    islem_yapan = Column(String)
    notlar = Column(Text)
    deleted_at = Column(Date)


class DeletedLicenseInventory(Base):
    __tablename__ = "deleted_license_inventory"
    id = Column(Integer, primary_key=True, index=True)
    departman = Column(String)
    kullanici = Column(String)
    yazilim_adi = Column(String)
    lisans_anahtari = Column(String)
    mail_adresi = Column(String)
    envanter_no = Column(String)
    ifs_no = Column(String)
    tarih = Column(Date)
    islem_yapan = Column(String)
    notlar = Column(Text)
    deleted_at = Column(Date)


class DeletedStockItem(Base):
    __tablename__ = "deleted_stock_items"
    id = Column(Integer, primary_key=True, index=True)
    urun_adi = Column(String)
    islem = Column(String)
    adet = Column(Integer)
    tarih = Column(Date)
    departman = Column("lokasyon", String)
    ifs_no = Column(String)
    aciklama = Column(String)
    islem_yapan = Column(String)
    deleted_at = Column(Date)


class PrinterInventory(Base):
    __tablename__ = "printer_inventory"
    id = Column(Integer, primary_key=True, index=True)
    envanter_no = Column(String)
    yazici_markasi = Column(String)
    yazici_modeli = Column(String)
    kullanim_alani = Column(String)
    ip_adresi = Column(String)
    mac = Column(String)
    hostname = Column(String)
    tarih = Column(Date)
    islem_yapan = Column(String)
    notlar = Column(Text)


class LicenseInventory(Base):
    __tablename__ = "license_inventory"
    id = Column(Integer, primary_key=True, index=True)
    departman = Column(String)
    kullanici = Column(String)
    yazilim_adi = Column(String)
    lisans_anahtari = Column(String)
    mail_adresi = Column(String)
    envanter_no = Column(String)
    ifs_no = Column(String)
    tarih = Column(Date)
    islem_yapan = Column(String)
    notlar = Column(Text)


class StockItem(Base):
    __tablename__ = "stock_tracking"
    id = Column(Integer, primary_key=True, index=True)
    urun_adi = Column(String)
    kategori = Column(String)
    marka = Column(String)
    adet = Column(Integer)
    departman = Column("lokasyon", String)
    guncelleme_tarihi = Column(Date)
    islem = Column(String)
    tarih = Column(Date)
    ifs_no = Column(String)
    aciklama = Column(String)
    islem_yapan = Column(String)


class DeletedAccessoryInventory(Base):
    __tablename__ = "deleted_accessory_inventory"
    id = Column(Integer, primary_key=True, index=True)
    urun_adi = Column(String)
    adet = Column(Integer)
    tarih = Column(Date)
    ifs_no = Column(String)
    departman = Column(String)
    kullanici = Column(String)
    aciklama = Column(String)
    islem_yapan = Column(String)
    deleted_at = Column(Date)


class AccessoryInventory(Base):
    __tablename__ = "accessory_inventory"
    id = Column(Integer, primary_key=True, index=True)
    urun_adi = Column(String)
    adet = Column(Integer)
    tarih = Column(Date)
    ifs_no = Column(String)
    departman = Column(String)
    kullanici = Column(String)
    aciklama = Column(String)
    islem_yapan = Column(String)


class RequestItem(Base):
    __tablename__ = "request_tracking"
    id = Column(Integer, primary_key=True, index=True)
    kategori = Column(String)
    donanim_tipi = Column(String)
    marka = Column(String)
    model = Column(String)
    yazilim_adi = Column(String)
    urun_adi = Column(String)
    adet = Column(Integer)
    tarih = Column(Date)
    ifs_no = Column(String)
    aciklama = Column(String)
    talep_acan = Column(String)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    is_admin = Column(Boolean, default=False)
    must_change_password = Column(Boolean, default=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, nullable=True)


class LookupItem(Base):
    __tablename__ = "lookup_items"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)
    name = Column(String)


class ActivityLog(Base):
    __tablename__ = "activity_log"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    action = Column(String)
    timestamp = Column(DateTime, default=func.now())


def init_db():
    """Create database tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
    migrations_dir = os.path.join(os.path.dirname(__file__), "db", "migrations")
    if os.path.isdir(migrations_dir) and DB_FILE:
        import glob
        import sqlite3

        with sqlite3.connect(DB_FILE) as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (filename TEXT PRIMARY KEY)"
            )
            applied = {
                row[0] for row in con.execute("SELECT filename FROM schema_migrations")
            }
            for path in sorted(glob.glob(os.path.join(migrations_dir, "*.sql"))):
                filename = os.path.basename(path)
                if filename in applied:
                    continue
                with open(path, "r") as fh:
                    con.executescript(fh.read())
                con.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (?)", (filename,)
                )

            # Ensure older databases have the printer inventory number column
            for table in ("printer_inventory", "deleted_printer_inventory"):
                cols = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
                if "envanter_no" not in cols:
                    con.execute(
                        f"ALTER TABLE {table} ADD COLUMN envanter_no TEXT"
                    )


def init_admin():
    """Create default admin user using environment variables."""
    username = os.getenv("ADMIN_USERNAME")
    password_plain = os.getenv("ADMIN_PASSWORD")
    if not username or not password_plain:
        return
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == username).first():
            admin = User(
                username=username,
                password=pwd_context.hash(password_plain),
                is_admin=True,
                must_change_password=True,
                first_name="Admin",
                last_name="",
                email="",
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
