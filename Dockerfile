# ── Etapa 1: builder ─────────────────────────────────────────────────────────
FROM python:3.12.9-slim-bookworm AS builder

WORKDIR /build

# Dependencias del sistema para compilar paquetes nativos (arch, scipy, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev libssl-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar solo requirements para aprovechar cache de capas
COPY backend/requirements.txt .

# Instalar en directorio local para copiar en etapa final
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Etapa 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.12.9-slim-bookworm AS runtime

WORKDIR /app

# Dependencias mínimas de runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copiar paquetes instalados desde builder
COPY --from=builder /install /usr/local

# Copiar código del backend
COPY backend/ .

# Directorio para SQLite persistente
RUN mkdir -p /app/data/cache

# Usuario no-root por seguridad
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

# Variables de entorno por defecto (se sobreescriben en Render/Railway)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

EXPOSE 8000

# Health check para que Render detecte arranque correcto
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/ || exit 1

# Comando de arranque con hot-reload desactivado en producción
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
