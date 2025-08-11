FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Statik veritabanını imajın içine göm
#COPY data/envanter.db ./data/envanter.db

# Uvicorn ile FastAPI uygulamasini baslat
# Allow the port to be overridden at runtime via the PORT environment variable.
# Defaults to 5000 if PORT is not set.
CMD ["bash", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-5000}"]
