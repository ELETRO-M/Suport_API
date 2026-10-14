#!/usr/bin/env bash
set -e

echo "==> migrando schema"
python manage.py migrate --noinput

echo "==> coletando estáticos (WhiteNoise)"
python manage.py collectstatic --noinput

echo "==> garantindo admin padrão"
python manage.py criar_admin || true

echo "==> iniciando gunicorn"
exec "$@"
