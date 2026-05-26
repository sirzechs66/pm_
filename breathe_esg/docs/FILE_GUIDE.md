# File Guide

This guide describes the active files for the current deployable prototype.

## Root

- `DEPLOY.md`: deployment and operation steps
- `render.yaml`: Render configuration
- `railway.json`: Railway deployment configuration
- `nixpacks.toml`: Railway build/runtime package configuration
- `Procfile`: process entrypoint
- `requirements.txt`: root convenience include for backend requirements
- `package.json`: root convenience scripts for frontend
- `sample_data/`: upload-ready example files

## Backend

### Entry Points

- `backend/manage.py`: Django CLI entrypoint
- `backend/config/urls.py`: top-level routing
- `backend/config/wsgi.py`: WSGI entrypoint for Gunicorn

### Settings

- `backend/config/settings/base.py`: shared settings, database parsing, static handling, middleware
- `backend/config/settings/local.py`: local development overrides
- `backend/config/settings/production.py`: production overrides

### Active App

- `backend/apps/prototype/models.py`: upload batches, raw rows, normalized activity model, audit model
- `backend/apps/prototype/services.py`: ingestion, normalization, suspicious-flagging, retry logic
- `backend/apps/prototype/views.py`: upload, list, approve, patch, raw, and health endpoints
- `backend/apps/prototype/serializers.py`: API serializers
- `backend/apps/prototype/middleware.py`: request tenant scoping via `X-Tenant-Id`
- `backend/apps/prototype/tests.py`: backend smoke tests
- `backend/apps/prototype/migrations/0001_initial.py`: schema for the active prototype

### Templates and Static Assets

- `backend/templates/index.html`: Django-served HTML shell for the React app
- `backend/static/frontend/`: built frontend assets

## Frontend

- `frontend/src/App.tsx`: review dashboard UI
- `frontend/src/shared/api/client.ts`: API client and types
- `frontend/src/styles.css`: UI styling
- `frontend/src/main.tsx`: React bootstrap
- `frontend/vite.config.ts`: frontend build and local dev proxy configuration
- `frontend/package.json`: frontend dependencies and scripts

## Sample Data

- `sample_data/utility_sample.csv`: Green Button style sample upload
- `sample_data/travel_sample.json`: travel sample upload

## Docs

- `docs/MODEL.md`: current active data model
- `docs/DECISIONS.md`: architecture and implementation decisions
- `docs/TRADEOFFS.md`: omitted features and boundaries
- `docs/SOURCES.md`: source format assumptions and research
- `docs/PROJECT_SUMMARY.md`: current prototype summary
- `docs/RUNBOOK.md`: local run and test guide
- `docs/FILE_GUIDE.md`: this file

## Legacy Files

Older experimental modules and planning files may still exist in the working tree, but they are not part of the staged deployable prototype unless explicitly staged later.
