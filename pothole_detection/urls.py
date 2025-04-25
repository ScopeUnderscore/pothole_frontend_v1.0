
# from django.contrib import admin
# from django.urls import path, include
# from django.conf import settings
# from django.conf.urls.static import static
# from detection.views import upload_file


# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('upload/', upload_file, name='upload_file'),
#     path("", include("frontend.urls")),  # Frontend routes
# ]

# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# your_project/urls.py
"""
URL configuration for the pothole detection Django project.
Defines routes for admin, file uploads, video status checks, and frontend pages.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from frontend.views import upload_file, video_status

urlpatterns = [
    path('admin/', admin.site.urls),
    path('upload/', upload_file, name='upload_file'),
    path('video-status/<str:task_id>/', video_status, name='video_status'),
    path('', include('frontend.urls')),  # Frontend routes
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)