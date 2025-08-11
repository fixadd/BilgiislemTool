# main.py
# FastAPI + SQLAlchemy + Docker uyumlu envanter sistemi backend yapisi

from fastapi import FastAPI, Depends, Request, Form, HTTPException, status, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from io import BytesIO
import pandas as pd
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import date, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Date, Text, Boolean, text, inspect, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.sessions import SessionMiddleware
import os
import json
import base64
from passlib.context import CryptContext

# --- DATABASE AYARI (Docker icin degisebilir) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.getenv("DB_FILE", os.path.join(BASE_DIR, "data", "envanter.db"))
DATABASE_URL = f"sqlite:///{DB_FILE}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
SETTINGS_FILE = os.path.join(BASE_DIR, "data", "column_settings.json")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- SQLALCHEMY MODELLER ---
class HardwareInventory(Base):
    __tablename__ = "hardware_inventory"
    id = Column(Integer, primary_key=True, index=True)
    demirbas_adi = Column(String)
    marka = Column(String)
    model = Column(String)
    seri_no = Column(String)
    lokasyon = Column(String)
    zimmetli_kisi = Column(String)
    notlar = Column(Text)

class DeletedHardwareInventory(Base):
    __tablename__ = "deleted_hardware_inventory"
    id = Column(Integer, primary_key=True, index=True)
    demirbas_adi = Column(String)
    marka = Column(String)
    model = Column(String)
    seri_no = Column(String)
    lokasyon = Column(String)
    zimmetli_kisi = Column(String)
    notlar = Column(Text)
    deleted_at = Column(Date)

class DeletedPrinterInventory(Base):
    __tablename__ = "deleted_printer_inventory"
    id = Column(Integer, primary_key=True, index=True)
    yazici_markasi = Column(String)
    yazici_modeli = Column(String)
    kullanim_alani = Column(String)
    ip_adresi = Column(String)
    mac = Column(String)
    hostname = Column(String)
    notlar = Column(Text)
    deleted_at = Column(Date)

class DeletedLicenseInventory(Base):
    __tablename__ = "deleted_license_inventory"
    id = Column(Integer, primary_key=True, index=True)
    yazilim_adi = Column(String)
    lisans_anahtari = Column(String)
    adet = Column(Integer)
    satin_alma_tarihi = Column(Date)
    bitis_tarihi = Column(Date)
    zimmetli_kisi = Column(String)
    notlar = Column(Text)
    deleted_at = Column(Date)

class DeletedStockItem(Base):
    __tablename__ = "deleted_stock_items"
    id = Column(Integer, primary_key=True, index=True)
    urun_adi = Column(String)
    kategori = Column(String)
    marka = Column(String)
    adet = Column(Integer)
    lokasyon = Column(String)
    guncelleme_tarihi = Column(Date)
    deleted_at = Column(Date)

class PrinterInventory(Base):
    __tablename__ = "printer_inventory"
    id = Column(Integer, primary_key=True, index=True)
    yazici_markasi = Column(String)
    yazici_modeli = Column(String)
    kullanim_alani = Column(String)
    ip_adresi = Column(String)
    mac = Column(String)
    hostname = Column(String)
    notlar = Column(Text)

class LicenseInventory(Base):
    __tablename__ = "license_inventory"
    id = Column(Integer, primary_key=True, index=True)
    yazilim_adi = Column(String)
    lisans_anahtari = Column(String)
    adet = Column(Integer)
    satin_alma_tarihi = Column(Date)
    bitis_tarihi = Column(Date)
    zimmetli_kisi = Column(String)
    notlar = Column(Text)

class StockItem(Base):
    __tablename__ = "stock_tracking"
    id = Column(Integer, primary_key=True, index=True)
    urun_adi = Column(String)
    kategori = Column(String)
    marka = Column(String)
    adet = Column(Integer)
    lokasyon = Column(String)
    guncelleme_tarihi = Column(Date)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    is_admin = Column(Boolean, default=False)


class LookupItem(Base):
    """Generic lookup table for dropdown values."""

    __tablename__ = "lookup_items"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)
    name = Column(String)


def init_db():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    if not os.path.exists(DB_FILE):
        open(DB_FILE, "w").close()
    Base.metadata.create_all(bind=engine)


def init_admin():
    db = SessionLocal()
    try:
        username = base64.b64decode("YWRtaW4=").decode()
        password_plain = base64.b64decode("YWRtaW4=").decode()
        if not db.query(User).filter(User.username == username).first():
            admin = User(
                username=username,
                password=pwd_context.hash(password_plain),
                is_admin=True,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


init_db()
init_admin()


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_settings(data):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f)


def get_table_columns(table_name: str) -> List[str]:
    return [col["name"] for col in inspect(engine).get_columns(table_name)]


def get_user_settings(username: str, table_name: str):
    data = load_settings()
    return data.get(username, {}).get(table_name, {})


def set_user_settings(username: str, table_name: str, settings: dict):
    data = load_settings()
    data.setdefault(username, {})[table_name] = settings
    save_settings(data)

def cleanup_deleted(db: Session):
    cutoff = date.today() - timedelta(days=15)
    db.query(DeletedHardwareInventory).filter(DeletedHardwareInventory.deleted_at < cutoff).delete()
    db.query(DeletedPrinterInventory).filter(DeletedPrinterInventory.deleted_at < cutoff).delete()
    db.query(DeletedLicenseInventory).filter(DeletedLicenseInventory.deleted_at < cutoff).delete()
    db.query(DeletedStockItem).filter(DeletedStockItem.deleted_at < cutoff).delete()
    db.commit()

# --- Pydantic Şemalar ---
class HardwareItem(BaseModel):
    id: Optional[int]
    demirbas_adi: str
    marka: str
    model: str
    seri_no: str
    lokasyon: str
    zimmetli_kisi: str
    notlar: Optional[str]
    class Config:
        orm_mode = True

class PrinterItem(BaseModel):
    id: Optional[int]
    yazici_markasi: str
    yazici_modeli: str
    kullanim_alani: str
    ip_adresi: str
    mac: str
    hostname: str
    notlar: Optional[str]
    class Config:
        orm_mode = True

class LicenseItem(BaseModel):
    id: Optional[int]
    yazilim_adi: str
    lisans_anahtari: str
    adet: int
    satin_alma_tarihi: Optional[date]
    bitis_tarihi: Optional[date]
    zimmetli_kisi: str
    notlar: Optional[str]
    class Config:
        orm_mode = True

class StockItemSchema(BaseModel):
    id: Optional[int]
    urun_adi: str
    kategori: str
    marka: str
    adet: int
    lokasyon: str
    guncelleme_tarihi: Optional[date]
    class Config:
        orm_mode = True

class ColumnDefinition(BaseModel):
    name: str
    type: str

class CreateTableSchema(BaseModel):
    table_name: str
    columns: List[ColumnDefinition]


class ColumnSettings(BaseModel):
    order: List[str]
    visible: List[str]
    widths: Dict[str, int] = Field(default_factory=dict)

class DeleteIds(BaseModel):
    ids: List[int]

# --- FastAPI Uygulaması ---
app = FastAPI()
app.mount("/image", StaticFiles(directory="image"), name="image")
templates = Jinja2Templates(directory="templates")

# Oturum yönetimi için SessionMiddleware ekle
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")

# --- Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Authentication ---
def require_login(request: Request, db: Session = Depends(get_db)):
    username = request.session.get("username")
    if not username:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


# --- Ana Sayfa ve Giriş ---
# Hem "/" hem de "/login" adreslerine gelen istekler aynı sayfayı döndürür.
@app.get("/", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    """Giriş sayfasını döndür."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if user and pwd_context.verify(password, user.password):
        request.session["username"] = user.username
        return RedirectResponse(url="/home", status_code=303)
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": "Hatalı kullanıcı adı veya şifre"}
    )


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/home", status_code=303)


@app.get("/home", response_class=HTMLResponse)
def home_page(
    request: Request,
    db: Session = Depends(get_db),
):
    """Ana ekranı döndür, kullanıcı giriş yapmadıysa yönlendir."""
    username = request.session.get("username")
    if not username:
        return RedirectResponse(url="/login", status_code=303)

    factory_rows = (
        db.query(
            StockItem.lokasyon,
            StockItem.kategori,
            func.sum(StockItem.adet).label("adet"),
        )
        .group_by(StockItem.lokasyon, StockItem.kategori)
        .all()
    )
    factories: Dict[str, List[Dict[str, int]]] = {}
    for lokasyon, kategori, adet in factory_rows:
        factories.setdefault(lokasyon or "Bilinmiyor", []).append(
            {"kategori": kategori, "adet": adet}
        )

    recent = (
        db.query(StockItem)
        .order_by(StockItem.id.desc())
        .limit(5)
        .all()
    )
    return templates.TemplateResponse(
        "main.html",
        {
            "request": request,
            "username": username,
            "factories": factories,
            "recent": recent,
        },
    )


@app.get("/admin", response_class=HTMLResponse)
def admin_page(
    request: Request,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Yetkisiz")
    users = db.query(User).all()
    return templates.TemplateResponse(
        "admin.html", {"request": request, "users": users}
    )


@app.post("/admin/create")
def admin_create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Yetkisiz")
    if db.query(User).filter(User.username == username).first():
        users = db.query(User).all()
        return templates.TemplateResponse(
            "admin.html",
            {
                "request": request,
                "users": users,
                "error": "Kullanıcı zaten var",
            },
        )
    db.add(User(username=username, password=pwd_context.hash(password)))
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/delete/{user_id}")
def admin_delete_user(
    user_id: int,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Yetkisiz")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    if target.is_admin:
        raise HTTPException(status_code=400, detail="Admin kullanıcı silinemez")
    db.delete(target)
    db.commit()
    return RedirectResponse("/admin", status_code=303)


# --- Takip Sayfaları (HTML) ---

@app.get("/lists", response_class=HTMLResponse)
def lists_page(
    request: Request,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Lookup list management page."""
    brands = db.query(LookupItem).filter(LookupItem.type == "marka").all()
    locations = db.query(LookupItem).filter(LookupItem.type == "lokasyon").all()
    categories = db.query(LookupItem).filter(LookupItem.type == "kategori").all()
    softwares = db.query(LookupItem).filter(LookupItem.type == "yazilim").all()
    return templates.TemplateResponse(
        "listeler.html",
        {
            "request": request,
            "brands": brands,
            "locations": locations,
            "categories": categories,
            "softwares": softwares,
        },
    )


@app.post("/lists/add")
def add_list_item(
    item_type: str = Form(...),
    name: str = Form(...),
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    db.add(LookupItem(type=item_type, name=name))
    db.commit()
    return RedirectResponse("/lists", status_code=303)


@app.get("/inventory", response_class=HTMLResponse)
def inventory_page(
    request: Request,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Donanım envanterini listeleyen sayfa."""
    items = db.query(HardwareInventory).limit(50).all()
    table_name = HardwareInventory.__tablename__
    columns = get_table_columns(table_name)
    settings = get_user_settings(user.username, table_name)
    order = settings.get("order", columns)
    visible = settings.get("visible", columns)
    widths = settings.get("widths", {})
    display_columns = [c for c in order if c in visible]
    brands = db.query(LookupItem).filter(LookupItem.type == "marka").all()
    locations = db.query(LookupItem).filter(LookupItem.type == "lokasyon").all()
    return templates.TemplateResponse(
        "envanter.html",
        {
            "request": request,
            "items": items,
            "count": len(items),
            "columns": display_columns,
            "table_name": table_name,
            "column_widths": widths,
            "brands": brands,
            "locations": locations,
        },
    )


@app.post("/inventory/add")
def add_inventory_form(
    item_id: Optional[int] = Form(None),
    demirbas_adi: str = Form(...),
    marka: str = Form(...),
    model: str = Form(...),
    seri_no: str = Form(...),
    lokasyon: str = Form(...),
    zimmetli_kisi: str = Form(...),
    notlar: str = Form(""),
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if item_id:
        item = db.query(HardwareInventory).get(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Kayıt bulunamadı")
        item.demirbas_adi = demirbas_adi
        item.marka = marka
        item.model = model
        item.seri_no = seri_no
        item.lokasyon = lokasyon
        item.zimmetli_kisi = zimmetli_kisi
        item.notlar = notlar
    else:
        db_item = HardwareInventory(
            demirbas_adi=demirbas_adi,
            marka=marka,
            model=model,
            seri_no=seri_no,
            lokasyon=lokasyon,
            zimmetli_kisi=zimmetli_kisi,
            notlar=notlar,
        )
        db.add(db_item)
    db.commit()
    return RedirectResponse("/inventory", status_code=303)


@app.post("/inventory/delete/{item_id}")
def delete_inventory_form(
    item_id: int,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    item = (
        db.query(HardwareInventory)
        .filter(HardwareInventory.id == item_id)
        .first()
    )
    if item:
        deleted = DeletedHardwareInventory(
            id=item.id,
            demirbas_adi=item.demirbas_adi,
            marka=item.marka,
            model=item.model,
            seri_no=item.seri_no,
            lokasyon=item.lokasyon,
            zimmetli_kisi=item.zimmetli_kisi,
            notlar=item.notlar,
            deleted_at=date.today(),
        )
        db.add(deleted)
        db.delete(item)
        db.commit()
    return RedirectResponse("/inventory", status_code=303)

@app.post("/inventory/delete")
def delete_inventory(ids: DeleteIds, user: User = Depends(require_login), db: Session = Depends(get_db)):
    items = db.query(HardwareInventory).filter(HardwareInventory.id.in_(ids.ids)).all()
    for item in items:
        deleted = DeletedHardwareInventory(
            id=item.id,
            demirbas_adi=item.demirbas_adi,
            marka=item.marka,
            model=item.model,
            seri_no=item.seri_no,
            lokasyon=item.lokasyon,
            zimmetli_kisi=item.zimmetli_kisi,
            notlar=item.notlar,
            deleted_at=date.today(),
        )
        db.add(deleted)
        db.delete(item)
    db.commit()
    return {"message": "deleted"}

@app.get("/trash", response_class=HTMLResponse)
def trash(request: Request, user: User = Depends(require_login), db: Session = Depends(get_db)):
    cleanup_deleted(db)
    hardware = db.query(DeletedHardwareInventory).all()
    printers = db.query(DeletedPrinterInventory).all()
    licenses = db.query(DeletedLicenseInventory).all()
    stocks = db.query(DeletedStockItem).all()
    return templates.TemplateResponse(
        "trash.html",
        {
            "request": request,
            "hardware": hardware,
            "printers": printers,
            "licenses": licenses,
            "stocks": stocks,
            "today": date.today(),
        },
    )

@app.get("/inventory/trash")
def inventory_trash_redirect():
    return RedirectResponse("/trash", status_code=307)

@app.post("/inventory/restore/{item_id}")
def restore_inventory(item_id: int, user: User = Depends(require_login), db: Session = Depends(get_db)):
    item = db.query(DeletedHardwareInventory).filter(DeletedHardwareInventory.id == item_id).first()
    if item:
        restored = HardwareInventory(
            id=item.id,
            demirbas_adi=item.demirbas_adi,
            marka=item.marka,
            model=item.model,
            seri_no=item.seri_no,
            lokasyon=item.lokasyon,
            zimmetli_kisi=item.zimmetli_kisi,
            notlar=item.notlar,
        )
        db.add(restored)
        db.delete(item)
        db.commit()
    return RedirectResponse("/trash", status_code=303)


@app.post("/inventory/upload")
async def upload_inventory_excel(
    excel_file: UploadFile = File(...),
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if not excel_file.filename.lower().endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="Sadece Excel dosyaları yüklenebilir.")
    contents = await excel_file.read()
    try:
        if excel_file.filename.lower().endswith(".xls"):
            sheets = pd.read_excel(BytesIO(contents), sheet_name=None, engine="xlrd")
        else:
            sheets = pd.read_excel(BytesIO(contents), sheet_name=None, engine="openpyxl")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Excel dosyası okunamadı. Hata: {str(e)}")

    for df in sheets.values():
        df.columns = df.columns.str.strip()
        df = df.rename(
            columns={
                "Demirbaş Adı": "demirbas_adi",
                "Marka": "marka",
                "Model": "model",
                "Seri No": "seri_no",
                "Lokasyon": "lokasyon",
                "Zimmetli Kişi": "zimmetli_kisi",
                "Notlar": "notlar",
            }
        )
        expected_cols = [
            "demirbas_adi",
            "marka",
            "model",
            "seri_no",
            "lokasyon",
            "zimmetli_kisi",
            "notlar",
        ]
        eksik_kolonlar = [col for col in expected_cols if col not in df.columns]
        if eksik_kolonlar:
            raise HTTPException(
                status_code=400,
                detail=f"Excel başlıkları eksik veya yanlış: {eksik_kolonlar}",
            )
        df = df[expected_cols]

        for _, row in df.iterrows():
            item = HardwareInventory(
                demirbas_adi=str(row["demirbas_adi"]),
                marka=str(row["marka"]),
                model=str(row["model"]),
                seri_no=str(row["seri_no"]),
                lokasyon=str(row["lokasyon"]),
                zimmetli_kisi=str(row["zimmetli_kisi"]),
                notlar=None if pd.isnull(row["notlar"]) else str(row["notlar"]),
            )
            db.add(item)
    db.commit()

    return {"detail": "ok"}


@app.get("/inventory/export")
def export_inventory_excel(
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    items = db.query(HardwareInventory).all()
    data = [
        {
            "Demirbaş Adı": i.demirbas_adi,
            "Marka": i.marka,
            "Model": i.model,
            "Seri No": i.seri_no,
            "Lokasyon": i.lokasyon,
            "Zimmetli Kişi": i.zimmetli_kisi,
            "Notlar": i.notlar,
        }
        for i in items
    ]
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    headers = {
        "Content-Disposition": "attachment; filename=hardware_inventory.xlsx"
    }
    return StreamingResponse(
        output,
        media_type=
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@app.get("/license", response_class=HTMLResponse)
def license_page(
    request: Request,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Lisans envanterini listeleyen sayfa."""
    licenses = db.query(LicenseInventory).limit(50).all()
    table_name = LicenseInventory.__tablename__
    columns = get_table_columns(table_name)
    settings = get_user_settings(user.username, table_name)
    order = settings.get("order", columns)
    visible = settings.get("visible", columns)
    widths = settings.get("widths", {})
    display_columns = [c for c in order if c in visible]
    softwares = db.query(LookupItem).filter(LookupItem.type == "yazilim").all()
    return templates.TemplateResponse(
        "lisans.html",
        {
            "request": request,
            "licenses": licenses,
            "count": len(licenses),
            "columns": display_columns,
            "table_name": table_name,
            "column_widths": widths,
            "softwares": softwares,
        },
    )


@app.post("/license/add")
def add_license_form(
    license_id: Optional[int] = Form(None),
    yazilim_adi: str = Form(...),
    lisans_anahtari: str = Form(...),
    adet: int = Form(...),
    satin_alma_tarihi: Optional[str] = Form(None),
    bitis_tarihi: Optional[str] = Form(None),
    zimmetli_kisi: str = Form(...),
    notlar: str = Form(""),
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if license_id:
        item = db.query(LicenseInventory).get(license_id)
        if not item:
            raise HTTPException(status_code=404, detail="Kayıt bulunamadı")
        item.yazilim_adi = yazilim_adi
        item.lisans_anahtari = lisans_anahtari
        item.adet = adet
        item.satin_alma_tarihi = (
            date.fromisoformat(satin_alma_tarihi) if satin_alma_tarihi else None
        )
        item.bitis_tarihi = (
            date.fromisoformat(bitis_tarihi) if bitis_tarihi else None
        )
        item.zimmetli_kisi = zimmetli_kisi
        item.notlar = notlar
    else:
        db_item = LicenseInventory(
            yazilim_adi=yazilim_adi,
            lisans_anahtari=lisans_anahtari,
            adet=adet,
            satin_alma_tarihi=
                date.fromisoformat(satin_alma_tarihi) if satin_alma_tarihi else None,
            bitis_tarihi=date.fromisoformat(bitis_tarihi) if bitis_tarihi else None,
            zimmetli_kisi=zimmetli_kisi,
            notlar=notlar,
        )
        db.add(db_item)
    db.commit()
    return RedirectResponse("/license", status_code=303)


@app.post("/license/delete/{license_id}")
def delete_license_form(
    license_id: int,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    lic = (
        db.query(LicenseInventory)
        .filter(LicenseInventory.id == license_id)
        .first()
    )
    if lic:
        deleted = DeletedLicenseInventory(
            id=lic.id,
            yazilim_adi=lic.yazilim_adi,
            lisans_anahtari=lic.lisans_anahtari,
            adet=lic.adet,
            satin_alma_tarihi=lic.satin_alma_tarihi,
            bitis_tarihi=lic.bitis_tarihi,
            zimmetli_kisi=lic.zimmetli_kisi,
            notlar=lic.notlar,
            deleted_at=date.today(),
        )
        db.add(deleted)
        db.delete(lic)
        db.commit()
    return RedirectResponse("/license", status_code=303)


@app.post("/license/delete")
def delete_license(
    ids: DeleteIds,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    items = (
        db.query(LicenseInventory)
        .filter(LicenseInventory.id.in_(ids.ids))
        .all()
    )
    for lic in items:
        deleted = DeletedLicenseInventory(
            id=lic.id,
            yazilim_adi=lic.yazilim_adi,
            lisans_anahtari=lic.lisans_anahtari,
            adet=lic.adet,
            satin_alma_tarihi=lic.satin_alma_tarihi,
            bitis_tarihi=lic.bitis_tarihi,
            zimmetli_kisi=lic.zimmetli_kisi,
            notlar=lic.notlar,
            deleted_at=date.today(),
        )
        db.add(deleted)
        db.delete(lic)
    db.commit()
    return {"message": "deleted"}


@app.post("/license/restore/{item_id}")
def restore_license(
    item_id: int,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    item = (
        db.query(DeletedLicenseInventory)
        .filter(DeletedLicenseInventory.id == item_id)
        .first()
    )
    if item:
        restored = LicenseInventory(
            id=item.id,
            yazilim_adi=item.yazilim_adi,
            lisans_anahtari=item.lisans_anahtari,
            adet=item.adet,
            satin_alma_tarihi=item.satin_alma_tarihi,
            bitis_tarihi=item.bitis_tarihi,
            zimmetli_kisi=item.zimmetli_kisi,
            notlar=item.notlar,
        )
        db.add(restored)
        db.delete(item)
        db.commit()
    return RedirectResponse("/trash", status_code=303)


@app.post("/license/upload")
async def upload_license_excel(
    excel_file: UploadFile = File(...),
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if not excel_file.filename.lower().endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="Sadece Excel dosyaları yüklenebilir.")
    contents = await excel_file.read()
    try:
        if excel_file.filename.lower().endswith(".xls"):
            sheets = pd.read_excel(BytesIO(contents), sheet_name=None, engine="xlrd")
        else:
            sheets = pd.read_excel(BytesIO(contents), sheet_name=None, engine="openpyxl")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Excel dosyası okunamadı. Hata: {str(e)}")

    for df in sheets.values():
        df.columns = df.columns.str.strip()
        df = df.rename(
            columns={
                "Yazılım Adı": "yazilim_adi",
                "Lisans Anahtarı": "lisans_anahtari",
                "Adet": "adet",
                "Satın Alma Tarihi": "satin_alma_tarihi",
                "Bitiş Tarihi": "bitis_tarihi",
                "Zimmetli Kişi": "zimmetli_kisi",
                "Notlar": "notlar",
            }
        )
        expected_cols = [
            "yazilim_adi",
            "lisans_anahtari",
            "adet",
            "satin_alma_tarihi",
            "bitis_tarihi",
            "zimmetli_kisi",
            "notlar",
        ]
        eksik_kolonlar = [col for col in expected_cols if col not in df.columns]
        if eksik_kolonlar:
            raise HTTPException(
                status_code=400,
                detail=f"Excel başlıkları eksik veya yanlış: {eksik_kolonlar}",
            )
        df = df[expected_cols]

        for _, row in df.iterrows():
            lic = LicenseInventory(
                yazilim_adi=str(row["yazilim_adi"]),
                lisans_anahtari=str(row["lisans_anahtari"]),
                adet=int(row["adet"]),
                satin_alma_tarihi=
                    pd.to_datetime(row["satin_alma_tarihi"]).date()
                    if not pd.isnull(row["satin_alma_tarihi"])
                    else None,
                bitis_tarihi=
                    pd.to_datetime(row["bitis_tarihi"]).date()
                    if not pd.isnull(row["bitis_tarihi"])
                    else None,
                zimmetli_kisi=str(row["zimmetli_kisi"]),
                notlar=None if pd.isnull(row["notlar"]) else str(row["notlar"]),
            )
            db.add(lic)
    db.commit()

    return {"detail": "ok"}


@app.get("/license/export")
def export_license_excel(
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    items = db.query(LicenseInventory).all()
    data = [
        {
            "Yazılım Adı": i.yazilim_adi,
            "Lisans Anahtarı": i.lisans_anahtari,
            "Adet": i.adet,
            "Satın Alma Tarihi": i.satin_alma_tarihi.isoformat() if i.satin_alma_tarihi else None,
            "Bitiş Tarihi": i.bitis_tarihi.isoformat() if i.bitis_tarihi else None,
            "Zimmetli Kişi": i.zimmetli_kisi,
            "Notlar": i.notlar,
        }
        for i in items
    ]
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    headers = {
        "Content-Disposition": "attachment; filename=license_inventory.xlsx"
    }
    return StreamingResponse(
        output,
        media_type=
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@app.get("/stock", response_class=HTMLResponse)
def stock_page(
    request: Request,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Stok kayıtlarını listeleyen sayfa."""
    stocks = db.query(StockItem).limit(50).all()
    table_name = StockItem.__tablename__
    columns = get_table_columns(table_name)
    settings = get_user_settings(user.username, table_name)
    order = settings.get("order", columns)
    visible = settings.get("visible", columns)
    widths = settings.get("widths", {})
    display_columns = [c for c in order if c in visible]
    brands = db.query(LookupItem).filter(LookupItem.type == "marka").all()
    locations = db.query(LookupItem).filter(LookupItem.type == "lokasyon").all()
    categories = db.query(LookupItem).filter(LookupItem.type == "kategori").all()
    return templates.TemplateResponse(
        "stok.html",
        {
            "request": request,
            "stocks": stocks,
            "count": len(stocks),
            "columns": display_columns,
            "table_name": table_name,
            "column_widths": widths,
            "brands": brands,
            "locations": locations,
            "categories": categories,
        },
    )


@app.post("/stock/add")
def add_stock_form(
    stock_id: Optional[int] = Form(None),
    urun_adi: str = Form(...),
    kategori: str = Form(...),
    marka: str = Form(...),
    adet: int = Form(...),
    lokasyon: str = Form(...),
    guncelleme_tarihi: Optional[str] = Form(None),
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if stock_id:
        item = db.query(StockItem).get(stock_id)
        if not item:
            raise HTTPException(status_code=404, detail="Kayıt bulunamadı")
        item.urun_adi = urun_adi
        item.kategori = kategori
        item.marka = marka
        item.adet = adet
        item.lokasyon = lokasyon
        item.guncelleme_tarihi = (
            date.fromisoformat(guncelleme_tarihi) if guncelleme_tarihi else None
        )
    else:
        db_item = StockItem(
            urun_adi=urun_adi,
            kategori=kategori,
            marka=marka,
            adet=adet,
            lokasyon=lokasyon,
            guncelleme_tarihi=
                date.fromisoformat(guncelleme_tarihi) if guncelleme_tarihi else None,
        )
        db.add(db_item)
    db.commit()
    return RedirectResponse("/stock", status_code=303)


@app.post("/stock/delete/{stock_id}")
def delete_stock_form(
    stock_id: int,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    st = db.query(StockItem).filter(StockItem.id == stock_id).first()
    if st:
        deleted = DeletedStockItem(
            id=st.id,
            urun_adi=st.urun_adi,
            kategori=st.kategori,
            marka=st.marka,
            adet=st.adet,
            lokasyon=st.lokasyon,
            guncelleme_tarihi=st.guncelleme_tarihi,
            deleted_at=date.today(),
        )
        db.add(deleted)
        db.delete(st)
        db.commit()
    return RedirectResponse("/stock", status_code=303)


@app.post("/stock/delete")
def delete_stock(
    ids: DeleteIds,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    items = db.query(StockItem).filter(StockItem.id.in_(ids.ids)).all()
    for st in items:
        deleted = DeletedStockItem(
            id=st.id,
            urun_adi=st.urun_adi,
            kategori=st.kategori,
            marka=st.marka,
            adet=st.adet,
            lokasyon=st.lokasyon,
            guncelleme_tarihi=st.guncelleme_tarihi,
            deleted_at=date.today(),
        )
        db.add(deleted)
        db.delete(st)
    db.commit()
    return {"message": "deleted"}


@app.post("/stock/restore/{item_id}")
def restore_stock(
    item_id: int,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    item = (
        db.query(DeletedStockItem)
        .filter(DeletedStockItem.id == item_id)
        .first()
    )
    if item:
        restored = StockItem(
            id=item.id,
            urun_adi=item.urun_adi,
            kategori=item.kategori,
            marka=item.marka,
            adet=item.adet,
            lokasyon=item.lokasyon,
            guncelleme_tarihi=item.guncelleme_tarihi,
        )
        db.add(restored)
        db.delete(item)
        db.commit()
    return RedirectResponse("/trash", status_code=303)


@app.post("/stock/upload")
async def upload_stock_excel(
    excel_file: UploadFile = File(...),
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if not excel_file.filename.lower().endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="Sadece Excel dosyaları yüklenebilir.")
    contents = await excel_file.read()
    try:
        if excel_file.filename.lower().endswith(".xls"):
            sheets = pd.read_excel(BytesIO(contents), sheet_name=None, engine="xlrd")
        else:
            sheets = pd.read_excel(BytesIO(contents), sheet_name=None, engine="openpyxl")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Excel dosyası okunamadı. Hata: {str(e)}")

    for df in sheets.values():
        df.columns = df.columns.str.strip()
        df = df.rename(
            columns={
                "Ürün Adı": "urun_adi",
                "Kategori": "kategori",
                "Marka": "marka",
                "Adet": "adet",
                "Lokasyon": "lokasyon",
                "Güncelleme Tarihi": "guncelleme_tarihi",
            }
        )
        expected_cols = [
            "urun_adi",
            "kategori",
            "marka",
            "adet",
            "lokasyon",
            "guncelleme_tarihi",
        ]
        eksik_kolonlar = [col for col in expected_cols if col not in df.columns]
        if eksik_kolonlar:
            raise HTTPException(
                status_code=400,
                detail=f"Excel başlıkları eksik veya yanlış: {eksik_kolonlar}",
            )
        df = df[expected_cols]

        for _, row in df.iterrows():
            st = StockItem(
                urun_adi=str(row["urun_adi"]),
                kategori=str(row["kategori"]),
                marka=str(row["marka"]),
                adet=int(row["adet"]),
                lokasyon=str(row["lokasyon"]),
                guncelleme_tarihi=
                    pd.to_datetime(row["guncelleme_tarihi"]).date()
                    if not pd.isnull(row["guncelleme_tarihi"])
                    else None,
            )
            db.add(st)
    db.commit()

    return {"detail": "ok"}


@app.get("/stock/export")
def export_stock_excel(
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    items = db.query(StockItem).all()
    data = [
        {
            "Ürün Adı": i.urun_adi,
            "Kategori": i.kategori,
            "Marka": i.marka,
            "Adet": i.adet,
            "Lokasyon": i.lokasyon,
            "Güncelleme Tarihi": i.guncelleme_tarihi.isoformat() if i.guncelleme_tarihi else None,
        }
        for i in items
    ]
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    headers = {
        "Content-Disposition": "attachment; filename=stock_items.xlsx"
    }
    return StreamingResponse(
        output,
        media_type=
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@app.get("/printer", response_class=HTMLResponse)
def printer_page(
    request: Request,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Yazıcı envanterini listeleyen sayfa."""
    printers = db.query(PrinterInventory).limit(50).all()
    table_name = PrinterInventory.__tablename__
    columns = get_table_columns(table_name)
    settings = get_user_settings(user.username, table_name)
    order = settings.get("order", columns)
    visible = settings.get("visible", columns)
    widths = settings.get("widths", {})
    display_columns = [c for c in order if c in visible]
    brands = db.query(LookupItem).filter(LookupItem.type == "marka").all()
    locations = db.query(LookupItem).filter(LookupItem.type == "lokasyon").all()
    return templates.TemplateResponse(
        "yazici.html",
        {
            "request": request,
            "printers": printers,
            "count": len(printers),
            "columns": display_columns,
            "table_name": table_name,
            "column_widths": widths,
            "brands": brands,
            "locations": locations,
        },
    )


@app.post("/printer/add")
def add_printer_form(
    printer_id: Optional[int] = Form(None),
    yazici_markasi: str = Form(...),
    yazici_modeli: str = Form(...),
    kullanim_alani: str = Form(...),
    ip_adresi: str = Form(...),
    mac: str = Form(...),
    hostname: str = Form(...),
    notlar: str = Form(""),
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Formdan gelen verilerle yeni yazıcı kaydı oluşturur."""
    if printer_id:
        item = db.query(PrinterInventory).get(printer_id)
        if not item:
            raise HTTPException(status_code=404, detail="Kayıt bulunamadı")
        item.yazici_markasi = yazici_markasi
        item.yazici_modeli = yazici_modeli
        item.kullanim_alani = kullanim_alani
        item.ip_adresi = ip_adresi
        item.mac = mac
        item.hostname = hostname
        item.notlar = notlar
    else:
        db_item = PrinterInventory(
            yazici_markasi=yazici_markasi,
            yazici_modeli=yazici_modeli,
            kullanim_alani=kullanim_alani,
            ip_adresi=ip_adresi,
            mac=mac,
            hostname=hostname,
            notlar=notlar,
        )
        db.add(db_item)
    db.commit()
    return RedirectResponse("/printer", status_code=303)


@app.post("/printer/delete/{printer_id}")
def delete_printer_form(
    printer_id: int,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Seçilen yazıcı kaydını siler."""
    printer = (
        db.query(PrinterInventory)
        .filter(PrinterInventory.id == printer_id)
        .first()
    )
    if printer:
        deleted = DeletedPrinterInventory(
            id=printer.id,
            yazici_markasi=printer.yazici_markasi,
            yazici_modeli=printer.yazici_modeli,
            kullanim_alani=printer.kullanim_alani,
            ip_adresi=printer.ip_adresi,
            mac=printer.mac,
            hostname=printer.hostname,
            notlar=printer.notlar,
            deleted_at=date.today(),
        )
        db.add(deleted)
        db.delete(printer)
        db.commit()
    return RedirectResponse("/printer", status_code=303)


@app.post("/printer/delete")
def delete_printer(
    ids: DeleteIds,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    items = (
        db.query(PrinterInventory)
        .filter(PrinterInventory.id.in_(ids.ids))
        .all()
    )
    for printer in items:
        deleted = DeletedPrinterInventory(
            id=printer.id,
            yazici_markasi=printer.yazici_markasi,
            yazici_modeli=printer.yazici_modeli,
            kullanim_alani=printer.kullanim_alani,
            ip_adresi=printer.ip_adresi,
            mac=printer.mac,
            hostname=printer.hostname,
            notlar=printer.notlar,
            deleted_at=date.today(),
        )
        db.add(deleted)
        db.delete(printer)
    db.commit()
    return {"message": "deleted"}


@app.post("/printer/restore/{item_id}")
def restore_printer(
    item_id: int,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    item = (
        db.query(DeletedPrinterInventory)
        .filter(DeletedPrinterInventory.id == item_id)
        .first()
    )
    if item:
        restored = PrinterInventory(
            id=item.id,
            yazici_markasi=item.yazici_markasi,
            yazici_modeli=item.yazici_modeli,
            kullanim_alani=item.kullanim_alani,
            ip_adresi=item.ip_adresi,
            mac=item.mac,
            hostname=item.hostname,
            notlar=item.notlar,
        )
        db.add(restored)
        db.delete(item)
        db.commit()
    return RedirectResponse("/trash", status_code=303)


@app.post("/printer/upload")
async def upload_printer_excel(
    excel_file: UploadFile = File(...),
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    # Dosya uzantısını küçük harfe çevirerek Excel dosyası kontrolünü
    # büyük/küçük harf duyarlılığından bağımsız hale getir
    if not excel_file.filename.lower().endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="Sadece Excel dosyaları yüklenebilir.")
    contents = await excel_file.read()
    try:
        if excel_file.filename.lower().endswith(".xls"):
            sheets = pd.read_excel(BytesIO(contents), sheet_name=None, engine="xlrd")
        else:
            sheets = pd.read_excel(BytesIO(contents), sheet_name=None, engine="openpyxl")
    except Exception as e:
    # Detaylı hata mesajı için
            raise HTTPException(status_code=400, detail=f"Excel dosyası okunamadı. Hata: {str(e)}")

    for df in sheets.values():
        df.columns = df.columns.str.strip()
        df = df.rename(
            columns={
                "Yazıcı Markası": "yazici_markasi",
                "Yazıcı Modeli": "yazici_modeli",
                "Kullanım alanı": "kullanim_alani",
                "İp Adresi": "ip_adresi",
                "Mac": "mac",
                "Hostname": "hostname",
                "not": "notlar",
            }
        )
        expected_cols = [
            "yazici_markasi", "yazici_modeli", "kullanim_alani", "ip_adresi", "mac", "hostname", "notlar"
        ]
        eksik_kolonlar = [col for col in expected_cols if col not in df.columns]
        if eksik_kolonlar:
            raise HTTPException(status_code=400, detail=f"Excel başlıkları eksik veya yanlış: {eksik_kolonlar}")
        df = df[expected_cols]

        for _, row in df.iterrows():
            printer = PrinterInventory(
                yazici_markasi=str(row["yazici_markasi"]),
                yazici_modeli=str(row["yazici_modeli"]),
                kullanim_alani=str(row["kullanim_alani"]),
                ip_adresi=str(row["ip_adresi"]),
                mac=str(row["mac"]),
                hostname=str(row["hostname"]),
                notlar=None if pd.isnull(row["notlar"]) else str(row["notlar"]),
            )
            db.add(printer)
    db.commit()

    return {"detail": "ok"}


@app.get("/printer/export")
def export_printer_excel(
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    items = db.query(PrinterInventory).all()
    data = [
        {
            "Yazıcı Markası": i.yazici_markasi,
            "Yazıcı Modeli": i.yazici_modeli,
            "Kullanım alanı": i.kullanim_alani,
            "İp Adresi": i.ip_adresi,
            "Mac": i.mac,
            "Hostname": i.hostname,
            "Notlar": i.notlar,
        }
        for i in items
    ]
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    headers = {
        "Content-Disposition": "attachment; filename=printer_inventory.xlsx"
    }
    return StreamingResponse(
        output,
        media_type=
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


# --- Donanım ---
@app.get("/hardware", response_model=List[HardwareItem])
def get_hardware(
    user: User = Depends(require_login), db: Session = Depends(get_db)
):
    return db.query(HardwareInventory).all()

@app.post("/hardware", response_model=HardwareItem)
def add_hardware(
    item: HardwareItem,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    db_item = HardwareInventory(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


# --- DB Şema Yönetimi ---
@app.post("/db/add-column")
def add_column(
    table_name: str = Form(...),
    column_name: str = Form(...),
    column_type: str = Form(...),
    user: User = Depends(require_login),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Yetkisiz")
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                )
            )
        return {"message": "Kolon eklendi"}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/db/remove-column")
def remove_column(
    table_name: str = Form(...),
    column_name: str = Form(...),
    user: User = Depends(require_login),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Yetkisiz")
    with engine.connect() as conn:
        count = conn.execute(
            text(
                f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} IS NOT NULL AND TRIM({column_name}) != ''"
            )
        ).scalar()
        if count and count > 0:
            raise HTTPException(
                status_code=400,
                detail="Kolon verisi içeriyor, silinemez",
            )
        try:
            conn.execute(text(f"ALTER TABLE {table_name} DROP COLUMN {column_name}"))
        except SQLAlchemyError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    return {"message": "Kolon silindi"}

@app.post("/db/create-table")
def create_table(
    schema: CreateTableSchema, user: User = Depends(require_login)
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Yetkisiz")
    if not schema.columns:
        raise HTTPException(status_code=400, detail="Kolon listesi boş olamaz")
    columns_def = ", ".join(f"{col.name} {col.type}" for col in schema.columns)
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    f"CREATE TABLE IF NOT EXISTS {schema.table_name} ({columns_def})"
                )
            )
        return {"message": "Tablo oluşturuldu"}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/table-columns")
def table_columns(
    table_name: str,
    user: User = Depends(require_login),
):
    return {"columns": get_table_columns(table_name)}


@app.get("/column-settings")
def column_settings_get(
    table_name: str,
    user: User = Depends(require_login),
):
    return get_user_settings(user.username, table_name)


@app.post("/column-settings")
def column_settings_post(
    table_name: str,
    settings: ColumnSettings,
    user: User = Depends(require_login),
):
    set_user_settings(user.username, table_name, settings.dict())
    return {"message": "kaydedildi"}

# --- Yazıcı ---
@app.get("/printers", response_model=List[PrinterItem])
def get_printers(
    user: User = Depends(require_login), db: Session = Depends(get_db)
):
    return db.query(PrinterInventory).all()

@app.post("/printers", response_model=PrinterItem)
def add_printer(
    item: PrinterItem,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    db_item = PrinterInventory(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

# --- Lisans ---
@app.get("/licenses", response_model=List[LicenseItem])
def get_licenses(
    user: User = Depends(require_login), db: Session = Depends(get_db)
):
    return db.query(LicenseInventory).all()

@app.post("/licenses", response_model=LicenseItem)
def add_license(
    item: LicenseItem,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    db_item = LicenseInventory(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

# --- Stok ---
@app.get("/stock_items", response_model=List[StockItemSchema])
def get_stock(
    user: User = Depends(require_login), db: Session = Depends(get_db)
):
    return db.query(StockItem).all()

@app.post("/stock_items", response_model=StockItemSchema)
def add_stock(
    item: StockItemSchema,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    db_item = StockItem(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

