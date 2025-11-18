"""
Serializers for booking and scheduling.
"""
from rest_framework import serializers
from django.utils import timezone
from .models import TimeSlot, Booking
from apps.moves.models import Move
from apps.moves.serializers import MoveDetailSerializer
import re
from datetime import datetime


class TimeSlotSerializer(serializers.ModelSerializer):
    """
    Serializer for time slots.
    """
    available = serializers.SerializerMethodField()

    class Meta:
        model = TimeSlot
        fields = ['id', 'start_time', 'end_time', 'available', 'price']

    def get_available(self, obj):
        """Check if time slot is available for the requested date."""
        date = self.context.get('date')
        if date:
            return obj.is_available_on_date(date)
        return True


class BookingCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a booking without DB TimeSlot.
    Accepts a time_slot string like "10:00-11:00".
    """

    move_id = serializers.UUIDField(write_only=True)
    time_slot = serializers.CharField()

    class Meta:
        model = Booking
        fields = ['move_id', 'time_slot', 'phone_number']

    def validate_move_id(self, value):
        """Validate that the move belongs to the user and return the move instance."""
        user = self.context['request'].user
        try:
            move = Move.objects.get(id=value, user=user)
            return move
        except Move.DoesNotExist:
            raise serializers.ValidationError("Move not found or doesn't belong to you")

    def validate_time_slot(self, value):
        """Validate time slot format (HH:MM-HH:MM)."""
        pattern = r'^\d{2}:\d{2}-\d{2}:\d{2}$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Time slot must be in format HH:MM-HH:MM (e.g., 10:00-11:00)"
            )
        return value

    def validate_phone_number(self, value):
        """Validate phone number format."""
        pattern = r'^[\+\d\s\-\(\)]{8,20}$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Phone number must be 8-20 characters and can include +, spaces, hyphens, and parentheses"
            )
        return value

    def validate(self, attrs):
        """Validate booking availability."""
        move = attrs['move_id']  # this is already a Move instance from validate_move_id
        time_slot = attrs['time_slot']
        date = move.move_date

        # Check if user already has a booking for this move
        if Booking.objects.filter(move=move, status__in=['requested', 'in_progress']).exists():
            raise serializers.ValidationError({
                'move_id': ['You already have an active booking for this move']
            })

        attrs['move'] = move  # replace move_id with actual move instance
        attrs['date'] = date
        attrs.pop('move_id')  # remove move_id because Booking doesn't need it
        return attrs

    def create(self, validated_data):
        """Create a booking."""
        user = self.context['request'].user
        move = validated_data.pop('move')
        time_slot_str = validated_data.pop('time_slot')

        # Parse time_slot string into start_time and end_time
        start_time_str, end_time_str = time_slot_str.split('-')
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()

        booking = Booking.objects.create(
            user=user,
            move=move,
            start_time=start_time,
            end_time=end_time,
            status='requested',  # Set status to requested instead of default confirmed
            **validated_data
        )

        # Update move status to scheduled
        move.status = 'scheduled'
        move.save()

        return booking


class BookingDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for booking details.
    """
    time_slot_display = serializers.CharField(read_only=True)
    move = MoveDetailSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'move', 'date', 'start_time', 'end_time', 'time_slot_display',
            'status', 'confirmation_number', 'phone_number', 'created_at'
        ]
        read_only_fields = [
            'id', 'confirmation_number', 'created_at'
        ]


class BookingListSerializer(serializers.ModelSerializer):
    """
    Serializer for booking list (summary view).
    """
    time_slot_display = serializers.CharField(read_only=True)
    move = MoveDetailSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'move', 'date', 'time_slot_display',
            'status', 'confirmation_number', 'created_at','phone_number',
        ]
        read_only_fields = [
            'id', 'confirmation_number', 'created_at'
        ]
