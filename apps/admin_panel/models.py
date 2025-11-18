"""
Admin panel models for notifications and analytics.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from apps.authentication.models import User
from apps.bookings.models import Booking
from apps.verification.models import PartnerDocument

User = get_user_model()


class AdminNotification(models.Model):
    """
    Model for admin notifications and activity feed.
    """
    NOTIFICATION_TYPES = (
        ('success', 'Success'),
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Optional foreign keys for context
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, null=True, blank=True)
    partner_document = models.ForeignKey(PartnerDocument, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Admin Notification'
        verbose_name_plural = 'Admin Notifications'
    
    def __str__(self):
        return f"{self.title} - {self.get_notification_type_display()}"


class DashboardMetric(models.Model):
    """
    Model to store dashboard metrics and analytics data.
    """
    METRIC_TYPES = (
        ('users', 'Users'),
        ('partners', 'Partners'),
        ('bookings', 'Bookings'),
        ('revenue', 'Revenue'),
        ('eco_score', 'Eco Score'),
        ('carbon_offset', 'Carbon Offset'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    metric_type = models.CharField(max_length=20, choices=METRIC_TYPES)
    value = models.DecimalField(max_digits=15, decimal_places=2)
    period = models.CharField(max_length=20)  # daily, weekly, monthly, yearly
    date = models.DateField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['metric_type', 'period', 'date']
        ordering = ['-date']
        verbose_name = 'Dashboard Metric'
        verbose_name_plural = 'Dashboard Metrics'
    
    def __str__(self):
        return f"{self.get_metric_type_display()} - {self.period} - {self.date}"
