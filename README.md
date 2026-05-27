
# Breathe ESG Prototype

Deployable ESG ingestion and review prototype built with Django and React.


https://github.com/user-attachments/assets/5f00314b-7e7b-4c6f-afbc-1eefc4f875d3



## Stack

- Django + Django REST Framework
- React + Vite
- PostgreSQL in production, SQLite fallback locally
- WhiteNoise for static files
- Railway and Render deployment support

## What It Does

- Ingests three source types:
  - utility CSV
  - travel JSON
  - SAP CSV
- Stores raw source rows in source-specific tables
- Normalizes them into a unified `ActivityData` model
- Scopes all records by integer `tenant_id`
- Supports analyst review, approval, scope override, raw row inspection, and retry for failed rows

## Repo Layout

- `breathe_esg/backend/` Django project
- `breathe_esg/frontend/` React app
- `breathe_esg/sample_data/` sample upload files
- `breathe_esg/DEPLOY.md` deployment guide
- `nixpacks.toml` repo-root Railway build/start config
- `Procfile` repo-root process entry

## Main API Endpoints

- `POST /api/upload/utility/`
- `POST /api/upload/travel/`
- `POST /api/upload/sap/`
- `GET /api/activities/`
- `PATCH /api/activities/<id>/`
- `POST /api/activities/<id>/approve/`
- `GET /api/activities/<id>/raw/`
- `GET /api/health/`

Use:

- `X-Tenant-Id: 1`
- optional `X-Analyst-Name: Primary Analyst`

## Local Run

From `breathe_esg/`:

```bash
pip install -r backend/requirements.txt
cd frontend
npm install
npm run build
cd ../backend
python manage.py migrate
python manage.py runserver
```

Open:

- `https://pm-production-b183.up.railway.app/`

## Railway

If Railway deploys from repo root, it uses the repo-root `nixpacks.toml` and `Procfile`.

Required environment variables:

- `DJANGO_SETTINGS_MODULE=config.settings.production`
- `SECRET_KEY=<strong-random-value>`
- `DEBUG=false`
- `ALLOWED_HOSTS=<your-railway-domain>`
- `DATABASE_URL=<railway-postgres-url>`

If Railway `Root Directory` is set manually, set it to:

- `breathe_esg`

Then make sure the `breathe_esg/nixpacks.toml` and `breathe_esg/Procfile` are used.

## Sample Files

- `breathe_esg/sample_data/utility_sample.csv`
- `breathe_esg/sample_data/travel_sample.json`

Upload your SAP CSV separately using the required columns:

- `MATNR, MAKTX, MENGE, MEINS, WERKS, BSART, ERDAT`

## Testing

From `breathe_esg/backend/`:

```bash
python manage.py check
python manage.py test apps.prototype.tests
```

From `breathe_esg/frontend/`:

```bash
npm ci
npm run build
```

## Notes

- Utility datetime parsing accepts common CSV formats, including ISO, space-separated timestamps, and US-style dates such as `03/01/2025 00:00`.
- Failed rows remain reviewable and can be retried after parser or data fixes.
- Upload processing is synchronous; no workers are required.
