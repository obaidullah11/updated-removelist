"""
URL patterns for pricing and subscription management endpoints.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Pricing plan endpoints
    path('plans/', views.get_pricing_plans, name='get_pricing_plans'),
    path('plans/<uuid:plan_id>/', views.get_pricing_plan, name='get_pricing_plan'),
    
    # Subscription endpoints
    path('subscription/', views.get_user_subscription, name='get_user_subscription'),
    path('subscription/create/', views.create_subscription, name='create_subscription'),
    path('subscription/update/', views.update_subscription, name='update_subscription'),
    path('subscription/cancel/', views.cancel_subscription, name='cancel_subscription'),
    
    # Payment history endpoints
    path('payments/', views.get_payment_history, name='get_payment_history'),
    
    # Discount code endpoints
    path('discount/validate/', views.validate_discount_code, name='validate_discount_code'),
    path('discount/usage/', views.get_discount_usage_history, name='get_discount_usage_history'),
    
    # User plan information
    path('user/plan-info/', views.get_user_plan_info, name='get_user_plan_info'),
]

