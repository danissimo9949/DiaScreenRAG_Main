from django.urls import path

from .views import PatientAnalyticsView

app_name = "analytic"

urlpatterns = [
    path("patient/<int:pk>/", PatientAnalyticsView.as_view(), name="patient_dashboard"),
]

