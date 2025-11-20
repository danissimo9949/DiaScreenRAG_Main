from django.urls import path

from .views import PatientAnalyticsView, PatientAnalyticsPDFExportView, analyze_analytics_data

app_name = "analytic"

urlpatterns = [
    path("patient/<int:pk>/", PatientAnalyticsView.as_view(), name="patient_dashboard"),
    path("patient/<int:pk>/export-pdf/", PatientAnalyticsPDFExportView.as_view(), name="patient_dashboard_pdf"),
    path("patient/<int:pk>/analyze/", analyze_analytics_data, name="analyze_data"),
]

