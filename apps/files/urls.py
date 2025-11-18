"""
URL patterns for file upload and storage endpoints.
"""
from django.urls import path
from . import views

urlpatterns = [
    # File uploads
    path('floor-plans/', views.upload_floor_plan, name='upload_floor_plan'),
    path('documents/', views.upload_document, name='upload_document'),
    
    # File retrieval
    path('user-files/', views.get_user_files, name='get_user_files'),
    path('floor-plans/<uuid:file_id>/', views.get_floor_plan, name='get_floor_plan'),
    path('documents/<uuid:file_id>/', views.get_document, name='get_document'),
    
    # File deletion
    path('floor-plans/<uuid:file_id>/', views.delete_floor_plan, name='delete_floor_plan'),  # Same URL, different methods
    path('documents/<uuid:file_id>/', views.delete_document, name='delete_document'),  # Same URL, different methods
    path('<uuid:file_id>/', views.delete_file, name='delete_file'),  # Generic delete endpoint
]
