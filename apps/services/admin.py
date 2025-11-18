"""
Admin configuration for service booking marketplace.
"""
from django.contrib import admin
from .models import ServiceProvider, Service, ServiceBooking, ServiceReview, ServiceQuote


@admin.register(ServiceProvider)
class ServiceProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'verification_status', 'rating', 'review_count', 'is_active', 'created_at']
    list_filter = ['verification_status', 'is_active', 'created_at']
    search_fields = ['name', 'email', 'business_address']
    readonly_fields = ['id', 'rating', 'review_count', 'verified_at', 'created_at', 'updated_at']
    ordering = ['-rating', 'name']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'category', 'price_from', 'price_unit', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'provider__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['category', 'name']


@admin.register(ServiceBooking)
class ServiceBookingAdmin(admin.ModelAdmin):
    list_display = ['service', 'provider', 'move', 'preferred_date', 'status', 'quoted_price', 'created_at']
    list_filter = ['status', 'preferred_date', 'created_at']
    search_fields = ['service__name', 'provider__name', 'move__user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(ServiceReview)
class ServiceReviewAdmin(admin.ModelAdmin):
    list_display = ['provider', 'user', 'rating', 'is_verified', 'is_public', 'created_at']
    list_filter = ['rating', 'is_verified', 'is_public', 'created_at']
    search_fields = ['provider__name', 'user__email', 'title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(ServiceQuote)
class ServiceQuoteAdmin(admin.ModelAdmin):
    list_display = ['booking', 'provider', 'total_price', 'status', 'valid_until', 'created_at']
    list_filter = ['status', 'valid_until', 'created_at']
    search_fields = ['booking__service__name', 'provider__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']

