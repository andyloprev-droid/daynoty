# Multi-stage build para optimizar imagen
FROM python:3.10-slim as builder

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --user --no-cache-dir -r requirements.txt

# ============ Imagen final ============
FROM python:3.10-slim

# Instalar dependencias de runtime
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar Python packages desde builder
COPY --from=builder /root/.local /root/.local

# Configurar PATH
ENV PATH=/root/.local/bin:$PATH

# Copiar código de la aplicación
COPY . .

# Crear directorio de logs
RUN mkdir -p logs

# Variable de entorno para Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Comando por defecto: ejecutar agente programado
CMD ["python", "main.py", "--schedule"]
