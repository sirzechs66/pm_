from django.urls import path

from .views import (
    ActivityApproveView,
    ActivityDetailView,
    ActivityListView,
    ActivityRawView,
    HealthView,
    UploadView,
)


urlpatterns = [
    path("api/health/", HealthView.as_view(), name="health"),
    path("api/upload/<str:source_type>/", UploadView.as_view(), name="upload"),
    path("api/activities/", ActivityListView.as_view(), name="activity-list"),
    path("api/activities/<int:pk>/", ActivityDetailView.as_view(), name="activity-detail"),
    path("api/activities/<int:pk>/approve/", ActivityApproveView.as_view(), name="activity-approve"),
    path("api/activities/<int:pk>/raw/", ActivityRawView.as_view(), name="activity-raw"),
]
