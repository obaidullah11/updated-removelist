"""
Serializers for service booking marketplace.
"""
from rest_framework import serializers
from django.utils import timezone
from .models import ServiceProvider, Service, ServiceBooking, ServiceReview, ServiceQuote
from apps.moves.models import Move


class ServiceProviderSerializer(serializers.ModelSerializer):
    """
    Serializer for service provider details.
    """
    verification_status_display = serializers.CharField(source='get_verification_status_display', read_only=True)
    
    class Meta:
        model = ServiceProvider
        fields = [
            'id', 'name', 'description', 'email', 'phone', 'website',
            'business_address', 'service_areas', 'verification_status',
            'verification_status_display', 'verified_at', 'rating', 'review_count',
            'features', 'certifications', 'availability', 'is_active'
        ]
        read_only_fields = [
            'id', 'verification_status_display', 'verified_at', 'rating', 'review_count'
        ]


class ServiceDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for service details.
    """
    provider = ServiceProviderSerializer(read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = Service
        fields = [
            'id', 'name', 'description', 'category', 'category_display',
            'price_from', 'price_unit', 'features', 'requirements',
            'images', 'is_active', 'provider', 'created_at'
        ]
        read_only_fields = ['id', 'category_display', 'provider', 'created_at']


class ServiceListSerializer(serializers.ModelSerializer):
    """
    Serializer for service list.
    """
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    provider_rating = serializers.DecimalField(source='provider.rating', max_digits=3, decimal_places=2, read_only=True)
    provider_verified = serializers.SerializerMethodField()
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = Service
        fields = [
            'id', 'name', 'description', 'category_display', 'price_from', 'price_unit',
            'provider_name', 'provider_rating', 'provider_verified', 'features'
        ]
        read_only_fields = [
            'id', 'category_display', 'provider_name', 'provider_rating', 'provider_verified'
        ]
    
    def get_provider_verified(self, obj):
        """Check if provider is verified."""
        return obj.provider.verification_status == 'verified'


class ServiceBookingCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a service booking.
    """
    move_id = serializers.UUIDField(write_only=True)
    service_id = serializers.UUIDField(write_only=True)
    provider_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = ServiceBooking
        fields = [
            'move_id', 'service_id', 'provider_id', 'preferred_date',
            'preferred_time', 'notes', 'property_access'
        ]
    
    def validate_move_id(self, value):
        """Validate that the move belongs to the user."""
        user = self.context['request'].user
        try:
            move = Move.objects.get(id=value, user=user)
            return move
        except Move.DoesNotExist:
            raise serializers.ValidationError("Move not found or doesn't belong to you")
    
    def validate_service_id(self, value):
        """Validate that the service exists and is active."""
        try:
            service = Service.objects.get(id=value, is_active=True)
            return service
        except Service.DoesNotExist:
            raise serializers.ValidationError("Service not found or not active")
    
    def validate_provider_id(self, value):
        """Validate that the provider exists and is verified."""
        try:
            provider = ServiceProvider.objects.get(id=value, is_active=True)
            return provider
        except ServiceProvider.DoesNotExist:
            raise serializers.ValidationError("Provider not found or not active")
    
    def validate_preferred_date(self, value):
        """Validate that preferred date is in the future."""
        if value <= timezone.now().date():
            raise serializers.ValidationError("Preferred date must be in the future")
        return value
    
    def validate_preferred_time(self, value):
        """Validate preferred time choice."""
        valid_choices = [choice[0] for choice in ServiceBooking.TIME_PREFERENCE_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid time preference. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate(self, attrs):
        """Validate that service belongs to provider."""
        service = attrs.get('service_id')
        provider = attrs.get('provider_id')
        
        if service and provider and service.provider != provider:
            raise serializers.ValidationError("Service does not belong to the specified provider")
        
        return attrs
    
    def create(self, validated_data):
        """Create a service booking."""
        move = validated_data.pop('move_id')
        service = validated_data.pop('service_id')
        provider = validated_data.pop('provider_id')
        
        return ServiceBooking.objects.create(
            move=move,
            service=service,
            provider=provider,
            **validated_data
        )


class ServiceBookingDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for service booking details.
    """
    service = ServiceListSerializer(read_only=True)
    provider = ServiceProviderSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    preferred_time_display = serializers.CharField(source='get_preferred_time_display', read_only=True)
    move_date = serializers.DateField(source='move.move_date', read_only=True)
    
    class Meta:
        model = ServiceBooking
        fields = [
            'id', 'service', 'provider', 'preferred_date', 'preferred_time',
            'preferred_time_display', 'notes', 'property_access', 'status',
            'status_display', 'confirmed_date', 'completed_date', 'quoted_price',
            'final_price', 'provider_notes', 'provider_response_date',
            'move_date', 'created_at'
        ]
        read_only_fields = [
            'id', 'service', 'provider', 'status_display', 'preferred_time_display',
            'confirmed_date', 'completed_date', 'provider_response_date',
            'move_date', 'created_at'
        ]


class ServiceBookingListSerializer(serializers.ModelSerializer):
    """
    Serializer for service booking list.
    """
    service_name = serializers.CharField(source='service.name', read_only=True)
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ServiceBooking
        fields = [
            'id', 'service_name', 'provider_name', 'preferred_date',
            'status', 'status_display', 'quoted_price', 'created_at'
        ]
        read_only_fields = [
            'id', 'service_name', 'provider_name', 'status_display', 'created_at'
        ]


class ServiceBookingUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating a service booking.
    """
    
    class Meta:
        model = ServiceBooking
        fields = [
            'preferred_date', 'preferred_time', 'notes', 'property_access', 'status'
        ]
    
    def validate_preferred_date(self, value):
        """Validate that preferred date is in the future."""
        if value <= timezone.now().date():
            raise serializers.ValidationError("Preferred date must be in the future")
        return value
    
    def validate_status(self, value):
        """Validate status choice."""
        valid_choices = [choice[0] for choice in ServiceBooking.STATUS_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid status. Choose from: {', '.join(valid_choices)}")
        return value


class ServiceReviewCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a service review.
    """
    booking_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = ServiceReview
        fields = [
            'booking_id', 'rating', 'title', 'comment', 'punctuality_rating',
            'quality_rating', 'communication_rating', 'value_rating'
        ]
    
    def validate_booking_id(self, value):
        """Validate that the booking belongs to the user and is completed."""
        user = self.context['request'].user
        try:
            booking = ServiceBooking.objects.get(id=value, move__user=user, status='completed')
            
            # Check if review already exists
            if hasattr(booking, 'review'):
                raise serializers.ValidationError("Review already exists for this booking")
            
            return booking
        except ServiceBooking.DoesNotExist:
            raise serializers.ValidationError("Booking not found, doesn't belong to you, or is not completed")
    
    def validate_rating(self, value):
        """Validate rating is between 1 and 5."""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value
    
    def validate_punctuality_rating(self, value):
        """Validate punctuality rating."""
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("Punctuality rating must be between 1 and 5")
        return value
    
    def validate_quality_rating(self, value):
        """Validate quality rating."""
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("Quality rating must be between 1 and 5")
        return value
    
    def validate_communication_rating(self, value):
        """Validate communication rating."""
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("Communication rating must be between 1 and 5")
        return value
    
    def validate_value_rating(self, value):
        """Validate value rating."""
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("Value rating must be between 1 and 5")
        return value
    
    def create(self, validated_data):
        """Create a service review."""
        booking = validated_data.pop('booking_id')
        user = self.context['request'].user
        
        return ServiceReview.objects.create(
            booking=booking,
            provider=booking.provider,
            user=user,
            **validated_data
        )


class ServiceReviewDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for service review details.
    """
    user_name = serializers.SerializerMethodField()
    service_name = serializers.CharField(source='booking.service.name', read_only=True)
    
    class Meta:
        model = ServiceReview
        fields = [
            'id', 'rating', 'title', 'comment', 'punctuality_rating',
            'quality_rating', 'communication_rating', 'value_rating',
            'user_name', 'service_name', 'is_verified', 'created_at'
        ]
        read_only_fields = ['id', 'user_name', 'service_name', 'is_verified', 'created_at']
    
    def get_user_name(self, obj):
        """Get user's first name only for privacy."""
        return obj.user.first_name if obj.user.first_name else "Anonymous"


class ServiceQuoteSerializer(serializers.ModelSerializer):
    """
    Serializer for service quotes.
    """
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ServiceQuote
        fields = [
            'id', 'total_price', 'breakdown', 'notes', 'valid_until',
            'terms_conditions', 'status', 'status_display', 'provider_name',
            'created_at'
        ]
        read_only_fields = ['id', 'status_display', 'provider_name', 'created_at']

