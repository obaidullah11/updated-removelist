"""
Admin panel views for dashboard, user management, and analytics.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from apps.bookings.models import Booking
from apps.verification.models import PartnerDocument
from .models import AdminNotification, DashboardMetric
from .serializers import (
    UserListSerializer, UserDetailSerializer, UserStatusUpdateSerializer,
    BookingListSerializer, BookingDetailSerializer,
    PartnerListSerializer, PartnerDetailSerializer, PartnerActionSerializer,
    NotificationSerializer, DashboardMetricSerializer,
    UserStatsSerializer, BookingStatsSerializer, PartnerStatsSerializer
)

User = get_user_model()


class AdminPagination(PageNumberPagination):
    """Custom pagination for admin panel."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# Dashboard APIs
@api_view(['GET'])
@permission_classes([IsAdminUser])
def dashboard_metrics(request):
    """Get dashboard metrics and statistics."""
    try:
        # Calculate user metrics
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        new_users_this_month = User.objects.filter(
            created_at__gte=timezone.now().replace(day=1)
        ).count()
        verified_users = User.objects.filter(is_email_verified=True).count()
        
        # Calculate booking metrics
        total_bookings = Booking.objects.count()
        completed_bookings = Booking.objects.filter(status='completed').count()
        pending_bookings = Booking.objects.filter(status='pending').count()
        cancelled_bookings = Booking.objects.filter(status='cancelled').count()
        
        # Calculate revenue (using fixed price per booking as proxy)
        total_bookings_count = Booking.objects.count()
        total_revenue = total_bookings_count * 200.0  # $200 per booking
        
        monthly_bookings_count = Booking.objects.filter(
            created_at__gte=timezone.now().replace(day=1)
        ).count()
        monthly_revenue = monthly_bookings_count * 200.0  # $200 per booking
        
        # Calculate partner metrics
        total_partners = User.objects.filter(role_type='partner').count()
        approved_partners = User.objects.filter(
            role_type='partner', is_document_verified=True
        ).count()
        pending_partners = User.objects.filter(
            role_type='partner', is_doucment_submitted=True, is_document_verified=False
        ).count()
        
        # Calculate eco metrics (placeholder - would need actual eco score calculation)
        avg_eco_score = 85.5  # This would be calculated from actual data
        total_carbon_offset = 2450.0  # This would be calculated from actual data
        
        metrics = {
            'users': {
                'total': total_users,
                'active': active_users,
                'new_this_month': new_users_this_month,
                'verified': verified_users,
                'growth_rate': 12.5  # This would be calculated
            },
            'bookings': {
                'total': total_bookings,
                'completed': completed_bookings,
                'pending': pending_bookings,
                'cancelled': cancelled_bookings,
                'completion_rate': (completed_bookings / total_bookings * 100) if total_bookings > 0 else 0
            },
            'revenue': {
                'total': float(total_revenue),
                'monthly': float(monthly_revenue),
                'growth_rate': 23.1  # This would be calculated
            },
            'partners': {
                'total': total_partners,
                'approved': approved_partners,
                'pending': pending_partners,
                'approval_rate': (approved_partners / total_partners * 100) if total_partners > 0 else 0
            },
            'eco_impact': {
                'avg_eco_score': avg_eco_score,
                'carbon_offset': total_carbon_offset,
                'eco_bookings_percentage': 94.2  # This would be calculated
            }
        }
        
        return Response({
            'success': True,
            'message': 'Dashboard metrics retrieved successfully',
            'data': metrics
        })
    
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving dashboard metrics: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def dashboard_analytics(request):
    """Get analytics data for charts and trends."""
    try:
        # Get date range from query params
        days = int(request.GET.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Generate booking trends data
        booking_trends = []
        for i in range(days):
            date = start_date + timedelta(days=i)
            bookings_count = Booking.objects.filter(
                created_at__date=date
            ).count()
            eco_score = 85 + (i % 10)  # Placeholder calculation
            
            booking_trends.append({
                'date': date.strftime('%Y-%m-%d'),
                'bookings': bookings_count,
                'eco_score': eco_score
            })
        
        # Generate partner status data
        partner_status = [
            {
                'name': 'Approved',
                'value': User.objects.filter(role_type='partner', is_document_verified=True).count(),
                'color': '#009A64'
            },
            {
                'name': 'Pending',
                'value': User.objects.filter(role_type='partner', is_doucment_submitted=True, is_document_verified=False).count(),
                'color': '#f59e0b'
            },
            {
                'name': 'Rejected',
                'value': User.objects.filter(role_type='partner', is_doucment_submitted=True, is_document_verified=False).count() // 3,  # Placeholder
                'color': '#ef4444'
            }
        ]
        
        # Generate recent activities
        recent_activities = AdminNotification.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).order_by('-created_at')[:10]
        
        activities = NotificationSerializer(recent_activities, many=True).data
        
        analytics_data = {
            'booking_trends': booking_trends,
            'partner_status': partner_status,
            'recent_activities': activities,
            'period': f'{days} days'
        }
        
        return Response({
            'success': True,
            'message': 'Analytics data retrieved successfully',
            'data': analytics_data
        })
    
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving analytics data: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# User Management APIs
@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_users_list(request):
    """Get list of users for admin panel."""
    try:
        paginator = AdminPagination()
        
        # Get query parameters
        search = request.GET.get('search', '')
        role = request.GET.get('role', '')
        status_filter = request.GET.get('status', '')
        
        # Build queryset
        queryset = User.objects.all()
        
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        
        if role:
            queryset = queryset.filter(role_type=role)
        
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        elif status_filter == 'verified':
            queryset = queryset.filter(is_email_verified=True)
        elif status_filter == 'unverified':
            queryset = queryset.filter(is_email_verified=False)
        
        # Order by creation date
        queryset = queryset.order_by('-created_at')
        
        # Paginate
        page = paginator.paginate_queryset(queryset, request)
        serializer = UserListSerializer(page, many=True)
        
        return paginator.get_paginated_response({
            'success': True,
            'message': 'Users retrieved successfully',
            'data': serializer.data
        })
    
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving users: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_user_detail(request, user_id):
    """Get detailed user information."""
    try:
        user = User.objects.get(id=user_id)
        serializer = UserDetailSerializer(user)
        
        return Response({
            'success': True,
            'message': 'User details retrieved successfully',
            'data': serializer.data
        })
    
    except User.DoesNotExist:
        return Response({
            'success': False,
            'message': 'User not found',
            'data': None
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving user details: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def admin_user_status(request, user_id):
    """Update user status (active/inactive)."""
    try:
        user = User.objects.get(id=user_id)
        serializer = UserStatusUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            user.is_active = serializer.validated_data['is_active']
            user.save()
            
            # Create notification
            AdminNotification.objects.create(
                title=f"User Status Updated",
                message=f"User {user.full_name} status changed to {'Active' if user.is_active else 'Inactive'}",
                notification_type='info',
                user=user
            )
            
            return Response({
                'success': True,
                'message': 'User status updated successfully',
                'data': {'is_active': user.is_active}
            })
        
        return Response({
            'success': False,
            'message': 'Invalid data provided',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except User.DoesNotExist:
        return Response({
            'success': False,
            'message': 'User not found',
            'data': None
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error updating user status: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Booking Management APIs
@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_bookings_list(request):
    """Get list of bookings for admin panel."""
    try:
        paginator = AdminPagination()
        
        # Get query parameters
        search = request.GET.get('search', '')
        status_filter = request.GET.get('status', '')
        
        # Build queryset
        queryset = Booking.objects.select_related('user').all()
        
        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search)
            )
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Order by creation date
        queryset = queryset.order_by('-created_at')
        
        # Paginate
        page = paginator.paginate_queryset(queryset, request)
        serializer = BookingListSerializer(page, many=True)
        
        return paginator.get_paginated_response({
            'success': True,
            'message': 'Bookings retrieved successfully',
            'data': serializer.data
        })
    
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving bookings: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_booking_detail(request, booking_id):
    """Get detailed booking information."""
    try:
        booking = Booking.objects.select_related('user').get(id=booking_id)
        serializer = BookingDetailSerializer(booking)
        
        return Response({
            'success': True,
            'message': 'Booking details retrieved successfully',
            'data': serializer.data
        })
    
    except Booking.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Booking not found',
            'data': None
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving booking details: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Partner Management APIs
@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_partners_list(request):
    """Get list of partners for admin panel."""
    try:
        paginator = AdminPagination()
        
        # Get query parameters
        search = request.GET.get('search', '')
        status_filter = request.GET.get('status', '')
        
        # Build queryset
        queryset = PartnerDocument.objects.select_related('partner').all()
        
        if search:
            queryset = queryset.filter(
                Q(partner__first_name__icontains=search) |
                Q(partner__last_name__icontains=search) |
                Q(partner__email__icontains=search)
            )
        
        if status_filter:
            if status_filter == 'approved':
                queryset = queryset.filter(is_verified=True)
            elif status_filter == 'rejected':
                queryset = queryset.filter(is_rejected=True)
            elif status_filter == 'pending':
                queryset = queryset.filter(is_submitted=True, is_verified=False, is_rejected=False)
        
        # Order by submission date
        queryset = queryset.order_by('-submitted_at')
        
        # Paginate
        page = paginator.paginate_queryset(queryset, request)
        serializer = PartnerListSerializer(page, many=True)
        
        return paginator.get_paginated_response({
            'success': True,
            'message': 'Partners retrieved successfully',
            'data': serializer.data
        })
    
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving partners: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_partner_detail(request, partner_id):
    """Get detailed partner information."""
    try:
        partner_doc = PartnerDocument.objects.select_related('partner').get(id=partner_id)
        serializer = PartnerDetailSerializer(partner_doc)
        
        return Response({
            'success': True,
            'message': 'Partner details retrieved successfully',
            'data': serializer.data
        })
    
    except PartnerDocument.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Partner not found',
            'data': None
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving partner details: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_partner_approve(request, partner_id):
    """Approve partner documents."""
    try:
        partner_doc = PartnerDocument.objects.get(id=partner_id)
        serializer = PartnerActionSerializer(data=request.data)
        
        if serializer.is_valid():
            partner_doc.approve()
            partner_doc.partner.is_document_verified = True
            partner_doc.partner.save()
            
            # Create notification
            AdminNotification.objects.create(
                title="Partner Approved",
                message=f"Partner {partner_doc.partner.full_name} has been approved! 🌱",
                notification_type='success',
                partner_document=partner_doc
            )
            
            return Response({
                'success': True,
                'message': 'Partner approved successfully',
                'data': {'status': 'approved'}
            })
        
        return Response({
            'success': False,
            'message': 'Invalid data provided',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except PartnerDocument.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Partner not found',
            'data': None
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error approving partner: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_partner_reject(request, partner_id):
    """Reject partner documents."""
    try:
        partner_doc = PartnerDocument.objects.get(id=partner_id)
        serializer = PartnerActionSerializer(data=request.data)
        
        if serializer.is_valid():
            partner_doc.reject()
            
            # Create notification
            AdminNotification.objects.create(
                title="Partner Rejected",
                message=f"Partner {partner_doc.partner.full_name} has been rejected",
                notification_type='warning',
                partner_document=partner_doc
            )
            
            return Response({
                'success': True,
                'message': 'Partner rejected successfully',
                'data': {'status': 'rejected'}
            })
        
        return Response({
            'success': False,
            'message': 'Invalid data provided',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except PartnerDocument.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Partner not found',
            'data': None
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error rejecting partner: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Notifications APIs
@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_notifications_list(request):
    """Get admin notifications."""
    try:
        paginator = AdminPagination()
        
        # Get query parameters
        notification_type = request.GET.get('type', '')
        is_read = request.GET.get('read', '')
        
        # Build queryset
        queryset = AdminNotification.objects.all()
        
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        if is_read == 'true':
            queryset = queryset.filter(is_read=True)
        elif is_read == 'false':
            queryset = queryset.filter(is_read=False)
        
        # Order by creation date
        queryset = queryset.order_by('-created_at')
        
        # Paginate
        page = paginator.paginate_queryset(queryset, request)
        serializer = NotificationSerializer(page, many=True)
        
        return paginator.get_paginated_response({
            'success': True,
            'message': 'Notifications retrieved successfully',
            'data': serializer.data
        })
    
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving notifications: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def admin_notification_mark_read(request, notification_id):
    """Mark notification as read."""
    try:
        notification = AdminNotification.objects.get(id=notification_id)
        notification.is_read = True
        notification.save()
        
        return Response({
            'success': True,
            'message': 'Notification marked as read',
            'data': {'is_read': True}
        })
    
    except AdminNotification.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Notification not found',
            'data': None
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error updating notification: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_notifications_mark_all_read(request):
    """Mark all notifications as read."""
    try:
        AdminNotification.objects.filter(is_read=False).update(is_read=True)
        
        return Response({
            'success': True,
            'message': 'All notifications marked as read',
            'data': {'updated_count': AdminNotification.objects.filter(is_read=True).count()}
        })
    
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error updating notifications: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def admin_notification_delete(request, notification_id):
    """Delete notification."""
    try:
        notification = AdminNotification.objects.get(id=notification_id)
        notification.delete()
        
        return Response({
            'success': True,
            'message': 'Notification deleted successfully',
            'data': None
        })
    
    except AdminNotification.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Notification not found',
            'data': None
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error deleting notification: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
