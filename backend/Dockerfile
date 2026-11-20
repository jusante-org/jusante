FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# GDAL, GEOS e PROJ são necessários para o GeoDjango.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gdal-bin libgdal-dev binutils libproj-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir "django>=5.2,<5.3" "psycopg[binary]>=3.2" gunicorn

COPY . .

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000"]
