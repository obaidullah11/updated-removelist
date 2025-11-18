"""
Admin configuration for timeline models.
"""
from django.contrib import admin
from .models import TimelineEvent, ChecklistItem, ChecklistTemplate


@admin.register(TimelineEvent)
class TimelineEventAdmin(admin.ModelAdmin):
    """
    Admin configuration for TimelineEvent model.
    """
    list_display = [
        'title', 'move', 'days_from_move', 'category', 'priority',
        'completed', 'due_date', 'created_at'
    ]
    list_filter = ['category', 'priority', 'completed', 'created_at']
    search_fields = [
        'title', 'description', 'move__user__email',
        'move__current_location', 'move__destination_location'
    ]
    readonly_fields = ['id', 'created_at', 'updated_at', 'due_date']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Event Information', {
            'fields': ('move', 'title', 'description', 'completed')
        }),
        ('Scheduling', {
            'fields': ('days_from_move', 'due_date', 'estimated_time')
        }),
        ('Classification', {
            'fields': ('category', 'priority')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('move', 'move__user')


@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    """
    Admin configuration for ChecklistItem model.
    """
    list_display = [
        'title', 'move', 'week', 'priority', 'completed',
        'is_custom', 'created_at'
    ]
    list_filter = ['week', 'priority', 'completed', 'is_custom', 'created_at']
    search_fields = [
        'title', 'move__user__email',
        'move__current_location', 'move__destination_location'
    ]
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Task Information', {
            'fields': ('move', 'title', 'completed', 'is_custom')
        }),
        ('Scheduling', {
            'fields': ('week', 'priority')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('move', 'move__user')


@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    """
    Admin configuration for ChecklistTemplate model.
    """
    list_display = ['title', 'week', 'priority', 'is_active', 'created_at']
    list_filter = ['week', 'priority', 'is_active', 'created_at']
    search_fields = ['title']
    ordering = ['-week', 'priority', 'title']
    
    fieldsets = (
        ('Template Information', {
            'fields': ('title', 'is_active')
        }),
        ('Scheduling', {
            'fields': ('week', 'priority')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
