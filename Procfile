web: python manage.py migrate && python manage.py collectstatic --noinput -v 2 && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}
