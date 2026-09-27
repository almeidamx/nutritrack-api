# API NutriTrack — Flask + gunicorn
FROM python:3.11-slim

# Nao gerar .pyc e log sem buffer (aparece na hora no docker logs).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/nutritrack.db

WORKDIR /app

# Dependencias primeiro (cache de layer).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Codigo da aplicacao.
COPY . .

# O SQLite vive em /data, montado como volume nomeado pelo compose.
RUN mkdir -p /data

EXPOSE 5000

# 2 workers e suficiente para o MVP; timeout folgado para chamadas a OFF.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "30", "wsgi:app"]
