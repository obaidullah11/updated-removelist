"""
Admin configuration for move models.
"""
from django.contrib import admin
from .models import Move, MoveCollaborator, TaskAssignment


@admin.register(Move)
class MoveAdmin(admin.ModelAdmin):
    """
    Admin configuration for Move model.
    """
    list_display = [
        'user', 'move_date', 'current_location', 'destination_location',
        'from_property_type', 'to_property_type', 'current_floor_map_preview', 
        'new_floor_map_preview', 'status', 'progress', 'created_at'
    ]
    list_filter = ['status', 'from_property_type', 'to_property_type', 'discount_type', 'move_date', 'created_at']
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'current_location', 'destination_location', 'first_name', 'last_name'
    ]
    readonly_fields = ['id', 'created_at', 'updated_at', 'progress']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'move_date', 'status', 'progress')
        }),
        ('Locations', {
            'fields': ('current_location', 'destination_location')
        }),
        ('Property Details', {
            'fields': ('from_property_type', 'to_property_type', 'current_property_floor_map', 'new_property_floor_map', 'special_items', 'additional_details')
        }),
        ('Discount Information', {
            'fields': ('discount_type', 'discount_percentage')
        }),
        ('Contact Information', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request).select_related('user')
        # Filter out any invalid references that might cause DoesNotExist errors
        return qs
    
    def current_floor_map_preview(self, obj):
        """Display current property floor map preview."""
        if obj and obj.current_property_floor_map:
            try:
                return f'<img src="{obj.current_property_floor_map.url}" width="50" height="50" style="object-fit: cover;" />'
            except (ValueError, AttributeError):
                return "No image"
        return "No image"
    current_floor_map_preview.allow_tags = True
    current_floor_map_preview.short_description = "Current Floor Map"
    
    def new_floor_map_preview(self, obj):
        """Display new property floor map preview."""
        if obj and obj.new_property_floor_map:
            try:
                return f'<img src="{obj.new_property_floor_map.url}" width="50" height="50" style="object-fit: cover;" />'
            except (ValueError, AttributeError):
                return "No image"
        return "No image"
    new_floor_map_preview.allow_tags = True
    new_floor_map_preview.short_description = "New Floor Map"
    
    def changelist_view(self, request, extra_context=None):
        """Override changelist_view to handle DoesNotExist errors gracefully."""
        try:
            return super().changelist_view(request, extra_context)
        except Exception as e:
            # If there's a DoesNotExist error, it might be from a filter or action
            # Clear any problematic query parameters and redirect
            from django.contrib import messages
            from django.shortcuts import redirect
            from django.urls import reverse
            from django.core.exceptions import ObjectDoesNotExist
            
            # Check if it's a DoesNotExist error
            if isinstance(e, ObjectDoesNotExist) or 'DoesNotExist' in str(type(e)):
                messages.error(request, "The requested move no longer exists. The page has been refreshed.")
            else:
                messages.error(request, f"An error occurred: {str(e)}. Please try again.")
            
            # Redirect to clean changelist without query parameters
            return redirect(reverse('admin:moves_move_changelist'))


@admin.register(MoveCollaborator)
class MoveCollaboratorAdmin(admin.ModelAdmin):
    """
    Admin configuration for MoveCollaborator model.
    """
    list_display = [
        'move', 'email', 'first_name', 'last_name', 'role', 'permissions', 
        'is_active', 'invited_at', 'accepted_at'
    ]
    list_filter = ['role', 'permissions', 'is_active', 'invited_at', 'accepted_at']
    search_fields = [
        'move__user__email', 'email', 'first_name', 'last_name', 
        'move__current_location', 'move__destination_location'
    ]
    readonly_fields = ['id', 'invited_at', 'invitation_token']
    ordering = ['-invited_at']
    
    fieldsets = (
        ('Collaborator Information', {
            'fields': ('move', 'email', 'first_name', 'last_name', 'role', 'permissions')
        }),
        ('Invitation Status', {
            'fields': ('is_active', 'invited_at', 'accepted_at', 'invitation_token')
        }),
        ('User Account', {
            'fields': ('user',),
            'description': 'Link to user account if they have one'
        }),
    )


@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    """
    Admin configuration for TaskAssignment model.
    """
    list_display = [
        'timeline_event', 'collaborator', 'assigned_by', 'assigned_at'
    ]
    list_filter = ['assigned_at', 'timeline_event__move__user']
    search_fields = [
        'timeline_event__title', 'collaborator__first_name', 'collaborator__last_name',
        'assigned_by__first_name', 'assigned_by__last_name'
    ]
    readonly_fields = ['id', 'assigned_at']
    ordering = ['-assigned_at']
    
    fieldsets = (
        ('Assignment Details', {
            'fields': ('timeline_event', 'collaborator', 'assigned_by', 'assigned_at')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )
