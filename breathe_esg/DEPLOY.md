# Deploy

## Render

1. Create a PostgreSQL database on Render or Neon.
2. Create a Web Service pointing at this repo.
3. Set:
   - `DJANGO_SETTINGS_MODULE=config.settings.production`
   - `SECRET_KEY=<strong-random-value>`
   - `DEBUG=false`
   - `ALLOWED_HOSTS=<your-render-domain>`
   - `DATABASE_URL=<postgres-connection-string>`
4. Build command:
   - `pip install -r backend/requirements.txt && cd frontend && npm ci && npm run build && cd .. && python backend/manage.py migrate --settings=config.settings.production && python backend/manage.py collectstatic --noinput --settings=config.settings.production`
5. Start command:
   - `cd backend && gunicorn config.wsgi:application`
6. Healthcheck path:
   - `/api/health/`
7. Open the site, upload files from `sample_data/`, and use tenant `1`.

## Railway

1. Create a PostgreSQL service.
2. Create a Python app from this repo.
3. Set:
   - `DJANGO_SETTINGS_MODULE=config.settings.production`
   - `SECRET_KEY=<strong-random-value>`
   - `DEBUG=false`
   - `ALLOWED_HOSTS=<your-railway-domain>`
   - `DATABASE_URL=${{Postgres.DATABASE_URL}}`
4. The repo already includes `railway.json`, `nixpacks.toml`, and `Procfile`, so Railway can pick the commands up automatically.
5. Deploy the service and confirm `/api/health/` returns `{"status":"ok"}`.

## Local run

1. `pip install -r backend/requirements.txt`
2. `cd frontend && npm install && npm run build`
3. `cd ..\\backend && python manage.py migrate`
4. `python manage.py runserver`
5. Visit `http://127.0.0.1:8000/`

## Operate

1. Open the app and keep tenant `1` unless you want a separate isolated dataset.
2. Upload one file at a time from `sample_data/` or your own source files:
   - utility: `sample_data/utility_sample.csv`
   - travel: `sample_data/travel_sample.json`
   - sap: your SAP CSV sample
3. Use the filters to narrow by source, status, or suspicious rows.
4. Click `Raw` to inspect the stored source payload.
5. Change the scope dropdown to override heuristic scope classification.
6. Click `Approve` to mark a row approved and write the audit trail.
7. Click `Retry` on failed rows after correcting the raw source and reuploading or after testing retry behavior.

## Test

1. Backend smoke:
   - `python backend/manage.py check`
   - `python backend/manage.py migrate`
   - `python backend/manage.py test apps.prototype.tests`
2. Frontend build:
   - `cd frontend && npm ci && npm run build`
3. API smoke with curl:
   - `curl -H "X-Tenant-Id: 1" http://127.0.0.1:8000/api/health/`
   - `curl -H "X-Tenant-Id: 1" http://127.0.0.1:8000/api/activities/`
