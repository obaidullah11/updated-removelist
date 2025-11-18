"""
Admin configuration for admin panel models.
"""
from django.contrib import admin
from .models import AdminNotification, DashboardMetric


@admin.register(AdminNotification)
class AdminNotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(DashboardMetric)
class DashboardMetricAdmin(admin.ModelAdmin):
    list_display = ['metric_type', 'value', 'period', 'date', 'created_at']
    list_filter = ['metric_type', 'period', 'date']
    search_fields = ['metric_type']
    readonly_fields = ['created_at']
    ordering = ['-date', '-created_at']





