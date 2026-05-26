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

