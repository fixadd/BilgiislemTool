# main.py
# FastAPI + SQLAlchemy + Docker uyumlu envanter sistemi backend yapisi

from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from sqlalchemy import create_engine, Column, Integer, String, Date, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from starlette.middleware.sessions import SessionMiddleware
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

Base.metadata.create_all(bind=engine)

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
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")
templates = Jinja2Templates(directory="templates")

# --- Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Authentication ve Ana Sayfa ---
@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "password":
        request.session["user"] = username
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Geçersiz kullanıcı adı veya şifre"},
        status_code=401,
    )


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    hardware_items = db.query(HardwareInventory).all()
    return templates.TemplateResponse(
        "home.html", {"request": request, "user": user, "hardware": hardware_items}
    )

# --- Donanım ---
@app.get("/hardware", response_model=List[HardwareItem])
def get_hardware(db: Session = Depends(get_db)):
    return db.query(HardwareInventory).all()

@app.post("/hardware", response_model=HardwareItem)
def add_hardware(item: HardwareItem, db: Session = Depends(get_db)):
    db_item = HardwareInventory(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

# --- Yazıcı ---
@app.get("/printers", response_model=List[PrinterItem])
def get_printers(db: Session = Depends(get_db)):
    return db.query(PrinterInventory).all()

@app.post("/printers", response_model=PrinterItem)
def add_printer(item: PrinterItem, db: Session = Depends(get_db)):
    db_item = PrinterInventory(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

# --- Lisans ---
@app.get("/licenses", response_model=List[LicenseItem])
def get_licenses(db: Session = Depends(get_db)):
    return db.query(LicenseInventory).all()

@app.post("/licenses", response_model=LicenseItem)
def add_license(item: LicenseItem, db: Session = Depends(get_db)):
    db_item = LicenseInventory(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

# --- Stok ---
@app.get("/stock", response_model=List[StockItemSchema])
def get_stock(db: Session = Depends(get_db)):
    return db.query(StockItem).all()

@app.post("/stock", response_model=StockItemSchema)
def add_stock(item: StockItemSchema, db: Session = Depends(get_db)):
    db_item = StockItem(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

