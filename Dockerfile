FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema requeridas para utilidades y healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar aplicación, assets y utilidades
COPY backend/ ./backend/
COPY 01_schema.sql 02_seed.sql init_db.py run.py ./

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

HEALTHCHECK --interval=20s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
