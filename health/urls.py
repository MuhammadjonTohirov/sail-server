from django.urls import path
from .views import liveness

urlpatterns = [
    path("", liveness, name="healthz"),
]

