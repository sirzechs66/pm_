# Model Design

## Overview

The active prototype uses row-level tenant scoping with a simple integer `tenant_id`.

It does not use schema-based tenancy.

The core pattern is:
- store uploaded raw rows in source-specific tables
- normalize them into one review table
- keep an audit log of analyst actions

## Tenant Scoping

Tenant context is attached per request:
- header: `X-Tenant-Id`
- query fallback: `tenant_id`
- form fallback: `tenant_id`

Middleware sets `request.tenant_id`, and all API queries filter on that value.

## Core Models

### UploadBatch

Groups one uploaded file.

Fields:
- `tenant_id`
- `source_type`
- `original_filename`
- `created_at`

### UtilityRawRow

Stores parsed utility CSV rows.

Fields:
- `tenant_id`
- `upload_batch`
- `row_index`
- `status`
- `failure_reason`
- `raw_data`
- `meter_id`
- `start_time`
- `end_time`
- `usage_kwh`
- `cost`

### TravelRawRow

Stores parsed travel JSON segments.

Fields:
- `tenant_id`
- `upload_batch`
- `row_index`
- `status`
- `failure_reason`
- `raw_data`
- `trip_id`
- `segment_type`
- `departure_airport`
- `arrival_airport`
- `nights`
- `distance_km`

### SapRawRow

Stores parsed SAP CSV rows.

Fields:
- `tenant_id`
- `upload_batch`
- `row_index`
- `status`
- `failure_reason`
- `raw_data`
- `matnr`
- `maktx`
- `menge`
- `meins`
- `werks`
- `bsart`
- `erdat`

### ActivityData

Unified normalized review table.

Fields:
- `tenant_id`
- `upload_batch`
- `source_type`
- `source_row_id`
- `date`
- `quantity`
- `unit_normalised`
- `description`
- `scope`
- `status`
- `suspicious_flag`
- `failure_reason`
- `raw_data_link`
- `created_at`
- `updated_at`
- `approved_by`
- `approved_at`
- `modified_by`
- `previous_scope`
- `previous_status`

Status values:
- `pending_review`
- `approved`
- `failed`

Scope values:
- `1`
- `2`
- `3`

### ActivityAudit

Simple audit trail for analyst actions.

Fields:
- `tenant_id`
- `activity`
- `action`
- `actor`
- `previous_values`
- `new_values`
- `created_at`

## Normalization Flow

### Utility

- upload CSV
- create `UtilityRawRow`
- normalize to `ActivityData`
- default scope `2`
- unit normalized to `kWh`

### Travel

- upload JSON
- create `TravelRawRow`
- normalize segment into `ActivityData`
- default scope `3`
- unit normalized to `km` or `nights`

### SAP

- upload CSV
- create `SapRawRow`
- normalize to `ActivityData`
- unit mapping:
  - `KG -> kg`
  - `L -> kg` using density by material description
  - `PC -> kg` only for known material map
  - anything else fails
- default scope `1` for fuel-like descriptions

## Failure Handling

If normalization fails:
- raw row is stored with `status='failed'`
- failure reason is captured
- `ActivityData` row is still created
- normalized row gets:
  - `status='failed'`
  - `failure_reason`
  - zero quantity

## Suspicious Flag

Rows are flagged suspicious if:
- quantity is `0`
- quantity is more than three standard deviations from the batch mean

## Audit Behavior

Actions recorded in `ActivityAudit` include:
- `approve`
- `scope_override`
- `retry`

## Raw Lineage

Each normalized row stores:
- `source_type`
- `source_row_id`
- `raw_data_link`

This allows the frontend to open the original payload through:
- `GET /api/activities/<id>/raw/`
