"""
Views for pricing and subscription management.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import PricingPlan, UserSubscription, PaymentHistory, DiscountCode
from .serializers import (
    PricingPlanSerializer, UserSubscriptionCreateSerializer, UserSubscriptionDetailSerializer,
    PaymentHistorySerializer, DiscountCodeValidationSerializer, DiscountCodeDetailSerializer,
    DiscountUsageSerializer
)
from apps.common.utils import success_response, error_response, paginated_response


@api_view(['GET'])
def get_pricing_plans(request):
    """
    Get all active pricing plans with optional context-based pricing.
    """
    # Get pricing context from query parameters
    location = request.GET.get('location')
    timeline = request.GET.get('timeline')
    move_type = request.GET.get('move_type')
    
    pricing_context = {
        'location': location,
        'timeline': timeline,
        'move_type': move_type
    }
    
    plans = PricingPlan.objects.filter(is_active=True).order_by('price_monthly')
    
    serializer = PricingPlanSerializer(
        plans, 
        many=True, 
        context={'pricing_context': pricing_context}
    )
    
    return success_response(
        "Pricing plans retrieved successfully",
        serializer.data
    )


@api_view(['GET'])
def get_pricing_plan(request, plan_id):
    """
    Get pricing plan details by ID.
    """
    plan = get_object_or_404(PricingPlan, id=plan_id, is_active=True)
    
    # Get pricing context from query parameters
    location = request.GET.get('location')
    timeline = request.GET.get('timeline')
    move_type = request.GET.get('move_type')
    
    pricing_context = {
        'location': location,
        'timeline': timeline,
        'move_type': move_type
    }
    
    serializer = PricingPlanSerializer(plan, context={'pricing_context': pricing_context})
    
    return success_response(
        "Pricing plan details retrieved",
        serializer.data
    )


# ============= SUBSCRIPTION VIEWS =============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_subscription(request):
    """
    Get user's current subscription.
    """
    try:
        subscription = UserSubscription.objects.get(user=request.user)
        serializer = UserSubscriptionDetailSerializer(subscription)
        
        return success_response(
            "User subscription retrieved",
            serializer.data
        )
    except UserSubscription.DoesNotExist:
        return success_response(
            "No active subscription",
            None
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_subscription(request):
    """
    Create a new subscription for the user.
    """
    # Check if user already has an active subscription
    existing_subscription = UserSubscription.objects.filter(
        user=request.user, 
        status='active'
    ).first()
    
    if existing_subscription:
        return error_response(
            "Subscription already exists",
            {'detail': ['You already have an active subscription']},
            status.HTTP_400_BAD_REQUEST
        )
    
    serializer = UserSubscriptionCreateSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        subscription = serializer.save()
        
        # TODO: Process payment with Stripe here
        # payment_result = process_stripe_payment(subscription)
        # if payment_result.success:
        #     subscription.status = 'active'
        #     subscription.save()
        
        # For now, mark as active immediately (in production, this would be after successful payment)
        subscription.status = 'active'
        subscription.save()
        
        # Return subscription details
        detail_serializer = UserSubscriptionDetailSerializer(subscription)
        
        return success_response(
            "Subscription created successfully",
            detail_serializer.data,
            status.HTTP_201_CREATED
        )
    
    return error_response(
        "Subscription creation failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_subscription(request):
    """
    Update user's subscription settings.
    """
    try:
        subscription = UserSubscription.objects.get(user=request.user)
    except UserSubscription.DoesNotExist:
        return error_response(
            "No subscription found",
            {'detail': ['You do not have an active subscription']},
            status.HTTP_404_NOT_FOUND
        )
    
    # Only allow updating certain fields
    allowed_fields = ['auto_renew']
    update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
    
    for field, value in update_data.items():
        setattr(subscription, field, value)
    
    subscription.save()
    
    # Return updated subscription data
    detail_serializer = UserSubscriptionDetailSerializer(subscription)
    
    return success_response(
        "Subscription updated successfully",
        detail_serializer.data
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    """
    Cancel user's subscription.
    """
    try:
        subscription = UserSubscription.objects.get(user=request.user, status='active')
    except UserSubscription.DoesNotExist:
        return error_response(
            "No active subscription found",
            {'detail': ['You do not have an active subscription to cancel']},
            status.HTTP_404_NOT_FOUND
        )
    
    subscription.cancel()
    
    # TODO: Cancel Stripe subscription
    # cancel_stripe_subscription(subscription.stripe_subscription_id)
    
    return success_response("Subscription cancelled successfully")


# ============= PAYMENT HISTORY VIEWS =============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_payment_history(request):
    """
    Get user's payment history.
    """
    try:
        subscription = UserSubscription.objects.get(user=request.user)
        payments = PaymentHistory.objects.filter(subscription=subscription).order_by('-created_at')
        
        # Check if pagination is requested
        if request.GET.get('page'):
            return paginated_response(
                payments,
                PaymentHistorySerializer,
                request,
                "Payment history retrieved successfully"
            )
        
        # Return all payments without pagination
        serializer = PaymentHistorySerializer(payments, many=True)
        
        return success_response(
            "Payment history retrieved successfully",
            serializer.data
        )
    except UserSubscription.DoesNotExist:
        return success_response(
            "No payment history found",
            []
        )


# ============= DISCOUNT CODE VIEWS =============

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_discount_code(request):
    """
    Validate a discount code.
    """
    serializer = DiscountCodeValidationSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        discount_code = serializer.validated_data['code']
        plan = serializer.validated_data.get('plan_id')
        
        # Calculate discount amount if plan is provided
        discount_amount = 0
        if plan:
            base_price = plan.price_monthly  # Default to monthly
            discount_amount = discount_code.calculate_discount(base_price)
        
        # Return discount code details
        discount_serializer = DiscountCodeDetailSerializer(discount_code)
        response_data = discount_serializer.data
        response_data['discount_amount'] = discount_amount
        
        return success_response(
            "Discount code is valid",
            response_data
        )
    
    return error_response(
        "Invalid discount code",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_discount_usage_history(request):
    """
    Get user's discount code usage history.
    """
    from .models import DiscountUsage
    
    usages = DiscountUsage.objects.filter(user=request.user).order_by('-created_at')
    
    # Check if pagination is requested
    if request.GET.get('page'):
        return paginated_response(
            usages,
            DiscountUsageSerializer,
            request,
            "Discount usage history retrieved successfully"
        )
    
    # Return all usages without pagination
    serializer = DiscountUsageSerializer(usages, many=True)
    
    return success_response(
        "Discount usage history retrieved successfully",
        serializer.data
    )


# ============= USER PLAN INFORMATION =============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_plan_info(request):
    """
    Get user's current plan information and limits.
    """
    user = request.user
    
    plan_info = {
        'current_plan': user.pricing_plan,
        'date_changes_used': user.date_changes_used,
        'date_changes_remaining': user.get_remaining_date_changes(),
        'can_change_date': user.can_change_date(),
    }
    
    # Add subscription details if available
    try:
        subscription = UserSubscription.objects.get(user=user)
        subscription_serializer = UserSubscriptionDetailSerializer(subscription)
        plan_info['subscription'] = subscription_serializer.data
    except UserSubscription.DoesNotExist:
        plan_info['subscription'] = None
    
    return success_response(
        "User plan information retrieved",
        plan_info
    )

