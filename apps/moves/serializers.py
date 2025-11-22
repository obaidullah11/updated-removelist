"""
Serializers for move management.
"""
from rest_framework import serializers
from django.utils import timezone
from django.db import models

from .models import Move, MoveCollaborator, TaskAssignment, MoveExpense
from apps.common.validators import validate_name
import logging

logger = logging.getLogger(__name__)


class MoveCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a move.
    """
    
    class Meta:
        model = Move
        fields = [
            'move_date', 'current_location', 'destination_location',
            'from_property_type', 'to_property_type',   
            'current_property_floor_map', 'new_property_floor_map',
            'discount_type', 'discount_percentage',
            'estimated_budget',
            'special_items', 'additional_details',
            'first_name', 'last_name', 'email'
        ]
    
    def validate_move_date(self, value):
        """Validate that move date is in the future."""
        if value <= timezone.now().date():
            raise serializers.ValidationError("Move date must be in the future")
        return value
    
    def validate_from_property_type(self, value):
        """Validate from property type choice."""
        valid_choices = [choice[0] for choice in Move.PROPERTY_TYPE_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid property type. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate_from_property_size(self, value):
        """Validate from property size choice."""
        valid_choices = [choice[0] for choice in Move.PROPERTY_SIZE_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid property size. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate_to_property_type(self, value):
        """Validate to property type choice."""
        valid_choices = [choice[0] for choice in Move.PROPERTY_TYPE_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid property type. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate_to_property_size(self, value):
        """Validate to property size choice."""
        valid_choices = [choice[0] for choice in Move.PROPERTY_SIZE_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid property size. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate_first_name(self, value):
        """Validate first name."""
        validate_name(value)
        return value
    
    def validate_last_name(self, value):
        """Validate last name."""
        validate_name(value)
        return value
        
    def validate_current_property_floor_map(self, value):
        """Validate current property floor map image."""
        # Add any image validation here if needed
        return value
        
    def validate_new_property_floor_map(self, value):
        """Validate new property floor map image."""
        # Add any image validation here if needed
        return value
        
    def validate_discount_type(self, value):
        """Validate discount type."""
        valid_choices = [choice[0] for choice in Move.DISCOUNT_TYPE_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid discount type. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate_estimated_budget(self, value):
        """Validate that estimated budget is positive if provided."""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Estimated budget must be greater than zero.")
        return value
    
    def create(self, validated_data):
        """Create a move with the authenticated user."""
        user = self.context['request'].user
        validated_data['user'] = user
        
        # Set discount percentage based on discount type
        discount_type = validated_data.get('discount_type')
        if discount_type == 'first_home_buyer':
            validated_data['discount_percentage'] = 15.00
        elif discount_type == 'seniors':
            validated_data['discount_percentage'] = 20.00
        elif discount_type == 'single_parent':
            validated_data['discount_percentage'] = 18.00
        else:
            validated_data['discount_percentage'] = 0.00
        
        # Create the move first
        move = super().create(validated_data)
        
        # Automatically analyze floor plan if provided
        if move.current_property_floor_map:
            try:
                
                analyzer = FloorPlanAnalyzer()
                analysis_result = analyzer.analyze_floor_plan(move.id, move.current_property_floor_map.path)
                
                if analysis_result['success']:
                    logger.info(f"Floor plan analysis completed for move {move.id}. "
                              f"Created {analysis_result['rooms_created']} rooms with inventory.")
                else:
                    logger.warning(f"Floor plan analysis failed for move {move.id}: "
                                 f"{analysis_result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                # Log error but don't fail move creation
                logger.error(f"Floor plan analysis failed for move {move.id}: {str(e)}")
        
        return move


class MoveUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating a move.
    """
    
    class Meta:
        model = Move
        fields = [
            'move_date', 'current_location', 'destination_location',
            'from_property_type', 'to_property_type',
            'current_property_floor_map', 'new_property_floor_map',
            'discount_type', 'discount_percentage',
            'estimated_budget',
            'special_items', 'additional_details',
            'first_name', 'last_name', 'email', 'status'
        ]
    
    def validate_move_date(self, value):
        """Validate that move date is in the future."""
        if value <= timezone.now().date():
            raise serializers.ValidationError("Move date must be in the future")
        return value
    
    def validate_from_property_type(self, value):
        """Validate from property type choice."""
        valid_choices = [choice[0] for choice in Move.PROPERTY_TYPE_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid property type. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate_from_property_size(self, value):
        """Validate from property size choice."""
        valid_choices = [choice[0] for choice in Move.PROPERTY_SIZE_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid property size. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate_to_property_type(self, value):
        """Validate to property type choice."""
        valid_choices = [choice[0] for choice in Move.PROPERTY_TYPE_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid property type. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate_to_property_size(self, value):
        """Validate to property size choice."""
        valid_choices = [choice[0] for choice in Move.PROPERTY_SIZE_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid property size. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate_status(self, value):
        """Validate status choice."""
        valid_choices = [choice[0] for choice in Move.STATUS_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid status. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate_current_property_floor_map(self, value):
        """Validate current property floor map image."""
        # Add any image validation here if needed
        return value
        
    def validate_new_property_floor_map(self, value):
        """Validate new property floor map image."""
        # Add any image validation here if needed
        return value
        
    def validate_discount_type(self, value):
        """Validate discount type."""
        valid_choices = [choice[0] for choice in Move.DISCOUNT_TYPE_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid discount type. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate_estimated_budget(self, value):
        """Validate that estimated budget is positive if provided."""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Estimated budget must be greater than zero.")
        return value
    
    def validate_first_name(self, value):
        """Validate first name."""
        validate_name(value)
        return value
    
    def validate_last_name(self, value):
        """Validate last name."""
        validate_name(value)
        return value


class MoveDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for move details (read-only).
    """
    inventory_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = Move
        fields = [
            'id', 'move_date', 'current_location', 'destination_location',
            'from_property_type', 'to_property_type',
            'current_property_floor_map', 'new_property_floor_map',
            'discount_type', 'discount_percentage',
            'estimated_budget',
            'special_items', 'additional_details',
            'first_name', 'last_name', 'email', 'status', 'progress',
            'created_at', 'updated_at', 'inventory_summary'
        ]
        read_only_fields = ['id', 'progress', 'created_at', 'updated_at', 'inventory_summary']
    
    def get_inventory_summary(self, obj):
        """Get inventory summary for the move."""
        try:
            rooms = obj.inventory_rooms.all()
            boxes = obj.inventory_boxes.all()
            heavy_items = obj.heavy_items.all()
            
            return {
                'total_rooms': rooms.count(),
                'total_boxes': boxes.count(),
                'total_heavy_items': heavy_items.count(),
                'total_regular_items': sum(len(room.items) for room in rooms),
                'rooms_by_type': {
                    room_type: rooms.filter(type=room_type).count()
                    for room_type in rooms.values_list('type', flat=True).distinct()
                } if rooms.exists() else {},
                'has_floor_plan_analysis': rooms.exists()
            }
        except Exception as e:
            logger.error(f"Error getting inventory summary for move {obj.id}: {str(e)}")
            return {
                'total_rooms': 0,
                'total_boxes': 0,
                'total_heavy_items': 0,
                'total_regular_items': 0,
                'rooms_by_type': {},
                'has_floor_plan_analysis': False
            }


class MoveListSerializer(serializers.ModelSerializer):
    """
    Serializer for move list (summary view).
    """
    
    class Meta:
        model = Move
        fields = [
            'id', 'move_date', 'current_location', 'destination_location',
            'status', 'progress', 'created_at'
        ]
        read_only_fields = ['id', 'progress', 'created_at']


class MoveCollaboratorSerializer(serializers.ModelSerializer):
    """
    Serializer for move collaborators.
    """
    
    class Meta:
        model = MoveCollaborator
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role', 'permissions',
            'invited_at', 'accepted_at', 'is_active'
        ]
        read_only_fields = ['id', 'invited_at', 'accepted_at']
        
    def validate_email(self, value):
        """Validate email format and uniqueness for the move."""
        move_id = self.context.get('move_id')
        if move_id and MoveCollaborator.objects.filter(move_id=move_id, email=value).exists():
            raise serializers.ValidationError("This email is already invited to this move.")
        return value


class MoveCollaboratorInviteSerializer(serializers.ModelSerializer):
    """
    Serializer for inviting collaborators.
    """
    move_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = MoveCollaborator
        fields = [
            'move_id', 'email', 'first_name', 'last_name', 'role', 'permissions'
        ]
        
    def validate_move_id(self, value):
        """Validate that the move belongs to the user."""
        user = self.context['request'].user
        try:
            move = Move.objects.get(id=value, user=user)
            return move
        except Move.DoesNotExist:
            raise serializers.ValidationError("Move not found or doesn't belong to you")
    
    def validate(self, attrs):
        """Validate that email is not already invited to this move."""
        move = attrs['move_id']
        email = attrs['email']
        
        if MoveCollaborator.objects.filter(move=move, email=email).exists():
            raise serializers.ValidationError({'email': 'This email is already invited to this move.'})
        
        attrs['move'] = move
        attrs.pop('move_id')
        return attrs
    
    def create(self, validated_data):
        """Create collaborator invitation."""
        return MoveCollaborator.objects.create(**validated_data)


class TaskAssignmentSerializer(serializers.ModelSerializer):
    """
    Serializer for task assignments.
    """
    collaborator_name = serializers.CharField(source='collaborator.first_name', read_only=True)
    task_title = serializers.CharField(source='timeline_event.title', read_only=True)
    
    class Meta:
        model = TaskAssignment
        fields = [
            'id', 'timeline_event', 'collaborator', 'collaborator_name', 
            'task_title', 'assigned_at', 'notes'
        ]
        read_only_fields = ['id', 'assigned_at', 'collaborator_name', 'task_title']


class MoveExpenseSerializer(serializers.ModelSerializer):
    """Serializer for move expenses."""
    
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = MoveExpense
        fields = [
            'id', 'move', 'description', 'amount', 'category', 'category_display',
            'payment_method', 'payment_method_display', 'expense_date',
            'receipt', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'category_display', 'payment_method_display']
    
    def validate_amount(self, value):
        """Validate that amount is positive."""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value
    
    def validate_move(self, value):
        """Validate that move belongs to the user."""
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError("You can only add expenses to your own moves.")
        return value


class MoveExpenseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating expenses."""
    
    class Meta:
        model = MoveExpense
        fields = [
            'move', 'description', 'amount', 'category', 'payment_method',
            'expense_date', 'receipt', 'notes'
        ]
    
    def validate_amount(self, value):
        """Validate that amount is positive."""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value
