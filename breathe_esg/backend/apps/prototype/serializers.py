from rest_framework import serializers

from .models import ActivityAudit, ActivityData


class ActivityAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityAudit
        fields = [
            "id",
            "action",
            "actor",
            "previous_values",
            "new_values",
            "created_at",
        ]


class ActivityDataSerializer(serializers.ModelSerializer):
    audits = ActivityAuditSerializer(many=True, read_only=True)

    class Meta:
        model = ActivityData
        fields = [
            "id",
            "tenant_id",
            "source_type",
            "date",
            "quantity",
            "unit_normalised",
            "description",
            "scope",
            "status",
            "suspicious_flag",
            "failure_reason",
            "raw_data_link",
            "created_at",
            "updated_at",
            "approved_by",
            "approved_at",
            "modified_by",
            "previous_scope",
            "previous_status",
            "audits",
        ]
        read_only_fields = [
            "tenant_id",
            "source_type",
            "date",
            "quantity",
            "unit_normalised",
            "description",
            "status",
            "failure_reason",
            "raw_data_link",
            "created_at",
            "updated_at",
            "approved_by",
            "approved_at",
            "modified_by",
            "previous_scope",
            "previous_status",
            "audits",
        ]

