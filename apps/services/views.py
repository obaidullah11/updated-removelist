"""
Views for service booking marketplace.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import ServiceProvider, Service, ServiceBooking, ServiceReview, ServiceQuote
from .serializers import (
    ServiceProviderSerializer, ServiceDetailSerializer, ServiceListSerializer,
    ServiceBookingCreateSerializer, ServiceBookingDetailSerializer, 
    ServiceBookingListSerializer, ServiceBookingUpdateSerializer,
    ServiceReviewCreateSerializer, ServiceReviewDetailSerializer,
    ServiceQuoteSerializer
)
from apps.moves.models import Move
from apps.common.utils import success_response, error_response, paginated_response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_services(request):
    """
    Get available services with filtering options.
    """
    move_id = request.GET.get('move_id')
    category = request.GET.get('category')
    search = request.GET.get('search')
    verified_only = request.GET.get('verified_only', 'false').lower() == 'true'
    
    if not move_id:
        return error_response(
            "Move ID required",
            {'move_id': ['This parameter is required']},
            status.HTTP_400_BAD_REQUEST
        )
    
    # Verify move belongs to user
    move = get_object_or_404(Move, id=move_id, user=request.user)
    
    # Get active services
    services = Service.objects.filter(
        is_active=True,
        provider__is_active=True
    ).select_related('provider')
    
    # Apply filters
    if category:
        services = services.filter(category=category)
    
    if verified_only:
        services = services.filter(provider__verification_status='verified')
    
    if search:
        services = services.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(provider__name__icontains=search)
        )
    
    # Order by provider rating
    services = services.order_by('-provider__rating', 'name')
    
    # Check if pagination is requested
    if request.GET.get('page'):
        return paginated_response(
            services,
            ServiceListSerializer,
            request,
            "Services retrieved successfully"
        )
    
    # Return all services without pagination
    serializer = ServiceDetailSerializer(services, many=True)
    
    return success_response(
        "Services retrieved successfully",
        serializer.data
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_service(request, service_id):
    """
    Get service details by ID.
    """
    service = get_object_or_404(
        Service, 
        id=service_id, 
        is_active=True, 
        provider__is_active=True
    )
    
    serializer = ServiceDetailSerializer(service)
    
    return success_response(
        "Service details retrieved",
        serializer.data
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_service_categories(request):
    """
    Get all available service categories.
    """
    categories = [
        {
            'id': choice[0],
            'name': choice[1],
            'services_count': Service.objects.filter(
                category=choice[0], 
                is_active=True, 
                provider__is_active=True
            ).count()
        }
        for choice in Service.CATEGORY_CHOICES
    ]
    
    return success_response(
        "Service categories retrieved successfully",
        categories
    )


# ============= SERVICE BOOKING VIEWS =============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_service_bookings(request):
    """
    Get service bookings for the user.
    """
    move_id = request.GET.get('move_id')
    booking_status = request.GET.get('status')
    
    if move_id:
        # Get bookings for a specific move
        move = get_object_or_404(Move, id=move_id, user=request.user)
        bookings = ServiceBooking.objects.filter(move=move)
    else:
        # Get all bookings for the user
        bookings = ServiceBooking.objects.filter(move__user=request.user)
    
    # Apply status filter
    if booking_status:
        bookings = bookings.filter(status=booking_status)
    
    # Order by creation date
    bookings = bookings.select_related('service', 'provider', 'move').order_by('-created_at')
    
    # Check if pagination is requested
    if request.GET.get('page'):
        return paginated_response(
            bookings,
            ServiceBookingListSerializer,
            request,
            "Service bookings retrieved successfully"
        )
    
    # Return all bookings without pagination
    serializer = ServiceBookingDetailSerializer(bookings, many=True)
    
    return success_response(
        "Service bookings retrieved successfully",
        serializer.data
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_service_booking(request):
    """
    Create a new service booking.
    """
    serializer = ServiceBookingCreateSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        booking = serializer.save()
        
        # TODO: Send notification to service provider
        # send_booking_notification(booking)
        
        # Return detailed booking data
        detail_serializer = ServiceBookingDetailSerializer(booking)
        
        return success_response(
            "Service booking created successfully",
            detail_serializer.data,
            status.HTTP_201_CREATED
        )
    
    return error_response(
        "Service booking creation failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_service_booking(request, booking_id):
    """
    Get service booking details by ID.
    """
    booking = get_object_or_404(ServiceBooking, id=booking_id, move__user=request.user)
    
    serializer = ServiceBookingDetailSerializer(booking)
    
    return success_response(
        "Service booking details retrieved",
        serializer.data
    )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_service_booking(request, booking_id):
    """
    Update a service booking.
    """
    booking = get_object_or_404(ServiceBooking, id=booking_id, move__user=request.user)
    
    # Only allow updates if booking is still pending
    if booking.status not in ['pending', 'confirmed']:
        return error_response(
            "Cannot update booking",
            {'detail': ['Booking cannot be updated in its current status']},
            status.HTTP_400_BAD_REQUEST
        )
    
    serializer = ServiceBookingUpdateSerializer(booking, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        
        # Return updated booking data
        detail_serializer = ServiceBookingDetailSerializer(booking)
        
        return success_response(
            "Service booking updated successfully",
            detail_serializer.data
        )
    
    return error_response(
        "Service booking update failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cancel_service_booking(request, booking_id):
    """
    Cancel a service booking.
    """
    booking = get_object_or_404(ServiceBooking, id=booking_id, move__user=request.user)
    
    # Only allow cancellation if booking is pending or confirmed
    if booking.status not in ['pending', 'confirmed']:
        return error_response(
            "Cannot cancel booking",
            {'detail': ['Booking cannot be cancelled in its current status']},
            status.HTTP_400_BAD_REQUEST
        )
    
    booking.status = 'cancelled'
    booking.save()
    
    # TODO: Send cancellation notification to provider
    # send_cancellation_notification(booking)
    
    return success_response("Service booking cancelled successfully")


# ============= SERVICE REVIEW VIEWS =============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_service_reviews(request):
    """
    Get service reviews for a provider or user's reviews.
    """
    provider_id = request.GET.get('provider_id')
    my_reviews = request.GET.get('my_reviews', 'false').lower() == 'true'
    
    if provider_id:
        # Get reviews for a specific provider
        provider = get_object_or_404(ServiceProvider, id=provider_id)
        reviews = ServiceReview.objects.filter(
            provider=provider, 
            is_public=True
        ).select_related('user', 'booking__service')
    elif my_reviews:
        # Get user's own reviews
        reviews = ServiceReview.objects.filter(
            user=request.user
        ).select_related('provider', 'booking__service')
    else:
        return error_response(
            "Provider ID or my_reviews parameter required",
            {'detail': ['Specify provider_id or set my_reviews=true']},
            status.HTTP_400_BAD_REQUEST
        )
    
    # Order by creation date
    reviews = reviews.order_by('-created_at')
    
    # Check if pagination is requested
    if request.GET.get('page'):
        return paginated_response(
            reviews,
            ServiceReviewDetailSerializer,
            request,
            "Service reviews retrieved successfully"
        )
    
    # Return all reviews without pagination
    serializer = ServiceReviewDetailSerializer(reviews, many=True)
    
    return success_response(
        "Service reviews retrieved successfully",
        serializer.data
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_service_review(request):
    """
    Create a new service review.
    """
    serializer = ServiceReviewCreateSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        review = serializer.save()
        
        # Return detailed review data
        detail_serializer = ServiceReviewDetailSerializer(review)
        
        return success_response(
            "Service review created successfully",
            detail_serializer.data,
            status.HTTP_201_CREATED
        )
    
    return error_response(
        "Service review creation failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_service_review(request, review_id):
    """
    Get service review details by ID.
    """
    review = get_object_or_404(ServiceReview, id=review_id, user=request.user)
    
    serializer = ServiceReviewDetailSerializer(review)
    
    return success_response(
        "Service review details retrieved",
        serializer.data
    )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_service_review(request, review_id):
    """
    Update a service review.
    """
    review = get_object_or_404(ServiceReview, id=review_id, user=request.user)
    
    # Only allow certain fields to be updated
    allowed_fields = ['rating', 'title', 'comment', 'punctuality_rating', 'quality_rating', 'communication_rating', 'value_rating']
    update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
    
    for field, value in update_data.items():
        if field in ['rating', 'punctuality_rating', 'quality_rating', 'communication_rating', 'value_rating']:
            if value is not None and (value < 1 or value > 5):
                return error_response(
                    "Invalid rating",
                    {field: ['Rating must be between 1 and 5']},
                    status.HTTP_400_BAD_REQUEST
                )
        setattr(review, field, value)
    
    review.save()
    
    # Return updated review data
    detail_serializer = ServiceReviewDetailSerializer(review)
    
    return success_response(
        "Service review updated successfully",
        detail_serializer.data
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_service_review(request, review_id):
    """
    Delete a service review.
    """
    review = get_object_or_404(ServiceReview, id=review_id, user=request.user)
    
    provider = review.provider
    review.delete()
    
    # Update provider rating after review deletion
    provider.update_rating()
    
    return success_response("Service review deleted successfully")


# ============= SERVICE QUOTE VIEWS =============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_service_quotes(request):
    """
    Get service quotes for a booking.
    """
    booking_id = request.GET.get('booking_id')
    
    if not booking_id:
        return error_response(
            "Booking ID required",
            {'booking_id': ['This parameter is required']},
            status.HTTP_400_BAD_REQUEST
        )
    
    # Verify booking belongs to user
    booking = get_object_or_404(ServiceBooking, id=booking_id, move__user=request.user)
    
    # Get quotes for this booking
    quotes = ServiceQuote.objects.filter(booking=booking).select_related('provider').order_by('-created_at')
    
    serializer = ServiceQuoteSerializer(quotes, many=True)
    
    return success_response(
        "Service quotes retrieved successfully",
        serializer.data
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_service_quote(request, quote_id):
    """
    Get service quote details by ID.
    """
    quote = get_object_or_404(ServiceQuote, id=quote_id, booking__move__user=request.user)
    
    serializer = ServiceQuoteSerializer(quote)
    
    return success_response(
        "Service quote details retrieved",
        serializer.data
    )

