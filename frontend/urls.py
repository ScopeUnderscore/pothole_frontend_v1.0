from django.urls import path
from .views import frontend_home

urlpatterns = [
    path("", frontend_home, name="frontend-home"),
]
