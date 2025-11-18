"""
Admin configuration for pricing and subscription management.
"""
from django.contrib import admin
from .models import PricingPlan, UserSubscription, PaymentHistory, DiscountCode, DiscountUsage


@admin.register(PricingPlan)
class PricingPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'price_monthly', 'price_yearly', 'date_changes_allowed', 'is_active', 'is_popular']
    list_filter = ['plan_type', 'is_active', 'is_popular']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['price_monthly']


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'billing_cycle', 'status', 'start_date', 'end_date', 'price_paid']
    list_filter = ['status', 'billing_cycle', 'plan', 'auto_renew']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'amount', 'currency', 'status', 'billing_period_start', 'created_at']
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['subscription__user__email', 'stripe_payment_intent_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'current_uses', 'max_uses', 'valid_until', 'is_active']
    list_filter = ['discount_type', 'is_active', 'valid_from', 'valid_until']
    search_fields = ['code', 'description']
    readonly_fields = ['id', 'current_uses', 'created_at', 'updated_at']
    ordering = ['-created_at']
    filter_horizontal = ['applicable_plans']


@admin.register(DiscountUsage)
class DiscountUsageAdmin(admin.ModelAdmin):
    list_display = ['discount_code', 'user', 'subscription', 'discount_amount', 'final_amount', 'created_at']
    list_filter = ['created_at']
    search_fields = ['discount_code__code', 'user__email']
    readonly_fields = ['id', 'created_at']
    ordering = ['-created_at']

