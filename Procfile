web: cd breathe_esg && python backend/manage.py migrate --settings=config.settings.production && cd backend && python -m gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
