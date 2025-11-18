from django.conf import settings
from django.db import models
from apps.authentication.models import User
from django.utils import timezone

class PartnerDocument(models.Model):
    """
    Stores documents submitted by a partner for verification.
    """
    partner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_1 = models.FileField(upload_to='partner_documents/',null=True, blank=True)
    document_2 = models.FileField(upload_to='partner_documents/',null=True, blank=True)
    document_3 = models.FileField(upload_to='partner_documents/',null=True, blank=True)
    document_4 = models.FileField(upload_to='partner_documents/',null=True, blank=True)
    is_submitted = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'partner_documents'
        verbose_name = 'Partner Document'
        verbose_name_plural = 'Partner Documents'

    def __str__(self):
        return f"Documents for {self.partner.email}"

    def approve(self):
        self.is_verified = True
        self.is_rejected = False
        self.verified_at = timezone.now()
        self.save()

    def reject(self, reason=""):
        self.is_verified = False
        self.is_rejected = True
        self.rejected_at = timezone.now()
        self.rejection_reason = reason
        self.save()