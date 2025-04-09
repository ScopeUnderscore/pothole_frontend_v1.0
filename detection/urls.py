from django.urls import path
from .views import PotholeDetectionView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('detect/', PotholeDetectionView.as_view(), name='detect-pothole'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

