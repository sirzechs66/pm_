from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from .models import ActivityData


class PrototypeFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.defaults["HTTP_X_TENANT_ID"] = "1"
        self.client.defaults["HTTP_X_ANALYST_NAME"] = "QA Analyst"

    def test_utility_upload_and_approval(self):
        csv_content = (
            "MeterID,StartTime,EndTime,Usage_kWh,Cost\n"
            "MTR-1,2025-03-01T00:00:00Z,2025-03-31T23:59:59Z,1200,180.25\n"
        )
        upload = SimpleUploadedFile("utility.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = self.client.post("/api/upload/utility/", {"file": upload}, format="multipart")
        self.assertEqual(response.status_code, 201)
        activity_id = response.data["results"][0]["id"]

        approve = self.client.post(f"/api/activities/{activity_id}/approve/")
        self.assertEqual(approve.status_code, 200)
        self.assertEqual(approve.data["status"], "approved")

    def test_utility_upload_accepts_common_csv_datetime_formats(self):
        csv_content = (
            "MeterID,StartTime,EndTime,Usage_kWh,Cost\n"
            "MTR-2,03/01/2025 00:00,03/31/2025 23:59,1200,180.25\n"
        )
        upload = SimpleUploadedFile("utility.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = self.client.post("/api/upload/utility/", {"file": upload}, format="multipart")
        self.assertEqual(response.status_code, 201)
        result = response.data["results"][0]
        self.assertEqual(result["status"], "pending_review")
        self.assertEqual(result["quantity"], "1200.0000")
        self.assertEqual(result["unit_normalised"], "kWh")

    def test_failed_utility_row_can_retry_after_parser_fix(self):
        csv_content = (
            "MeterID,StartTime,EndTime,Usage_kWh,Cost\n"
            "MTR-3,03/01/2025 00:00,03/31/2025 23:59,250,40.00\n"
        )
        upload = SimpleUploadedFile("utility.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = self.client.post("/api/upload/utility/", {"file": upload}, format="multipart")
        self.assertEqual(response.status_code, 201)
        activity_id = response.data["results"][0]["id"]

        activity = ActivityData.objects.get(id=activity_id)
        activity.status = "failed"
        activity.failure_reason = "Invalid datetime in StartTime."
        activity.save(update_fields=["status", "failure_reason", "updated_at"])

        raw_row = activity.upload_batch.utilityrawrows.get(id=activity.source_row_id)
        raw_row.start_time = None
        raw_row.end_time = None
        raw_row.usage_kwh = None
        raw_row.status = "failed"
        raw_row.failure_reason = "Invalid datetime in StartTime."
        raw_row.save(update_fields=["start_time", "end_time", "usage_kwh", "status", "failure_reason", "updated_at"])

        retry = self.client.patch(f"/api/activities/{activity_id}/", {"action": "retry"}, format="json")
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.data["status"], "pending_review")
        self.assertEqual(retry.data["quantity"], "250.0000")

    def test_sap_failed_row_can_retry(self):
        csv_content = (
            "MATNR,MAKTX,MENGE,MEINS,WERKS,BSART,ERDAT\n"
            "UNKNOWN,Unknown Item,4,PC,PL01,NB,2025-03-11\n"
        )
        upload = SimpleUploadedFile("sap.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = self.client.post("/api/upload/sap/", {"file": upload}, format="multipart")
        self.assertEqual(response.status_code, 201)
        activity_id = response.data["results"][0]["id"]
        activity = ActivityData.objects.get(id=activity_id)
        self.assertEqual(activity.status, "failed")

        retry = self.client.patch(f"/api/activities/{activity_id}/", {"action": "retry"}, format="json")
        self.assertEqual(retry.status_code, 400)
