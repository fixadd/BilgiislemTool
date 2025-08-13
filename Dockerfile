FROM python:3.11

WORKDIR /app

COPY requirements.txt .
# Install pinned dependencies and verify integrity
RUN pip install --no-cache-dir -r requirements.txt \
    && pip check

COPY . .

# Uvicorn ile FastAPI uygulamasini baslat
# Allow the port to be overridden at runtime via the PORT environment variable.
# Defaults to 5000 if PORT is not set.
CMD ["bash", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-5000}"]
