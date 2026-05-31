from django.urls import path

from .views import CrowdDetectionUploadView


urlpatterns = [
    path(
        'detect/',
        CrowdDetectionUploadView.as_view(),
        name='crowd_detection_upload'
    ),
]
