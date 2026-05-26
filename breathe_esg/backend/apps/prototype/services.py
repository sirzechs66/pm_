import csv
import io
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from .models import (
    ActivityAudit,
    ActivityData,
    SapRawRow,
    TravelRawRow,
    UploadBatch,
    UtilityRawRow,
)

SAP_LITER_DENSITY = {
    "diesel": Decimal("0.832"),
    "petrol": Decimal("0.745"),
    "gasoline": Decimal("0.745"),
    "fuel oil": Decimal("0.96"),
    "heating oil": Decimal("0.84"),
    "lubricant": Decimal("0.88"),
}

SAP_PIECE_TO_KG_MAP = {
    "FUEL-DRUM-200": Decimal("200"),
    "LUBE-BOX-20": Decimal("20"),
}


@dataclass
class NormalizedRecord:
    date: date | None
    quantity: Decimal
    unit_normalised: str
    description: str
    scope: int
    status: str
    failure_reason: str = ""


def parse_decimal(value, field_name):
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, AttributeError):
        raise ValueError(f"Invalid decimal in {field_name}.")


def parse_datetime_value(value, field_name):
    parsed = parse_datetime(str(value))
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError as exc:
            raise ValueError(f"Invalid datetime in {field_name}.") from exc
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, dt_timezone.utc)
    return parsed


def parse_date_value(value, field_name):
    value = str(value).strip()
    for parser in (lambda x: parse_date(x), lambda x: datetime.strptime(x, "%Y%m%d").date()):
        try:
            parsed = parser(value)
        except ValueError:
            parsed = None
        if parsed:
            return parsed
    raise ValueError(f"Invalid date in {field_name}.")


def actor_name(request):
    return request.headers.get("X-Analyst-Name", "Analyst")


def make_raw_link(activity_id):
    return reverse("activity-raw", kwargs={"pk": activity_id})


def detect_suspicious(activities):
    successful = [activity for activity in activities if activity.status != "failed"]
    if not successful:
        return

    values = [activity.quantity for activity in successful]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    std_dev = variance.sqrt() if variance > 0 else Decimal("0")

    for activity in successful:
        suspicious = activity.quantity == 0
        if std_dev > 0 and abs(activity.quantity - mean) > std_dev * 3:
            suspicious = True
        if suspicious != activity.suspicious_flag:
            activity.suspicious_flag = suspicious
            activity.save(update_fields=["suspicious_flag", "updated_at"])


def normalize_utility_row(raw_row):
    usage = raw_row.usage_kwh
    if usage is None:
        raise ValueError("Usage_kWh is required.")
    if raw_row.start_time is None:
        raise ValueError("StartTime is required.")
    return NormalizedRecord(
        date=raw_row.start_time.date(),
        quantity=usage,
        unit_normalised="kWh",
        description=f"Utility meter {raw_row.meter_id or 'unknown'}",
        scope=2,
        status="pending_review",
    )


def normalize_travel_row(raw_row):
    segment_type = (raw_row.segment_type or "").lower()
    if segment_type == "hotel":
        quantity = raw_row.nights
        unit = "nights"
    else:
        quantity = raw_row.distance_km
        unit = "km"

    if quantity is None:
        raise ValueError("Travel segment quantity is required.")

    description_bits = [raw_row.segment_type or "Segment"]
    if raw_row.departure_airport or raw_row.arrival_airport:
        description_bits.append(f"{raw_row.departure_airport}-{raw_row.arrival_airport}".strip("-"))

    trip_date = parse_date(str(raw_row.raw_data.get("date"))) if raw_row.raw_data.get("date") else timezone.now().date()

    return NormalizedRecord(
        date=trip_date,
        quantity=quantity,
        unit_normalised=unit,
        description=" ".join(bit for bit in description_bits if bit),
        scope=3,
        status="pending_review",
    )


def normalize_sap_row(raw_row):
    quantity = raw_row.menge
    if quantity is None:
        raise ValueError("MENGE is required.")

    unit = (raw_row.meins or "").strip().upper()
    description = raw_row.maktx or raw_row.matnr or "SAP material"
    description_lower = description.lower()

    if unit == "KG":
        normalized_quantity = quantity
    elif unit == "L":
        density = next((factor for key, factor in SAP_LITER_DENSITY.items() if key in description_lower), None)
        if density is None:
            raise ValueError("No density mapping found for liter-based SAP row.")
        normalized_quantity = quantity * density
    elif unit == "PC":
        piece_factor = SAP_PIECE_TO_KG_MAP.get(raw_row.matnr)
        if piece_factor is None:
            raise ValueError("No piece-to-kg mapping found for SAP material.")
        normalized_quantity = quantity * piece_factor
    else:
        raise ValueError(f"Unsupported SAP unit '{unit}'.")

    scope = 1 if "fuel" in description_lower or "diesel" in description_lower or "petrol" in description_lower or "gasoline" in description_lower else None
    if scope is None:
        raise ValueError("SAP row could not be classified as fuel for Scope 1.")

    return NormalizedRecord(
        date=raw_row.erdat,
        quantity=normalized_quantity.quantize(Decimal("0.0001")),
        unit_normalised="kg",
        description=f"{description} ({raw_row.werks})".strip(),
        scope=scope,
        status="pending_review",
    )


def create_activity_for_raw_row(raw_row, normalized, source_type):
    activity = ActivityData.objects.create(
        tenant_id=raw_row.tenant_id,
        upload_batch=raw_row.upload_batch,
        source_type=source_type,
        source_row_id=raw_row.id,
        date=normalized.date,
        quantity=normalized.quantity,
        unit_normalised=normalized.unit_normalised,
        description=normalized.description,
        scope=normalized.scope,
        status=normalized.status,
        failure_reason=normalized.failure_reason,
    )
    activity.raw_data_link = make_raw_link(activity.id)
    activity.save(update_fields=["raw_data_link"])
    return activity


def record_failure(raw_row, source_type, reason):
    raw_row.status = "failed"
    raw_row.failure_reason = str(reason)
    raw_row.save(update_fields=["status", "failure_reason", "updated_at"])
    activity = ActivityData.objects.create(
        tenant_id=raw_row.tenant_id,
        upload_batch=raw_row.upload_batch,
        source_type=source_type,
        source_row_id=raw_row.id,
        date=getattr(raw_row, "erdat", None) or (raw_row.start_time.date() if getattr(raw_row, "start_time", None) else None),
        quantity=Decimal("0"),
        unit_normalised="",
        description=(getattr(raw_row, "maktx", None) or getattr(raw_row, "segment_type", None) or getattr(raw_row, "meter_id", None) or "Failed row"),
        scope=None,
        status="failed",
        failure_reason=str(reason),
    )
    activity.raw_data_link = make_raw_link(activity.id)
    activity.save(update_fields=["raw_data_link"])
    return activity


@transaction.atomic
def ingest_utility_file(uploaded_file, tenant_id):
    batch = UploadBatch.objects.create(
        tenant_id=tenant_id,
        source_type="utility",
        original_filename=uploaded_file.name,
    )
    activities = []
    content = uploaded_file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    for index, row in enumerate(reader, start=1):
        try:
            raw_row = UtilityRawRow.objects.create(
                tenant_id=tenant_id,
                upload_batch=batch,
                row_index=index,
                meter_id=(row.get("MeterID") or "").strip(),
                start_time=parse_datetime_value(row.get("StartTime"), "StartTime"),
                end_time=parse_datetime_value(row.get("EndTime"), "EndTime"),
                usage_kwh=parse_decimal(row.get("Usage_kWh"), "Usage_kWh"),
                cost=parse_decimal(row.get("Cost"), "Cost") if row.get("Cost") not in (None, "") else None,
                raw_data=row,
            )
            activities.append(create_activity_for_raw_row(raw_row, normalize_utility_row(raw_row), "utility"))
        except Exception as exc:
            raw_row = UtilityRawRow.objects.create(
                tenant_id=tenant_id,
                upload_batch=batch,
                row_index=index,
                meter_id=(row.get("MeterID") or "").strip(),
                raw_data=row,
                status="failed",
                failure_reason=str(exc),
            )
            activities.append(record_failure(raw_row, "utility", exc))
    detect_suspicious(activities)
    return batch, activities


@transaction.atomic
def ingest_travel_file(uploaded_file, tenant_id):
    batch = UploadBatch.objects.create(
        tenant_id=tenant_id,
        source_type="travel",
        original_filename=uploaded_file.name,
    )
    content = uploaded_file.read().decode("utf-8-sig")
    payload = json.loads(content)
    activities = []
    row_index = 1
    for trip in payload.get("trips", []):
        trip_id = str(trip.get("id", ""))
        for segment in trip.get("segments", []):
            try:
                raw_row = TravelRawRow.objects.create(
                    tenant_id=tenant_id,
                    upload_batch=batch,
                    row_index=row_index,
                    trip_id=trip_id,
                    segment_type=str(segment.get("type", "")),
                    departure_airport=str(segment.get("departure_airport", "")),
                    arrival_airport=str(segment.get("arrival_airport", "")),
                    nights=parse_decimal(segment.get("nights"), "nights") if segment.get("nights") not in (None, "") else None,
                    distance_km=parse_decimal(segment.get("distance_km"), "distance_km") if segment.get("distance_km") not in (None, "") else None,
                    raw_data={**segment, "trip_id": trip_id},
                )
                activities.append(create_activity_for_raw_row(raw_row, normalize_travel_row(raw_row), "travel"))
            except Exception as exc:
                raw_row = TravelRawRow.objects.create(
                    tenant_id=tenant_id,
                    upload_batch=batch,
                    row_index=row_index,
                    trip_id=trip_id,
                    segment_type=str(segment.get("type", "")),
                    raw_data={**segment, "trip_id": trip_id},
                    status="failed",
                    failure_reason=str(exc),
                )
                activities.append(record_failure(raw_row, "travel", exc))
            row_index += 1
    detect_suspicious(activities)
    return batch, activities


@transaction.atomic
def ingest_sap_file(uploaded_file, tenant_id):
    batch = UploadBatch.objects.create(
        tenant_id=tenant_id,
        source_type="sap",
        original_filename=uploaded_file.name,
    )
    content = uploaded_file.read().decode("utf-8-sig")
    sample = content.splitlines()[0] if content.splitlines() else ""
    delimiter = ";" if sample.count(";") >= sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
    activities = []
    for index, row in enumerate(reader, start=1):
        try:
            raw_row = SapRawRow.objects.create(
                tenant_id=tenant_id,
                upload_batch=batch,
                row_index=index,
                matnr=(row.get("MATNR") or "").strip(),
                maktx=(row.get("MAKTX") or "").strip(),
                menge=parse_decimal(row.get("MENGE"), "MENGE"),
                meins=(row.get("MEINS") or "").strip(),
                werks=(row.get("WERKS") or "").strip(),
                bsart=(row.get("BSART") or "").strip(),
                erdat=parse_date_value(row.get("ERDAT"), "ERDAT"),
                raw_data=row,
            )
            activities.append(create_activity_for_raw_row(raw_row, normalize_sap_row(raw_row), "sap"))
        except Exception as exc:
            raw_row = SapRawRow.objects.create(
                tenant_id=tenant_id,
                upload_batch=batch,
                row_index=index,
                matnr=(row.get("MATNR") or "").strip(),
                maktx=(row.get("MAKTX") or "").strip(),
                meins=(row.get("MEINS") or "").strip(),
                raw_data=row,
                status="failed",
                failure_reason=str(exc),
            )
            activities.append(record_failure(raw_row, "sap", exc))
    detect_suspicious(activities)
    return batch, activities


def get_raw_row(source_type, source_row_id, tenant_id):
    model = {"utility": UtilityRawRow, "travel": TravelRawRow, "sap": SapRawRow}[source_type]
    return model.objects.get(id=source_row_id, tenant_id=tenant_id)


@transaction.atomic
def retry_activity(activity, request):
    raw_row = get_raw_row(activity.source_type, activity.source_row_id, activity.tenant_id)
    normalizers = {
        "utility": normalize_utility_row,
        "travel": normalize_travel_row,
        "sap": normalize_sap_row,
    }
    previous = {"status": activity.status, "scope": activity.scope, "failure_reason": activity.failure_reason}
    normalized = normalizers[activity.source_type](raw_row)
    activity.previous_status = activity.status
    activity.previous_scope = activity.scope
    activity.date = normalized.date
    activity.quantity = normalized.quantity
    activity.unit_normalised = normalized.unit_normalised
    activity.description = normalized.description
    activity.scope = normalized.scope
    activity.status = normalized.status
    activity.failure_reason = normalized.failure_reason
    activity.suspicious_flag = activity.quantity == 0
    activity.modified_by = actor_name(request)
    activity.save()
    raw_row.status = "processed"
    raw_row.failure_reason = ""
    raw_row.save(update_fields=["status", "failure_reason", "updated_at"])
    ActivityAudit.objects.create(
        tenant_id=activity.tenant_id,
        activity=activity,
        action="retry",
        actor=actor_name(request),
        previous_values=previous,
        new_values={"status": activity.status, "scope": activity.scope},
    )
    return activity
