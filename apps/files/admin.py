"""
Admin configuration for file models.
"""
from django.contrib import admin
from .models import FloorPlan, Document


@admin.register(FloorPlan)
class FloorPlanAdmin(admin.ModelAdmin):
    """
    Admin configuration for FloorPlan model.
    """
    list_display = [
        'filename', 'move', 'location_type', 'size_display',
        'uploaded_at'
    ]
    list_filter = ['location_type', 'uploaded_at']
    search_fields = [
        'filename', 'move__user__email',
        'move__current_location', 'move__destination_location'
    ]
    readonly_fields = ['id', 'filename', 'size', 'uploaded_at']
    ordering = ['-uploaded_at']
    
    fieldsets = (
        ('File Information', {
            'fields': ('move', 'file', 'filename', 'size_display')
        }),
        ('Details', {
            'fields': ('location_type',)
        }),
        ('Timestamps', {
            'fields': ('uploaded_at',),
            'classes': ('collapse',)
        }),
    )
    
    def size_display(self, obj):
        """Display file size in human readable format."""
        if obj.size:
            if obj.size < 1024:
                return f"{obj.size} B"
            elif obj.size < 1024 * 1024:
                return f"{obj.size / 1024:.1f} KB"
            else:
                return f"{obj.size / (1024 * 1024):.1f} MB"
        return "Unknown"
    size_display.short_description = "File Size"
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('move', 'move__user')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """
    Admin configuration for Document model.
    """
    list_display = [
        'filename', 'move', 'document_type', 'size_display',
        'uploaded_at'
    ]
    list_filter = ['document_type', 'uploaded_at']
    search_fields = [
        'filename', 'move__user__email',
        'move__current_location', 'move__destination_location'
    ]
    readonly_fields = ['id', 'filename', 'size', 'uploaded_at']
    ordering = ['-uploaded_at']
    
    fieldsets = (
        ('File Information', {
            'fields': ('move', 'file', 'filename', 'size_display')
        }),
        ('Details', {
            'fields': ('document_type',)
        }),
        ('Timestamps', {
            'fields': ('uploaded_at',),
            'classes': ('collapse',)
        }),
    )
    
    def size_display(self, obj):
        """Display file size in human readable format."""
        if obj.size:
            if obj.size < 1024:
                return f"{obj.size} B"
            elif obj.size < 1024 * 1024:
                return f"{obj.size / 1024:.1f} KB"
            else:
                return f"{obj.size / (1024 * 1024):.1f} MB"
        return "Unknown"
    size_display.short_description = "File Size"
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('move', 'move__user')
