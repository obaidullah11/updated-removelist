"""
Models for service booking marketplace.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from apps.moves.models import Move
from apps.common.utils import ChoicesMixin
from apps.common.validators import validate_image_file

User = get_user_model()


class ServiceProvider(models.Model, ChoicesMixin):
    """
    Model representing a service provider in the marketplace.
    """
    
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Provider details
    name = models.CharField(max_length=200)
    description = models.TextField()
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    website = models.URLField(blank=True, null=True)
    
    # Business details
    abn = models.CharField(max_length=20, blank=True, null=True)
    business_address = models.TextField()
    service_areas = models.JSONField(default=list)  # List of areas they service
    
    # Verification
    verification_status = models.CharField(
        max_length=20, 
        choices=VERIFICATION_STATUS_CHOICES, 
        default='pending'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Rating and reviews
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    review_count = models.IntegerField(default=0)
    
    # Features and certifications
    features = models.JSONField(default=list)  # e.g., ["Insured", "Licensed", "Same-day service"]
    certifications = models.JSONField(default=list)
    
    # Availability
    availability = models.CharField(max_length=100, default="Mon-Sat 7AM-6PM")
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'service_providers'
        verbose_name = 'Service Provider'
        verbose_name_plural = 'Service Providers'
        ordering = ['-rating', 'name']
    
    def __str__(self):
        return self.name
    
    def update_rating(self):
        """Update provider's rating based on reviews."""
        from django.db.models import Avg
        avg_rating = self.reviews.aggregate(avg_rating=Avg('rating'))['avg_rating']
        if avg_rating:
            self.rating = round(avg_rating, 2)
            self.review_count = self.reviews.count()
            self.save(update_fields=['rating', 'review_count'])


class Service(models.Model, ChoicesMixin):
    """
    Model representing a service offered by providers.
    """
    
    CATEGORY_CHOICES = [
        ('movers', 'Removalists (Movers)'),
        ('hire_van', 'Hire a Van/Truck'),
        ('cleaning', 'Cleaners'),
        ('packing', 'Packing'),
        ('unpacking', 'Unpacking'),
        ('rubbish_removal', 'Rubbish Removals'),
        ('gardening', 'Gardening'),
        ('pest_control', 'Pest Control'),
        ('skip_bins', 'Skip Bins'),
        ('handyman', 'Handyman'),
        ('tradie', 'Tradie (Plumber/Electrician)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name='services')
    
    # Service details
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    
    # Pricing
    price_from = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_unit = models.CharField(max_length=20, default='hour')  # hour, job, item, etc.
    
    # Service specifics
    features = models.JSONField(default=list)
    requirements = models.JSONField(default=list)
    
    # Images
    images = models.JSONField(default=list)  # List of image URLs/paths
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'services'
        verbose_name = 'Service'
        verbose_name_plural = 'Services'
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.provider.name}"


class ServiceBooking(models.Model, ChoicesMixin):
    """
    Model representing a service booking request.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ]
    
    TIME_PREFERENCE_CHOICES = [
        ('morning', 'Morning (8AM-12PM)'),
        ('afternoon', 'Afternoon (12PM-5PM)'),
        ('evening', 'Evening (5PM-8PM)'),
        ('flexible', 'Flexible'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    move = models.ForeignKey(Move, on_delete=models.CASCADE, related_name='service_bookings')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='bookings')
    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name='bookings')
    
    # Booking details
    preferred_date = models.DateField()
    preferred_time = models.CharField(max_length=20, choices=TIME_PREFERENCE_CHOICES, default='flexible')
    notes = models.TextField(blank=True, null=True)
    
    # Property access information (for movers)
    property_access = models.JSONField(default=dict, blank=True)
    
    # Booking status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    confirmed_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    
    # Pricing
    quoted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Provider response
    provider_notes = models.TextField(blank=True, null=True)
    provider_response_date = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'service_bookings'
        verbose_name = 'Service Booking'
        verbose_name_plural = 'Service Bookings'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Booking: {self.service.name} for {self.move.user.email}"


class ServiceReview(models.Model):
    """
    Model representing a review for a service provider.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(ServiceBooking, on_delete=models.CASCADE, related_name='review')
    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='service_reviews')
    
    # Review details
    rating = models.IntegerField()  # 1-5 stars
    title = models.CharField(max_length=200, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    
    # Review categories
    punctuality_rating = models.IntegerField(null=True, blank=True)  # 1-5
    quality_rating = models.IntegerField(null=True, blank=True)  # 1-5
    communication_rating = models.IntegerField(null=True, blank=True)  # 1-5
    value_rating = models.IntegerField(null=True, blank=True)  # 1-5
    
    # Status
    is_verified = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'service_reviews'
        verbose_name = 'Service Review'
        verbose_name_plural = 'Service Reviews'
        ordering = ['-created_at']
        unique_together = ['booking', 'user']
    
    def __str__(self):
        return f"Review for {self.provider.name} - {self.rating} stars"
    
    def save(self, *args, **kwargs):
        """Update provider rating when review is saved."""
        super().save(*args, **kwargs)
        self.provider.update_rating()


class ServiceQuote(models.Model):
    """
    Model representing a quote from a service provider.
    """
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(ServiceBooking, on_delete=models.CASCADE, related_name='quotes')
    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name='quotes')
    
    # Quote details
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    breakdown = models.JSONField(default=dict)  # Detailed price breakdown
    notes = models.TextField(blank=True, null=True)
    
    # Terms
    valid_until = models.DateTimeField()
    terms_conditions = models.TextField(blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'service_quotes'
        verbose_name = 'Service Quote'
        verbose_name_plural = 'Service Quotes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Quote for {self.booking} - ${self.total_price}"

