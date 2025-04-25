from django.urls import path
from .views import frontend_home
from  .views import upload_file
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", frontend_home, name="frontend-home"),
    path('upload/', upload_file, name='upload_file')
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)