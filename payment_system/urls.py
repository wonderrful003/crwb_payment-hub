from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("uploads.urls")),
]

if settings.DEBUG:
    # Serve media files
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Serve static files (if STATICFILES_DIRS is defined)
    if hasattr(settings, 'STATICFILES_DIRS') and settings.STATICFILES_DIRS:
        urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])