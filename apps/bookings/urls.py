"""
URL patterns for booking and scheduling endpoints.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('slots/', views.available_slots, name='available_slots'),
    path('book/', views.book_slot, name='book_slot'),
    path('user-bookings/', views.user_bookings, name='user_bookings'),
    path('<uuid:booking_id>/', views.booking_detail, name='booking_detail'),
    path('<uuid:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
]
