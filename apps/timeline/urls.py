"""
URL patterns for timeline and task management endpoints.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Timeline events
    path('events/', views.get_timeline_events, name='get_timeline_events'),
    path('events/<uuid:event_id>/', views.update_timeline_event, name='update_timeline_event'),
    
    # Checklist items (also accessible via /api/checklist/)
    path('items/', views.get_checklist_items, name='get_checklist_items'),
    path('items/<uuid:item_id>/', views.update_checklist_item, name='update_checklist_item'),
    path('items/', views.add_custom_task, name='add_custom_task'),  # Same URL, different methods
    path('items/<uuid:item_id>/', views.delete_custom_task, name='delete_custom_task'),  # Same URL, different methods
]
