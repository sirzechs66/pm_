# Breathe ESG Prototype Summary

## Overview

This repository contains a deployable Django and React prototype for ESG activity ingestion and review.

The current implementation is intentionally narrow:
- simple integer-based tenant scoping
- three ingestion sources: utility CSV, travel JSON, SAP CSV
- source-specific raw row storage
- unified `ActivityData` review model
- analyst review dashboard
- Railway and Render deployment support

## Current Architecture

### Backend

- Django serves the API and the built React frontend
- tenant scoping is handled through request middleware using `X-Tenant-Id`
- uploads are processed synchronously inside the request
- raw source rows are stored before normalization
- normalized rows are written to `ActivityData`
- audit entries are written to `ActivityAudit`

### Frontend

- React + Vite
- bundled into `backend/static/frontend`
- dashboard supports:
  - upload by source type
  - filter by source, status, suspicious flag
  - scope override
  - approve action
  - raw payload modal
  - retry for failed rows

## Data Model

Primary models:
- `UploadBatch`
- `UtilityRawRow`
- `TravelRawRow`
- `SapRawRow`
- `ActivityData`
- `ActivityAudit`

## API Surface

- `POST /api/upload/<source_type>/`
- `GET /api/activities/`
- `PATCH /api/activities/<id>/`
- `POST /api/activities/<id>/approve/`
- `GET /api/activities/<id>/raw/`
- `GET /api/health/`

## Tenant Model

This prototype does not use schema-based tenancy.

Each record stores `tenant_id` directly, and middleware attaches `request.tenant_id` from:
- `X-Tenant-Id` header
- query param fallback
- form field fallback

## Deployment

Deployment assets included:
- `railway.json`
- `nixpacks.toml`
- `Procfile`
- `render.yaml`
- `DEPLOY.md`

## Verification Status

Verified locally:
- Django checks under local settings
- Django checks under production settings
- database migrations
- backend tests in `apps.prototype.tests`
- frontend production build

## Intentional Omissions

Not included in the active prototype path:
- real external SAP or travel integrations
- background workers
- schema-based multi-tenancy
- advanced user roles
- PDF parsing

## Repo Intent

The active code path is the prototype app under `backend/apps/prototype/`.

Older experimental modules remain in the working tree but are not part of the staged deployable prototype.
