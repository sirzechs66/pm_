# Runbook

## Local Startup

### Backend

From `breathe_esg/backend`:

```bash
python manage.py migrate
python manage.py runserver
```

### Frontend Build

From `breathe_esg/frontend`:

```bash
npm install
npm run build
```

The built assets are written into `backend/static/frontend`.

## Local Use

1. Start Django.
2. Open `http://127.0.0.1:8000/`.
3. Leave tenant as `1` unless you want a separate isolated dataset.
4. Upload:
   - `sample_data/utility_sample.csv`
   - `sample_data/travel_sample.json`
   - your SAP CSV sample
5. Review rows in the dashboard.

## API Usage

All API routes are tenant-scoped through the `X-Tenant-Id` header.

Optional analyst attribution:
- `X-Analyst-Name: Primary Analyst`

### Health Check

```bash
curl -H "X-Tenant-Id: 1" http://127.0.0.1:8000/api/health/
```

### List Activities

```bash
curl -H "X-Tenant-Id: 1" http://127.0.0.1:8000/api/activities/
```

### Filter Activities

```bash
curl -H "X-Tenant-Id: 1" "http://127.0.0.1:8000/api/activities/?source_type=utility&status=pending_review&suspicious_flag=true"
```

### Upload Utility CSV

```bash
curl -X POST http://127.0.0.1:8000/api/upload/utility/ \
  -H "X-Tenant-Id: 1" \
  -H "X-Analyst-Name: Primary Analyst" \
  -F "file=@sample_data/utility_sample.csv"
```

### Upload Travel JSON

```bash
curl -X POST http://127.0.0.1:8000/api/upload/travel/ \
  -H "X-Tenant-Id: 1" \
  -H "X-Analyst-Name: Primary Analyst" \
  -F "file=@sample_data/travel_sample.json"
```

### Upload SAP CSV

```bash
curl -X POST http://127.0.0.1:8000/api/upload/sap/ \
  -H "X-Tenant-Id: 1" \
  -H "X-Analyst-Name: Primary Analyst" \
  -F "file=@sample_data/your_sap.csv"
```

### Approve an Activity

```bash
curl -X POST http://127.0.0.1:8000/api/activities/1/approve/ \
  -H "X-Tenant-Id: 1" \
  -H "X-Analyst-Name: Primary Analyst"
```

### Override Scope

```bash
curl -X PATCH http://127.0.0.1:8000/api/activities/1/ \
  -H "X-Tenant-Id: 1" \
  -H "X-Analyst-Name: Primary Analyst" \
  -H "Content-Type: application/json" \
  -d "{\"scope\":3}"
```

### View Raw Source Row

```bash
curl -H "X-Tenant-Id: 1" http://127.0.0.1:8000/api/activities/1/raw/
```

### Retry a Failed Activity

```bash
curl -X PATCH http://127.0.0.1:8000/api/activities/1/ \
  -H "X-Tenant-Id: 1" \
  -H "X-Analyst-Name: Primary Analyst" \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"retry\"}"
```

## Validation Workflow

Recommended smoke test:

1. `python manage.py check`
2. `python manage.py migrate`
3. `python manage.py test apps.prototype.tests`
4. `cd frontend && npm run build`
5. hit `/api/health/`
6. upload utility sample
7. upload travel sample
8. upload SAP sample
9. approve one row
10. open raw payload for one row
11. override scope for one row

## Deployment

See `DEPLOY.md` for Railway and Render instructions.
