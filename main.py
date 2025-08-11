# main.py
# FastAPI + SQLAlchemy + Docker uyumlu envanter sistemi backend yapisi

from fastapi import FastAPI, Depends, Request, Form, HTTPException, status, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from io import BytesIO
import pandas as pd
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from sqlalchemy import create_engine, Column, Integer, String, Date, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os

# --- DATABASE AYARI (Docker icin degisebilir) ---
DB_FILE = os.getenv("DB_FILE", "./data/envanter.db")
DATABASE_URL = f"sqlite:///{DB_FILE}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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

class PrinterInventory(Base):
    __tablename__ = "printer_inventory"
    id = Column(Integer, primary_key=True, index=True)
    yazici_adi = Column(String)
    marka = Column(String)
    model = Column(String)
    ip_adresi = Column(String)
    seri_no = Column(String)
    lokasyon = Column(String)
    zimmetli_kisi = Column(String)
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

Base.metadata.create_all(bind=engine)


def init_admin():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(username="admin", password="admin", is_admin=True)
            db.add(admin)
            db.commit()
    finally:
        db.close()


init_admin()

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
    yazici_adi: str
    marka: str
    model: str
    ip_adresi: str
    seri_no: str
    lokasyon: str
    zimmetli_kisi: str
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

# --- FastAPI Uygulaması ---
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# --- Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Authentication ---
security = HTTPBasic()

def require_login(
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        User.username == credentials.username,
        User.password == credentials.password,
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kullanıcı adı/şifre",
        )
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
    user = db.query(User).filter(User.username == username, User.password == password).first()
    if user:
        return RedirectResponse(url=f"/home?username={username}", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Hatalı kullanıcı adı veya şifre"})


@app.get("/home", response_class=HTMLResponse)
def home_page(request: Request, username: Optional[str] = None):
    """Ana ekranı döndür, kullanıcı adı yoksa girişe yönlendir."""
    if not username:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("main.html", {"request": request, "username": username})


# --- Takip Sayfaları (HTML) ---
@app.get("/inventory", response_class=HTMLResponse)
def inventory_page(request: Request):
    return templates.TemplateResponse("envanter.html", {"request": request})


@app.get("/license", response_class=HTMLResponse)
def license_page(request: Request):
    return templates.TemplateResponse("lisans.html", {"request": request})


@app.get("/printer", response_class=HTMLResponse)
def printer_page(
    request: Request,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Yazıcı envanterini listeleyen sayfa."""
    printers = db.query(PrinterInventory).all()
    return templates.TemplateResponse(
        "yazici.html", {"request": request, "printers": printers}
    )


@app.post("/printer/add")
def add_printer_form(
    yazici_adi: str = Form(...),
    marka: str = Form(...),
    model: str = Form(...),
    ip_adresi: str = Form(...),
    seri_no: str = Form(...),
    lokasyon: str = Form(...),
    zimmetli_kisi: str = Form(...),
    notlar: str = Form(""),
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Formdan gelen verilerle yeni yazıcı kaydı oluşturur."""
    db_item = PrinterInventory(
        yazici_adi=yazici_adi,
        marka=marka,
        model=model,
        ip_adresi=ip_adresi,
        seri_no=seri_no,
        lokasyon=lokasyon,
        zimmetli_kisi=zimmetli_kisi,
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
        db.delete(printer)
        db.commit()
    return RedirectResponse("/printer", status_code=303)


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
                marka=str(row["yazici_markasi"]),
                yazici_modeli=str(row["yazici_modeli"]),
                kullanim_alani=str(row["kullanim_alani"]),
                ip_adresi=str(row["ip_adresi"]),
                mac=str(row["mac"]),
                hostname=str(row["hostname"]),
                notlar=None if pd.isnull(row["notlar"]) else str(row["notlar"]),
            )
            db.add(printer)
    db.commit()

    return RedirectResponse("/printer", status_code=303)


@app.get("/stock", response_class=HTMLResponse)
def stock_page(request: Request):
    return templates.TemplateResponse("stok.html", {"request": request})

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

