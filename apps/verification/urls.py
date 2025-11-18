from django.urls import path
from .views import submit_partner_documents, approve_partner_documents, reject_partner_documents
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('partner/documents/submit/', submit_partner_documents, name='submit_partner_documents'),
    path('partner/documents/<uuid:pk>/approve/', approve_partner_documents, name='approve_partner_documents'),
    path('partner/documents/<uuid:pk>/reject/', reject_partner_documents, name='reject_partner_documents'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)