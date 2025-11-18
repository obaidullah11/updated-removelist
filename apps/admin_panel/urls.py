"""
URL patterns for admin panel APIs.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard APIs
    path('dashboard/metrics/', views.dashboard_metrics, name='admin_dashboard_metrics'),
    path('dashboard/analytics/', views.dashboard_analytics, name='admin_dashboard_analytics'),
    
    # User Management APIs
    path('users/', views.admin_users_list, name='admin_users_list'),
    path('users/<uuid:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('users/<uuid:user_id>/status/', views.admin_user_status, name='admin_user_status'),
    
    # Booking Management APIs
    path('bookings/', views.admin_bookings_list, name='admin_bookings_list'),
    path('bookings/<uuid:booking_id>/', views.admin_booking_detail, name='admin_booking_detail'),
    
    # Partner Management APIs
    path('partners/', views.admin_partners_list, name='admin_partners_list'),
    path('partners/<uuid:partner_id>/', views.admin_partner_detail, name='admin_partner_detail'),
    path('partners/<uuid:partner_id>/approve/', views.admin_partner_approve, name='admin_partner_approve'),
    path('partners/<uuid:partner_id>/reject/', views.admin_partner_reject, name='admin_partner_reject'),
    
    # Notifications APIs
    path('notifications/', views.admin_notifications_list, name='admin_notifications_list'),
    path('notifications/<uuid:notification_id>/read/', views.admin_notification_mark_read, name='admin_notification_mark_read'),
    path('notifications/mark-all-read/', views.admin_notifications_mark_all_read, name='admin_notifications_mark_all_read'),
    path('notifications/<uuid:notification_id>/delete/', views.admin_notification_delete, name='admin_notification_delete'),
]





