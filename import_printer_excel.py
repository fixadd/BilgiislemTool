import os
import sqlite3
import pandas as pd

# Veritabanının ve Excel dosyasının yollarını tanımlar
DB_PATH = os.path.join("data", "envanter.db")
EXCEL_PATH = "Yazıcı Envanteri.xls"

# SQLite veritabanına bağlanır
conn = sqlite3.connect(DB_PATH)

try:
    # Excel çalışma kitabını (tüm sayfalarla) yükler
    xls = pd.ExcelFile(EXCEL_PATH)

    # Çalışma kitabındaki her sayfa için döngü
    for sheet in xls.sheet_names:
        # Mevcut sayfayı DataFrame olarak okur
        df = xls.parse(sheet)

        # Excel sütun isimlerini veritabanı sütunlarına eşler
        df = df.rename(columns={
            "Yazıcı Adı": "yazici_adi",
            "Marka": "marka",
            "Model": "model",
            "IP Adresi": "ip_adresi",
            "Seri No": "seri_no",
            "Lokasyon": "lokasyon",
            "Zimmetli Kişi": "zimmetli_kisi",
            "Notlar": "notlar",
        })

        # Beklenen sütunları seçer (eksik olanları NaN olarak bırakır)
        expected_cols = [
            "yazici_adi",
            "marka",
            "model",
            "ip_adresi",
            "seri_no",
            "lokasyon",
            "zimmetli_kisi",
            "notlar",
        ]
        df = df[expected_cols]

        # DataFrame içeriğini veritabanındaki printer_inventory tablosuna ekler
        df.to_sql("printer_inventory", conn, if_exists="append", index=False)
finally:
    # Bağlantıyı güvenli bir şekilde kapatır
    conn.close()

# İşlem başarıyla tamamlandığında bilgi mesajı yazar
print("Veriler mevcut veritabanındaki tabloya eklendi!")
