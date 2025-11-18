"""
URL patterns for service booking marketplace endpoints.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Service endpoints
    path('', views.get_services, name='get_services'),
    path('<uuid:service_id>/', views.get_service, name='get_service'),
    path('categories/', views.get_service_categories, name='get_service_categories'),
    
    # Service booking endpoints
    path('bookings/', views.get_service_bookings, name='get_service_bookings'),
    path('bookings/create/', views.create_service_booking, name='create_service_booking'),
    path('bookings/<uuid:booking_id>/', views.get_service_booking, name='get_service_booking'),
    path('bookings/<uuid:booking_id>/update/', views.update_service_booking, name='update_service_booking'),
    path('bookings/<uuid:booking_id>/cancel/', views.cancel_service_booking, name='cancel_service_booking'),
    
    # Service review endpoints
    path('reviews/', views.get_service_reviews, name='get_service_reviews'),
    path('reviews/create/', views.create_service_review, name='create_service_review'),
    path('reviews/<uuid:review_id>/', views.get_service_review, name='get_service_review'),
    path('reviews/<uuid:review_id>/update/', views.update_service_review, name='update_service_review'),
    path('reviews/<uuid:review_id>/delete/', views.delete_service_review, name='delete_service_review'),
    
    # Service quote endpoints
    path('quotes/', views.get_service_quotes, name='get_service_quotes'),
    path('quotes/<uuid:quote_id>/', views.get_service_quote, name='get_service_quote'),
]

