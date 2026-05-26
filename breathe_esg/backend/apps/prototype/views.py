from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ActivityAudit, ActivityData
from .serializers import ActivityDataSerializer
from .services import (
    actor_name,
    ingest_sap_file,
    ingest_travel_file,
    ingest_utility_file,
    retry_activity,
)


class IndexView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return render(request, "index.html")


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok"})


class UploadView(APIView):
    ingestion_map = {
        "utility": ingest_utility_file,
        "travel": ingest_travel_file,
        "sap": ingest_sap_file,
    }

    def post(self, request, source_type):
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            return Response({"detail": "File is required."}, status=status.HTTP_400_BAD_REQUEST)
        if source_type not in self.ingestion_map:
            return Response({"detail": "Unsupported source type."}, status=status.HTTP_404_NOT_FOUND)

        batch, activities = self.ingestion_map[source_type](uploaded_file, request.tenant_id)
        serializer = ActivityDataSerializer(activities, many=True)
        return Response(
            {
                "batch_id": batch.id,
                "source_type": source_type,
                "count": len(activities),
                "results": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class ActivityListView(APIView):
    def get(self, request):
        queryset = ActivityData.objects.filter(tenant_id=request.tenant_id)
        source_type = request.GET.get("source_type")
        status_filter = request.GET.get("status")
        suspicious_flag = request.GET.get("suspicious_flag")

        if source_type:
            queryset = queryset.filter(source_type=source_type)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if suspicious_flag is not None:
            queryset = queryset.filter(suspicious_flag=suspicious_flag.lower() == "true")

        return Response(ActivityDataSerializer(queryset, many=True).data)


class ActivityDetailView(APIView):
    def get_object(self, request, pk):
        return get_object_or_404(ActivityData, pk=pk, tenant_id=request.tenant_id)

    def patch(self, request, pk):
        activity = self.get_object(request, pk)

        if request.data.get("action") == "retry":
            try:
                activity = retry_activity(activity, request)
            except Exception as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            return Response(ActivityDataSerializer(activity).data)

        scope = request.data.get("scope")
        if scope is None:
            return Response({"detail": "Scope or action is required."}, status=status.HTTP_400_BAD_REQUEST)

        previous = {"scope": activity.scope, "status": activity.status}
        activity.previous_scope = activity.scope
        activity.scope = int(scope)
        activity.modified_by = actor_name(request)
        activity.save(update_fields=["previous_scope", "scope", "modified_by", "updated_at"])
        ActivityAudit.objects.create(
            tenant_id=activity.tenant_id,
            activity=activity,
            action="scope_override",
            actor=actor_name(request),
            previous_values=previous,
            new_values={"scope": activity.scope, "status": activity.status},
        )
        return Response(ActivityDataSerializer(activity).data)


class ActivityApproveView(APIView):
    def post(self, request, pk):
        activity = get_object_or_404(ActivityData, pk=pk, tenant_id=request.tenant_id)
        previous = {"status": activity.status, "approved_by": activity.approved_by}
        activity.previous_status = activity.status
        activity.status = "approved"
        activity.approved_by = actor_name(request)
        activity.approved_at = timezone.now()
        activity.modified_by = actor_name(request)
        activity.save(update_fields=["previous_status", "status", "approved_by", "approved_at", "modified_by", "updated_at"])
        ActivityAudit.objects.create(
            tenant_id=activity.tenant_id,
            activity=activity,
            action="approve",
            actor=actor_name(request),
            previous_values=previous,
            new_values={"status": activity.status, "approved_by": activity.approved_by},
        )
        return Response(ActivityDataSerializer(activity).data)


class ActivityRawView(APIView):
    def get(self, request, pk):
        activity = get_object_or_404(ActivityData, pk=pk, tenant_id=request.tenant_id)
        model_map = {
            "utility": "utilityrawrow",
            "travel": "travelrawrow",
            "sap": "saprawrow",
        }
        raw_row = getattr(activity.upload_batch, f"{model_map[activity.source_type]}s").get(id=activity.source_row_id)
        return Response(
            {
                "id": raw_row.id,
                "source_type": activity.source_type,
                "status": raw_row.status,
                "failure_reason": raw_row.failure_reason,
                "row_index": raw_row.row_index,
                "raw_data": raw_row.raw_data,
            }
        )
