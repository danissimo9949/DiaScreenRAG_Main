from django.urls import path

from . import views

app_name = "support"

urlpatterns = [
    path("create/", views.create_ticket, name="create_ticket"),
]


