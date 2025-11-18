"""
Models for pricing and subscription management.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from apps.common.utils import ChoicesMixin

User = get_user_model()


class PricingPlan(models.Model, ChoicesMixin):
    """
    Model representing pricing plans.
    """
    
    PLAN_TYPE_CHOICES = [
        ('free', 'Free'),
        ('plus', 'Plan +'),
        ('concierge', 'Concierge +'),
    ]
    
    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Plan details
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES, unique=True)
    description = models.TextField()
    
    # Pricing
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Features
    features = models.JSONField(default=list)  # List of features
    date_changes_allowed = models.IntegerField(default=0)  # -1 for unlimited
    
    # Location-based pricing
    location_multipliers = models.JSONField(default=dict)  # {"sydney": 1.2, "melbourne": 1.1}
    
    # Timeline-based pricing
    timeline_multipliers = models.JSONField(default=dict)  # {"urgent": 1.5, "standard": 1.0}
    
    # Move type multipliers
    move_type_multipliers = models.JSONField(default=dict)  # {"interstate": 1.3, "local": 1.0}
    
    # Status
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pricing_plans'
        verbose_name = 'Pricing Plan'
        verbose_name_plural = 'Pricing Plans'
        ordering = ['price_monthly']
    
    def __str__(self):
        return self.name
    
    def calculate_price(self, billing_cycle='monthly', location=None, timeline=None, move_type=None):
        """Calculate price based on various factors."""
        base_price = self.price_monthly if billing_cycle == 'monthly' else self.price_yearly
        
        # Apply location multiplier
        if location and location.lower() in self.location_multipliers:
            base_price *= self.location_multipliers[location.lower()]
        
        # Apply timeline multiplier
        if timeline and timeline.lower() in self.timeline_multipliers:
            base_price *= self.timeline_multipliers[timeline.lower()]
        
        # Apply move type multiplier
        if move_type and move_type.lower() in self.move_type_multipliers:
            base_price *= self.move_type_multipliers[move_type.lower()]
        
        return round(base_price, 2)


class UserSubscription(models.Model, ChoicesMixin):
    """
    Model representing user subscriptions.
    """
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('pending', 'Pending'),
    ]
    
    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(PricingPlan, on_delete=models.PROTECT, related_name='subscriptions')
    
    # Subscription details
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default='monthly')
    price_paid = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Dates
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    next_billing_date = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    auto_renew = models.BooleanField(default=True)
    
    # Payment details
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_subscriptions'
        verbose_name = 'User Subscription'
        verbose_name_plural = 'User Subscriptions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.plan.name}"
    
    def save(self, *args, **kwargs):
        """Update user's pricing plan when subscription is saved."""
        super().save(*args, **kwargs)
        if self.status == 'active':
            self.user.pricing_plan = self.plan.plan_type
            self.user.save(update_fields=['pricing_plan'])
    
    @property
    def is_active(self):
        """Check if subscription is currently active."""
        from django.utils import timezone
        return (
            self.status == 'active' and 
            self.start_date <= timezone.now() <= self.end_date
        )
    
    def cancel(self):
        """Cancel the subscription."""
        self.status = 'cancelled'
        self.auto_renew = False
        self.save()


class PaymentHistory(models.Model):
    """
    Model for tracking payment history.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, related_name='payments')
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='AUD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Stripe details
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_charge_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Billing period
    billing_period_start = models.DateTimeField()
    billing_period_end = models.DateTimeField()
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_history'
        verbose_name = 'Payment History'
        verbose_name_plural = 'Payment History'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment ${self.amount} - {self.subscription.user.email}"


class DiscountCode(models.Model):
    """
    Model for discount codes and promotions.
    """
    
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Code details
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    
    # Discount details
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Usage limits
    max_uses = models.IntegerField(null=True, blank=True)  # None for unlimited
    max_uses_per_user = models.IntegerField(default=1)
    current_uses = models.IntegerField(default=0)
    
    # Validity
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    
    # Applicable plans
    applicable_plans = models.ManyToManyField(PricingPlan, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'discount_codes'
        verbose_name = 'Discount Code'
        verbose_name_plural = 'Discount Codes'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.code
    
    def calculate_discount(self, amount):
        """Calculate discount amount for given price."""
        if self.discount_type == 'percentage':
            discount = amount * (self.discount_value / 100)
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
        else:  # fixed
            discount = self.discount_value
        
        return min(discount, amount)  # Don't exceed the original amount
    
    def is_valid_for_user(self, user):
        """Check if discount code is valid for a specific user."""
        from django.utils import timezone
        
        # Check if code is active and within validity period
        if not self.is_active or timezone.now() < self.valid_from or timezone.now() > self.valid_until:
            return False
        
        # Check usage limits
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
        
        # Check per-user usage limit
        user_usage = DiscountUsage.objects.filter(discount_code=self, user=user).count()
        if user_usage >= self.max_uses_per_user:
            return False
        
        return True


class DiscountUsage(models.Model):
    """
    Model to track discount code usage.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    discount_code = models.ForeignKey(DiscountCode, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discount_usages')
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, related_name='discount_usages')
    
    # Usage details
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    original_amount = models.DecimalField(max_digits=10, decimal_places=2)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'discount_usage'
        verbose_name = 'Discount Usage'
        verbose_name_plural = 'Discount Usage'
        ordering = ['-created_at']
        unique_together = ['discount_code', 'user', 'subscription']
    
    def __str__(self):
        return f"{self.discount_code.code} used by {self.user.email}"

