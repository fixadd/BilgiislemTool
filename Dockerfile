FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Statik veritabanını imajın içine göm
COPY data/envanter.db ./data/envanter.db

# Uvicorn ile FastAPI uygulamasini baslat
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
