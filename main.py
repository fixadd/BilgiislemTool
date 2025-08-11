# main.py
# FastAPI + SQLAlchemy + Docker uyumlu envanter sistemi backend yapisi

from fastapi import FastAPI, Depends, Request, Form, HTTPException, status, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from io import BytesIO
import pandas as pd
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from sqlalchemy import create_engine, Column, Integer, String, Date, Text, Boolean, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os

# --- DATABASE AYARI (Docker icin degisebilir) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.getenv("DB_FILE", os.path.join(BASE_DIR, "data", "envanter.db"))
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


def init_db():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    if not os.path.exists(DB_FILE):
        open(DB_FILE, "w").close()
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


init_db()
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

# --- FastAPI Uygulaması ---
app = FastAPI()
app.mount("/image", StaticFiles(directory="image"), name="image")
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
def inventory_page(
    request: Request,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Donanım envanterini listeleyen sayfa."""
    items = db.query(HardwareInventory).all()
    return templates.TemplateResponse(
        "envanter.html", {"request": request, "items": items}
    )


@app.post("/inventory/add")
def add_inventory_form(
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
        db.delete(item)
        db.commit()
    return RedirectResponse("/inventory", status_code=303)


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

    return RedirectResponse("/inventory", status_code=303)


@app.get("/license", response_class=HTMLResponse)
def license_page(
    request: Request,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Lisans envanterini listeleyen sayfa."""
    licenses = db.query(LicenseInventory).all()
    return templates.TemplateResponse(
        "lisans.html", {"request": request, "licenses": licenses}
    )


@app.post("/license/add")
def add_license_form(
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
        db.delete(lic)
        db.commit()
    return RedirectResponse("/license", status_code=303)


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

    return RedirectResponse("/license", status_code=303)


@app.get("/stock", response_class=HTMLResponse)
def stock_page(
    request: Request,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Stok kayıtlarını listeleyen sayfa."""
    stocks = db.query(StockItem).all()
    return templates.TemplateResponse(
        "stok.html", {"request": request, "stocks": stocks}
    )


@app.post("/stock/add")
def add_stock_form(
    urun_adi: str = Form(...),
    kategori: str = Form(...),
    marka: str = Form(...),
    adet: int = Form(...),
    lokasyon: str = Form(...),
    guncelleme_tarihi: Optional[str] = Form(None),
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
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
        db.delete(st)
        db.commit()
    return RedirectResponse("/stock", status_code=303)


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

    return RedirectResponse("/stock", status_code=303)


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

