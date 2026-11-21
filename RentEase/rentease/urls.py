"""
URL configuration for RentEase project.

Maps top-level URL prefixes to each Django app's URL module.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django built-in admin
    path('admin/', admin.site.urls),

    # All application URLs handled by the properties app
    path('', include('properties.urls')),
]

# Serve uploaded media files during development (DEBUG=True only)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
