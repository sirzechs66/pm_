from django.db import models


class UploadBatch(models.Model):
    SOURCE_TYPES = (
        ("utility", "Utility"),
        ("travel", "Travel"),
        ("sap", "SAP"),
    )

    tenant_id = models.IntegerField(db_index=True)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    original_filename = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class RawRowBase(models.Model):
    STATUS_CHOICES = (
        ("processed", "Processed"),
        ("failed", "Failed"),
    )

    tenant_id = models.IntegerField(db_index=True)
    upload_batch = models.ForeignKey(
        UploadBatch,
        on_delete=models.CASCADE,
        related_name="%(class)ss",
    )
    row_index = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="processed")
    failure_reason = models.TextField(blank=True)
    raw_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["row_index"]


class UtilityRawRow(RawRowBase):
    meter_id = models.CharField(max_length=100, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    usage_kwh = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    cost = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)


class TravelRawRow(RawRowBase):
    trip_id = models.CharField(max_length=100, blank=True)
    segment_type = models.CharField(max_length=50, blank=True)
    departure_airport = models.CharField(max_length=10, blank=True)
    arrival_airport = models.CharField(max_length=10, blank=True)
    nights = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    distance_km = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)


class SapRawRow(RawRowBase):
    matnr = models.CharField(max_length=100, blank=True)
    maktx = models.CharField(max_length=255, blank=True)
    menge = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    meins = models.CharField(max_length=20, blank=True)
    werks = models.CharField(max_length=100, blank=True)
    bsart = models.CharField(max_length=50, blank=True)
    erdat = models.DateField(null=True, blank=True)


class ActivityData(models.Model):
    SOURCE_TYPES = UploadBatch.SOURCE_TYPES
    STATUS_CHOICES = (
        ("pending_review", "Pending Review"),
        ("approved", "Approved"),
        ("failed", "Failed"),
    )
    SCOPE_CHOICES = (
        (1, "Scope 1"),
        (2, "Scope 2"),
        (3, "Scope 3"),
    )

    tenant_id = models.IntegerField(db_index=True)
    upload_batch = models.ForeignKey(
        UploadBatch,
        on_delete=models.CASCADE,
        related_name="activities",
        null=True,
        blank=True,
    )
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    source_row_id = models.PositiveIntegerField()
    date = models.DateField(null=True, blank=True)
    quantity = models.DecimalField(max_digits=16, decimal_places=4, default=0)
    unit_normalised = models.CharField(max_length=20, blank=True)
    description = models.CharField(max_length=255)
    scope = models.IntegerField(choices=SCOPE_CHOICES, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending_review")
    suspicious_flag = models.BooleanField(default=False)
    failure_reason = models.TextField(blank=True)
    raw_data_link = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.CharField(max_length=100, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    modified_by = models.CharField(max_length=100, blank=True)
    previous_scope = models.IntegerField(null=True, blank=True)
    previous_status = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["tenant_id", "source_type"]),
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "suspicious_flag"]),
        ]


class ActivityAudit(models.Model):
    tenant_id = models.IntegerField(db_index=True)
    activity = models.ForeignKey(ActivityData, on_delete=models.CASCADE, related_name="audits")
    action = models.CharField(max_length=50)
    actor = models.CharField(max_length=100, blank=True)
    previous_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

