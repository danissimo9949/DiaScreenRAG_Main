from django.urls import path

from . import views


app_name = 'card'


urlpatterns = [
    path('', views.patient_card, name='patient_card'),

    path('glucose/<int:pk>/edit/', views.GlucoseUpdateView.as_view(), name='glucose_edit'),
    path('glucose/<int:pk>/delete/', views.GlucoseDeleteView.as_view(), name='glucose_delete'),
    path('activity/<int:pk>/edit/', views.ActivityUpdateView.as_view(), name='activity_edit'),
    path('activity/<int:pk>/delete/', views.ActivityDeleteView.as_view(), name='activity_delete'),
    path('food/<int:pk>/edit/', views.FoodUpdateView.as_view(), name='food_edit'),
    path('food/<int:pk>/delete/', views.FoodDeleteView.as_view(), name='food_delete'),
    path('insuline/<int:pk>/edit/', views.InsulineUpdateView.as_view(), name='insuline_edit'),
    path('insuline/<int:pk>/delete/', views.InsulineDeleteView.as_view(), name='insuline_delete'),

    # Navigation buttons targets
    path('doctor-report/', views.doctor_report, name='doctor_report'),
]


