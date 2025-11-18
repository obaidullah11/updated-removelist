"""
Admin configuration for booking models.
"""
from django.contrib import admin
from .models import TimeSlot, Booking


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    """
    Admin configuration for TimeSlot model.
    """
    list_display = ['start_time', 'end_time', 'price', 'is_active']
    list_filter = ['is_active']
    ordering = ['start_time']
    
    fieldsets = (
        ('Time Details', {
            'fields': ('start_time', 'end_time')
        }),
        ('Pricing & Availability', {
            'fields': ('price', 'is_active')
        }),
    )


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """
    Admin configuration for Booking model.
    """
    list_display = [
        'confirmation_number', 'user', 'date',
        'status', 'phone_number', 'created_at'
    ]
    list_filter = ['status', 'date', 'created_at']
    search_fields = [
        'confirmation_number', 'user__email', 'user__first_name', 'user__last_name',
        'phone_number'
    ]
    readonly_fields = ['id', 'confirmation_number', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Booking Information', {
            'fields': ('confirmation_number', 'user', 'move', 'status')
        }),
        ('Schedule Details', {
            'fields': ('date','phone_number')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('user', 'move')
