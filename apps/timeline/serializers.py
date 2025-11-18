"""
Serializers for timeline and task management.
"""
from rest_framework import serializers
from .models import TimelineEvent, ChecklistItem, ChecklistTemplate
from apps.moves.models import Move


class TimelineEventSerializer(serializers.ModelSerializer):
    """
    Serializer for timeline events.
    """
    due_date = serializers.ReadOnlyField()
    
    class Meta:
        model = TimelineEvent
        fields = [
            'id', 'title', 'description', 'days_from_move', 'completed',
            'category', 'priority', 'estimated_time', 'due_date',
            'move_id', 'created_at'
        ]
        read_only_fields = ['id', 'move_id', 'created_at', 'due_date']
    
    def validate_category(self, value):
        """Validate category choice."""
        valid_choices = [choice[0] for choice in TimelineEvent.CATEGORY_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid category. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate_priority(self, value):
        """Validate priority choice."""
        valid_choices = [choice[0] for choice in TimelineEvent.PRIORITY_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid priority. Choose from: {', '.join(valid_choices)}")
        return value


class TimelineEventUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating timeline events (mainly completion status).
    """
    
    class Meta:
        model = TimelineEvent
        fields = ['completed']


class ChecklistItemSerializer(serializers.ModelSerializer):
    """
    Serializer for checklist items.
    """
    
    class Meta:
        model = ChecklistItem
        fields = [
            'id', 'title', 'week', 'completed', 'priority',
            'is_custom', 'move_id', 'created_at'
        ]
        read_only_fields = ['id', 'move_id', 'created_at']
    
    def validate_week(self, value):
        """Validate week value."""
        if value < 0 or value > 8:
            raise serializers.ValidationError("Week must be between 0 and 8")
        return value
    
    def validate_priority(self, value):
        """Validate priority choice."""
        valid_choices = [choice[0] for choice in ChecklistItem.PRIORITY_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid priority. Choose from: {', '.join(valid_choices)}")
        return value


class ChecklistItemCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating custom checklist items.
    """
    
    class Meta:
        model = ChecklistItem
        fields = ['title', 'week', 'priority', 'move_id']
    
    def validate_move_id(self, value):
        """Validate that the move belongs to the user."""
        user = self.context['request'].user
        try:
            move = Move.objects.get(id=value, user=user)
            return move
        except Move.DoesNotExist:
            raise serializers.ValidationError("Move not found or doesn't belong to you")
    
    def validate_week(self, value):
        """Validate week value."""
        if value < 0 or value > 8:
            raise serializers.ValidationError("Week must be between 0 and 8")
        return value
    
    def validate_priority(self, value):
        """Validate priority choice."""
        valid_choices = [choice[0] for choice in ChecklistItem.PRIORITY_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid priority. Choose from: {', '.join(valid_choices)}")
        return value
    
    def create(self, validated_data):
        """Create a custom checklist item."""
        move = validated_data.pop('move_id')
        return ChecklistItem.objects.create(
            move=move,
            is_custom=True,
            **validated_data
        )


class ChecklistItemUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating checklist items (mainly completion status).
    """
    
    class Meta:
        model = ChecklistItem
        fields = ['completed']


class ChecklistWeekSerializer(serializers.Serializer):
    """
    Serializer for grouped checklist items by week.
    """
    week = serializers.IntegerField()
    title = serializers.CharField()
    subtitle = serializers.CharField()
    progress = serializers.IntegerField()
    tasks = ChecklistItemSerializer(many=True)


class ChecklistTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for checklist templates.
    """
    
    class Meta:
        model = ChecklistTemplate
        fields = [
            'id', 'title', 'week', 'priority', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
