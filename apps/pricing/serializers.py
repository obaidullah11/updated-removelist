"""
Serializers for pricing and subscription management.
"""
from rest_framework import serializers
from django.utils import timezone
from .models import PricingPlan, UserSubscription, PaymentHistory, DiscountCode, DiscountUsage
from django.contrib.auth import get_user_model

User = get_user_model()


class PricingPlanSerializer(serializers.ModelSerializer):
    """
    Serializer for pricing plan details.
    """
    calculated_price_monthly = serializers.SerializerMethodField()
    calculated_price_yearly = serializers.SerializerMethodField()
    
    class Meta:
        model = PricingPlan
        fields = [
            'id', 'name', 'plan_type', 'description', 'price_monthly', 'price_yearly',
            'calculated_price_monthly', 'calculated_price_yearly', 'features', 
            'date_changes_allowed', 'is_popular', 'is_active'
        ]
        read_only_fields = ['id', 'calculated_price_monthly', 'calculated_price_yearly']
    
    def get_calculated_price_monthly(self, obj):
        """Get calculated monthly price based on context."""
        context = self.context.get('pricing_context', {})
        return obj.calculate_price(
            billing_cycle='monthly',
            location=context.get('location'),
            timeline=context.get('timeline'),
            move_type=context.get('move_type')
        )
    
    def get_calculated_price_yearly(self, obj):
        """Get calculated yearly price based on context."""
        context = self.context.get('pricing_context', {})
        return obj.calculate_price(
            billing_cycle='yearly',
            location=context.get('location'),
            timeline=context.get('timeline'),
            move_type=context.get('move_type')
        )


class UserSubscriptionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a user subscription.
    """
    plan_id = serializers.UUIDField(write_only=True)
    discount_code = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = UserSubscription
        fields = [
            'plan_id', 'billing_cycle', 'discount_code', 'auto_renew'
        ]
    
    def validate_plan_id(self, value):
        """Validate that the plan exists and is active."""
        try:
            plan = PricingPlan.objects.get(id=value, is_active=True)
            return plan
        except PricingPlan.DoesNotExist:
            raise serializers.ValidationError("Pricing plan not found or not active")
    
    def validate_billing_cycle(self, value):
        """Validate billing cycle choice."""
        valid_choices = [choice[0] for choice in UserSubscription.BILLING_CYCLE_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid billing cycle. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate_discount_code(self, value):
        """Validate discount code if provided."""
        if value:
            try:
                discount = DiscountCode.objects.get(code=value.upper())
                user = self.context['request'].user
                if not discount.is_valid_for_user(user):
                    raise serializers.ValidationError("Discount code is not valid or has expired")
                return discount
            except DiscountCode.DoesNotExist:
                raise serializers.ValidationError("Invalid discount code")
        return None
    
    def create(self, validated_data):
        """Create a user subscription."""
        plan = validated_data.pop('plan_id')
        discount_code = validated_data.pop('discount_code', None)
        user = self.context['request'].user
        
        # Calculate price
        billing_cycle = validated_data['billing_cycle']
        price = plan.calculate_price(billing_cycle=billing_cycle)
        
        # Apply discount if provided
        discount_amount = 0
        if discount_code:
            discount_amount = discount_code.calculate_discount(price)
            price -= discount_amount
        
        # Set subscription dates
        start_date = timezone.now()
        if billing_cycle == 'monthly':
            from datetime import timedelta
            end_date = start_date + timedelta(days=30)
            next_billing_date = end_date
        else:  # yearly
            from datetime import timedelta
            end_date = start_date + timedelta(days=365)
            next_billing_date = end_date
        
        # Create subscription
        subscription = UserSubscription.objects.create(
            user=user,
            plan=plan,
            price_paid=price,
            start_date=start_date,
            end_date=end_date,
            next_billing_date=next_billing_date,
            **validated_data
        )
        
        # Record discount usage if applicable
        if discount_code:
            DiscountUsage.objects.create(
                discount_code=discount_code,
                user=user,
                subscription=subscription,
                discount_amount=discount_amount,
                original_amount=price + discount_amount,
                final_amount=price
            )
            
            # Update discount code usage count
            discount_code.current_uses += 1
            discount_code.save()
        
        return subscription


class UserSubscriptionDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for user subscription details.
    """
    plan = PricingPlanSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    billing_cycle_display = serializers.CharField(source='get_billing_cycle_display', read_only=True)
    is_active_subscription = serializers.BooleanField(source='is_active', read_only=True)
    days_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSubscription
        fields = [
            'id', 'plan', 'billing_cycle', 'billing_cycle_display', 'price_paid',
            'start_date', 'end_date', 'next_billing_date', 'status', 'status_display',
            'auto_renew', 'is_active_subscription', 'days_remaining', 'created_at'
        ]
        read_only_fields = [
            'id', 'plan', 'price_paid', 'start_date', 'end_date', 'next_billing_date',
            'status_display', 'billing_cycle_display', 'is_active_subscription',
            'days_remaining', 'created_at'
        ]
    
    def get_days_remaining(self, obj):
        """Get days remaining in subscription."""
        if obj.is_active:
            return (obj.end_date.date() - timezone.now().date()).days
        return 0


class PaymentHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for payment history.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    plan_name = serializers.CharField(source='subscription.plan.name', read_only=True)
    
    class Meta:
        model = PaymentHistory
        fields = [
            'id', 'amount', 'currency', 'status', 'status_display',
            'plan_name', 'billing_period_start', 'billing_period_end',
            'created_at'
        ]
        read_only_fields = [
            'id', 'status_display', 'plan_name', 'created_at'
        ]


class DiscountCodeValidationSerializer(serializers.Serializer):
    """
    Serializer for validating discount codes.
    """
    code = serializers.CharField(max_length=50)
    plan_id = serializers.UUIDField(required=False)
    
    def validate_code(self, value):
        """Validate discount code exists."""
        try:
            discount = DiscountCode.objects.get(code=value.upper(), is_active=True)
            return discount
        except DiscountCode.DoesNotExist:
            raise serializers.ValidationError("Invalid discount code")
    
    def validate_plan_id(self, value):
        """Validate plan exists if provided."""
        if value:
            try:
                plan = PricingPlan.objects.get(id=value, is_active=True)
                return plan
            except PricingPlan.DoesNotExist:
                raise serializers.ValidationError("Invalid plan")
        return None
    
    def validate(self, attrs):
        """Validate discount code is valid for user and plan."""
        discount_code = attrs['code']
        plan = attrs.get('plan_id')
        user = self.context['request'].user
        
        # Check if valid for user
        if not discount_code.is_valid_for_user(user):
            raise serializers.ValidationError({'code': 'Discount code is not valid or has expired'})
        
        # Check if applicable to plan
        if plan and discount_code.applicable_plans.exists():
            if not discount_code.applicable_plans.filter(id=plan.id).exists():
                raise serializers.ValidationError({'code': 'Discount code is not applicable to this plan'})
        
        return attrs


class DiscountCodeDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for discount code details (for validation response).
    """
    discount_type_display = serializers.CharField(source='get_discount_type_display', read_only=True)
    
    class Meta:
        model = DiscountCode
        fields = [
            'id', 'code', 'description', 'discount_type', 'discount_type_display',
            'discount_value', 'max_discount_amount', 'valid_until'
        ]
        read_only_fields = ['id', 'discount_type_display']


class DiscountUsageSerializer(serializers.ModelSerializer):
    """
    Serializer for discount usage history.
    """
    discount_code_name = serializers.CharField(source='discount_code.code', read_only=True)
    plan_name = serializers.CharField(source='subscription.plan.name', read_only=True)
    
    class Meta:
        model = DiscountUsage
        fields = [
            'id', 'discount_code_name', 'plan_name', 'discount_amount',
            'original_amount', 'final_amount', 'created_at'
        ]
        read_only_fields = [
            'id', 'discount_code_name', 'plan_name', 'created_at'
        ]

