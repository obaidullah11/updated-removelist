from django.contrib import admin
from apps.verification.models import PartnerDocument  # <-- Correct import

@admin.register(PartnerDocument)
class PartnerDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'partner', 'is_submitted', 'is_verified', 'is_rejected', 'submitted_at', 'verified_at', 'rejected_at'
    )
    list_filter = ('is_submitted', 'is_verified', 'is_rejected')
    search_fields = ('partner__email',)