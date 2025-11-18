"""
Serializers for admin panel APIs.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.bookings.models import Booking
from apps.verification.models import PartnerDocument
from .models import AdminNotification, DashboardMetric

User = get_user_model()


class UserListSerializer(serializers.ModelSerializer):
    """Serializer for user list in admin panel."""
    full_name = serializers.ReadOnlyField()
    role_display = serializers.CharField(source='get_role_type_display', read_only=True)
    is_verified = serializers.BooleanField(source='is_email_verified', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'role_type', 'role_display', 'is_verified',
            'is_active', 'created_at', 'avatar'
        ]


class UserDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed user information in admin panel."""
    full_name = serializers.ReadOnlyField()
    role_display = serializers.CharField(source='get_role_type_display', read_only=True)
    is_verified = serializers.BooleanField(source='is_email_verified', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'role_type', 'role_display', 'is_verified',
            'is_active', 'created_at', 'updated_at', 'avatar',
            'is_doucment_submitted', 'is_document_verified'
        ]


class UserStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating user status."""
    is_active = serializers.BooleanField()
    reason = serializers.CharField(max_length=500, required=False)


class BookingListSerializer(serializers.ModelSerializer):
    """Serializer for booking list in admin panel."""
    customer_name = serializers.CharField(source='user.full_name', read_only=True)
    customer_email = serializers.CharField(source='user.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    move_date = serializers.DateField(source='date', read_only=True)
    total_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = [
            'id', 'customer_name', 'customer_email', 'status', 'status_display',
            'move_date', 'total_amount', 'created_at', 'updated_at'
        ]
    
    def get_total_amount(self, obj):
        return 200.00  # Fixed price per booking


class BookingDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed booking information in admin panel."""
    customer_name = serializers.CharField(source='user.full_name', read_only=True)
    customer_email = serializers.CharField(source='user.email', read_only=True)
    customer_phone = serializers.CharField(source='user.phone_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    move_date = serializers.DateField(source='date', read_only=True)
    time_slot = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = [
            'id', 'customer_name', 'customer_email', 'customer_phone',
            'status', 'status_display', 'move_date', 'time_slot',
            'total_amount', 'created_at', 'updated_at'
        ]
    
    def get_time_slot(self, obj):
        return f"{obj.start_time} - {obj.end_time}"
    
    def get_total_amount(self, obj):
        return 200.00  # Fixed price per booking


class PartnerListSerializer(serializers.ModelSerializer):
    """Serializer for partner list in admin panel."""
    partner_name = serializers.CharField(source='partner.full_name', read_only=True)
    partner_email = serializers.CharField(source='partner.email', read_only=True)
    partner_phone = serializers.CharField(source='partner.phone_number', read_only=True)
    status = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    submitted_at = serializers.DateTimeField(source='submitted_at', read_only=True)
    document_type = serializers.SerializerMethodField()
    
    class Meta:
        model = PartnerDocument
        fields = [
            'id', 'partner_name', 'partner_email', 'partner_phone',
            'status', 'status_display', 'submitted_at', 'document_type'
        ]
    
    def get_status(self, obj):
        if obj.is_verified:
            return 'approved'
        elif obj.is_rejected:
            return 'rejected'
        elif obj.is_submitted:
            return 'pending'
        else:
            return 'draft'
    
    def get_status_display(self, obj):
        status = self.get_status(obj)
        return status.title()
    
    def get_document_type(self, obj):
        return 'Partner Verification Documents'


class PartnerDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed partner information in admin panel."""
    partner_name = serializers.CharField(source='partner.full_name', read_only=True)
    partner_email = serializers.CharField(source='partner.email', read_only=True)
    partner_phone = serializers.CharField(source='partner.phone_number', read_only=True)
    status = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    submitted_at = serializers.DateTimeField(source='submitted_at', read_only=True)
    document_type = serializers.SerializerMethodField()
    notes = serializers.CharField(source='rejection_reason', read_only=True)
    
    class Meta:
        model = PartnerDocument
        fields = [
            'id', 'partner_name', 'partner_email', 'partner_phone',
            'status', 'status_display', 'submitted_at', 'document_type',
            'document_1', 'document_2', 'document_3', 'document_4', 'notes', 'submitted_at'
        ]
    
    def get_status(self, obj):
        if obj.is_verified:
            return 'approved'
        elif obj.is_rejected:
            return 'rejected'
        elif obj.is_submitted:
            return 'pending'
        else:
            return 'draft'
    
    def get_status_display(self, obj):
        status = self.get_status(obj)
        return status.title()
    
    def get_document_type(self, obj):
        return 'Partner Verification Documents'


class PartnerActionSerializer(serializers.Serializer):
    """Serializer for partner approval/rejection actions."""
    reason = serializers.CharField(max_length=500, required=False)


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for admin notifications."""
    type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = AdminNotification
        fields = [
            'id', 'title', 'message', 'notification_type', 'type_display',
            'is_read', 'created_at', 'time_ago'
        ]
    
    def get_time_ago(self, obj):
        """Calculate time ago for display."""
        from django.utils import timezone
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"


class DashboardMetricSerializer(serializers.ModelSerializer):
    """Serializer for dashboard metrics."""
    type_display = serializers.CharField(source='get_metric_type_display', read_only=True)
    
    class Meta:
        model = DashboardMetric
        fields = [
            'id', 'metric_type', 'type_display', 'value', 'period',
            'date', 'metadata', 'created_at'
        ]


class AnalyticsDataSerializer(serializers.Serializer):
    """Serializer for analytics data aggregation."""
    period = serializers.CharField(max_length=20)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    metrics = serializers.ListField(child=serializers.CharField())


class UserStatsSerializer(serializers.Serializer):
    """Serializer for user statistics."""
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    new_users_this_month = serializers.IntegerField()
    verified_users = serializers.IntegerField()
    users_by_role = serializers.DictField()


class BookingStatsSerializer(serializers.Serializer):
    """Serializer for booking statistics."""
    total_bookings = serializers.IntegerField()
    completed_bookings = serializers.IntegerField()
    pending_bookings = serializers.IntegerField()
    cancelled_bookings = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    monthly_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)


class PartnerStatsSerializer(serializers.Serializer):
    """Serializer for partner statistics."""
    total_partners = serializers.IntegerField()
    approved_partners = serializers.IntegerField()
    pending_partners = serializers.IntegerField()
    rejected_partners = serializers.IntegerField()
    partners_this_month = serializers.IntegerField()
