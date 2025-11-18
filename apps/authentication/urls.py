"""
URL patterns for authentication endpoints.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Authentication endpoints
    path('register/email/', views.register_email, name='register_email'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('refresh/', views.refresh_token, name='refresh_token'),
    
    # Email verification
    path('verify-email/', views.verify_email, name='verify_email'),
    path('resend-email/', views.resend_email, name='resend_email'),
    
    # Password management
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Profile management
    path('profile/', views.profile, name='profile'),
    path('profile/', views.update_profile, name='update_profile'),  # Same URL, different methods
    path('profile/avatar/', views.upload_avatar, name='upload_avatar'),
    
    # User management (Admin only)
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<uuid:user_id>/', views.user_detail, name='user_detail'),
    path('users/<uuid:user_id>/update/', views.user_update, name='user_update'),
    path('users/<uuid:user_id>/delete/', views.user_delete, name='user_delete'),
    path('users/<uuid:user_id>/reset-password/', views.user_reset_password, name='user_reset_password'),
    path('users/<uuid:user_id>/toggle-status/', views.user_toggle_status, name='user_toggle_status'),
]
