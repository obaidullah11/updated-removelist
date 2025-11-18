"""
URL configuration for removealist_backend project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def health_check(request):
    """Health check endpoint for monitoring."""
    return JsonResponse({
        'success': True,
        'message': 'RemoveList API is healthy',
        'status': 'ok'
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/move/', include('apps.moves.urls')),
    path('api/booking/', include('apps.bookings.urls')),
    path('api/inventory/', include('apps.inventory.urls')),
    path('api/timeline/', include('apps.timeline.urls')),
    path('api/checklist/', include('apps.timeline.urls')),  # Checklist is part of timeline
    path('api/files/', include('apps.files.urls')),
    path('api/verification/', include('apps.verification.urls')),
    path('api/admin/', include('apps.admin_panel.urls')),
    path('api/tasks/', include('apps.tasks.urls')),
    path('api/services/', include('apps.services.urls')),
    path('api/pricing/', include('apps.pricing.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
