"""
URL configuration for inventory app.
"""
from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Floor plan analysis service (no auth required)
    path('analyze-floor-plan/', views.analyze_floor_plan_service, name='analyze_floor_plan_service'),
    path('service-info/', views.floor_plan_service_info, name='floor_plan_service_info'),
    
    # AI-powered floor plan analysis (requires authentication)
    path('analyze-floor-plan-ai/', views.analyze_floor_plan_with_ai, name='analyze_floor_plan_with_ai'),
    
    # Inventory Rooms
    path('rooms/', views.get_rooms, name='get_rooms'),
    path('rooms/create/', views.create_room, name='create_room'),
    path('rooms/<uuid:room_id>/', views.get_room, name='get_room'),
    path('rooms/<uuid:room_id>/update/', views.update_room, name='update_room'),
    path('rooms/<uuid:room_id>/packed/', views.mark_room_packed, name='mark_room_packed'),
    path('rooms/<uuid:room_id>/delete/', views.delete_room, name='delete_room'),
    
    # Inventory Boxes
    path('boxes/', views.get_boxes, name='get_boxes'),
    path('boxes/create/', views.create_box, name='create_box'),
    path('boxes/<uuid:box_id>/', views.get_box, name='get_box'),
    path('boxes/<uuid:box_id>/update/', views.update_box, name='update_box'),
    path('boxes/<uuid:box_id>/packed/', views.mark_box_packed, name='mark_box_packed'),
    path('boxes/<uuid:box_id>/delete/', views.delete_box, name='delete_box'),
    
    # Heavy Items
    path('heavy-items/', views.get_heavy_items, name='get_heavy_items'),
    path('heavy-items/create/', views.create_heavy_item, name='create_heavy_item'),
    path('heavy-items/<uuid:item_id>/', views.get_heavy_item, name='get_heavy_item'),
    path('heavy-items/<uuid:item_id>/update/', views.update_heavy_item, name='update_heavy_item'),
    path('heavy-items/<uuid:item_id>/delete/', views.delete_heavy_item, name='delete_heavy_item'),
    
    # High Value Items
    path('high-value-items/', views.get_high_value_items, name='get_high_value_items'),
    path('high-value-items/create/', views.create_high_value_item, name='create_high_value_item'),
    path('high-value-items/<uuid:item_id>/', views.get_high_value_item, name='get_high_value_item'),
    path('high-value-items/<uuid:item_id>/update/', views.update_high_value_item, name='update_high_value_item'),
    path('high-value-items/<uuid:item_id>/delete/', views.delete_high_value_item, name='delete_high_value_item'),
    
    # Storage Items
    path('storage-items/', views.get_storage_items, name='get_storage_items'),
    path('storage-items/create/', views.create_storage_item, name='create_storage_item'),
    path('storage-items/<uuid:item_id>/', views.get_storage_item, name='get_storage_item'),
    path('storage-items/<uuid:item_id>/update/', views.update_storage_item, name='update_storage_item'),
    path('storage-items/<uuid:item_id>/delete/', views.delete_storage_item, name='delete_storage_item'),
    
    # Inventory Items
    path('items/', views.get_items, name='get_items'),
    path('items/create/', views.create_item, name='create_item'),
    path('items/<uuid:item_id>/', views.get_item, name='get_item'),
    path('items/<uuid:item_id>/update/', views.update_item, name='update_item'),
    path('items/<uuid:item_id>/checked/', views.toggle_item_checked, name='toggle_item_checked'),
    path('items/<uuid:item_id>/delete/', views.delete_item, name='delete_item'),
]