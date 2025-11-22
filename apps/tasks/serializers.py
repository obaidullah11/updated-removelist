"""
Serializers for task management.
"""
from rest_framework import serializers
from django.utils import timezone
from .models import Task, TaskTimer, TaskTemplate
from apps.moves.models import Move, MoveCollaborator
from django.contrib.auth import get_user_model

User = get_user_model()


class TaskCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a task.
    """
    move_id = serializers.UUIDField(write_only=True)
    collaborator_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Task
        fields = [
            'move_id', 'title', 'description', 'category', 'location', 
            'priority', 'due_date', 'assigned_to', 'collaborator_id',
            'is_external', 'external_url', 'subtasks'
        ]
    
    def validate_move_id(self, value):
        """Validate that the move belongs to the user."""
        user = self.context['request'].user
        try:
            move = Move.objects.get(id=value, user=user)
            return move
        except Move.DoesNotExist:
            raise serializers.ValidationError("Move not found or doesn't belong to you")
    
    def validate_collaborator_id(self, value):
        """Validate that the collaborator belongs to the move."""
        if value:
            try:
                collaborator = MoveCollaborator.objects.get(id=value)
                return collaborator
            except MoveCollaborator.DoesNotExist:
                raise serializers.ValidationError("Collaborator not found")
        return None
    
    def validate_category(self, value):
        """Validate task category choice."""
        valid_choices = [choice[0] for choice in Task.CATEGORY_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid category. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate_location(self, value):
        """Validate task location choice."""
        valid_choices = [choice[0] for choice in Task.LOCATION_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid location. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate_priority(self, value):
        """Validate task priority choice."""
        valid_choices = [choice[0] for choice in Task.PRIORITY_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid priority. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate_subtasks(self, value):
        """Validate subtasks list."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Subtasks must be a list")
        
        for subtask in value:
            if not isinstance(subtask, str):
                raise serializers.ValidationError("Each subtask must be a string")
            if len(subtask.strip()) == 0:
                raise serializers.ValidationError("Subtasks cannot be empty strings")
        
        return value
    
    def create(self, validated_data):
        """Create a task."""
        move = validated_data.pop('move_id')
        collaborator = validated_data.pop('collaborator_id', None)
        
        # If no assigned_to is provided, assign to the move owner
        if not validated_data.get('assigned_to'):
            validated_data['assigned_to'] = move.user
        
        return Task.objects.create(
            move=move, 
            collaborator=collaborator, 
            **validated_data
        )


class TaskDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for task details.
    """
    assigned_to_name = serializers.SerializerMethodField()
    collaborator_name = serializers.SerializerMethodField()
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    location_display = serializers.CharField(source='get_location_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    time_spent_formatted = serializers.SerializerMethodField()
    week = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'category', 'category_display',
            'location', 'location_display', 'priority', 'priority_display',
            'completed', 'completed_at', 'due_date', 'assigned_to', 'assigned_to_name',
            'collaborator', 'collaborator_name', 'is_external', 'external_url',
            'subtasks', 'time_spent', 'time_spent_formatted', 'created_at', 'week'
        ]
        read_only_fields = [
            'id', 'category_display', 'location_display', 'priority_display',
            'assigned_to_name', 'collaborator_name', 'time_spent_formatted', 'created_at', 'week'
        ]
    
    def get_assigned_to_name(self, obj):
        """Get assigned user's full name."""
        if obj.assigned_to:
            return f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip()
        return None
    
    def get_collaborator_name(self, obj):
        """Get collaborator's full name."""
        if obj.collaborator:
            return f"{obj.collaborator.first_name} {obj.collaborator.last_name}".strip()
        return None
    
    def get_week(self, obj):
        """Calculate week number from due_date and move_date."""
        if not obj.due_date or not obj.move or not obj.move.move_date:
            return 0
        
        from datetime import timedelta
        move_date = obj.move.move_date
        due_date = obj.due_date.date()
        
        # Calculate days difference
        days_diff = (move_date - due_date).days
        
        # Calculate week using the same formula as backend: N = (days_diff + 3) / 7
        # This reverses: due_date = (move_date - N weeks) + 3 days
        calculated_week = round((days_diff + 3) / 7)
        
        # Clamp to valid range (0-8)
        if calculated_week >= 8:
            return 8
        if calculated_week <= 0:
            return 0
        return calculated_week
    
    def get_time_spent_formatted(self, obj):
        """Get formatted time spent."""
        if obj.time_spent:
            hours = obj.time_spent // 3600
            minutes = (obj.time_spent % 3600) // 60
            seconds = obj.time_spent % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "00:00:00"
    
    def get_week(self, obj):
        """Calculate week number from due_date and move_date."""
        if not obj.due_date or not obj.move or not obj.move.move_date:
            return 0
        
        from datetime import timedelta
        move_date = obj.move.move_date
        due_date = obj.due_date.date()
        
        # Calculate days difference
        days_diff = (move_date - due_date).days
        
        # Calculate week using the same formula as backend: N = (days_diff + 3) / 7
        # This reverses: due_date = (move_date - N weeks) + 3 days
        calculated_week = round((days_diff + 3) / 7)
        
        # Clamp to valid range (0-8)
        if calculated_week >= 8:
            return 8
        if calculated_week <= 0:
            return 0
        return calculated_week


class TaskListSerializer(serializers.ModelSerializer):
    """
    Serializer for task list.
    """
    assigned_to_name = serializers.SerializerMethodField()
    collaborator_name = serializers.SerializerMethodField()
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    week = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'category_display', 'priority_display',
            'completed', 'due_date', 'assigned_to_name', 'collaborator_name',
            'is_external', 'created_at', 'week'
        ]
        read_only_fields = [
            'id', 'category_display', 'priority_display', 'assigned_to_name', 
            'collaborator_name', 'created_at', 'week'
        ]
    
    def get_assigned_to_name(self, obj):
        """Get assigned user's full name."""
        if obj.assigned_to:
            return f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip()
        return None
    
    def get_collaborator_name(self, obj):
        """Get collaborator's full name."""
        if obj.collaborator:
            return f"{obj.collaborator.first_name} {obj.collaborator.last_name}".strip()
        return None


class TaskUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating a task.
    """
    
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'priority', 'completed', 'due_date',
            'subtasks', 'external_url'
        ]
    
    def validate_priority(self, value):
        """Validate task priority choice."""
        valid_choices = [choice[0] for choice in Task.PRIORITY_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid priority. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate_subtasks(self, value):
        """Validate subtasks list."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Subtasks must be a list")
        
        for subtask in value:
            if not isinstance(subtask, str):
                raise serializers.ValidationError("Each subtask must be a string")
            if len(subtask.strip()) == 0:
                raise serializers.ValidationError("Subtasks cannot be empty strings")
        
        return value
    
    def update(self, instance, validated_data):
        """Update task and set completed_at if completed."""
        if 'completed' in validated_data and validated_data['completed'] and not instance.completed:
            validated_data['completed_at'] = timezone.now()
        elif 'completed' in validated_data and not validated_data['completed']:
            validated_data['completed_at'] = None
        
        return super().update(instance, validated_data)


class TaskTimerCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a task timer.
    """
    task_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = TaskTimer
        fields = ['task_id', 'start_time', 'notes']
    
    def validate_task_id(self, value):
        """Validate that the task belongs to the user's move."""
        user = self.context['request'].user
        try:
            task = Task.objects.get(id=value, move__user=user)
            return task
        except Task.DoesNotExist:
            raise serializers.ValidationError("Task not found or doesn't belong to you")
    
    def create(self, validated_data):
        """Create a task timer."""
        task = validated_data.pop('task_id')
        user = self.context['request'].user
        return TaskTimer.objects.create(task=task, user=user, **validated_data)


class TaskTimerDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for task timer details.
    """
    task_title = serializers.CharField(source='task.title', read_only=True)
    user_name = serializers.SerializerMethodField()
    duration_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = TaskTimer
        fields = [
            'id', 'task_title', 'user_name', 'start_time', 'end_time',
            'duration', 'duration_formatted', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'task_title', 'user_name', 'duration_formatted', 'created_at']
    
    def get_user_name(self, obj):
        """Get user's full name."""
        return f"{obj.user.first_name} {obj.user.last_name}".strip()
    
    def get_duration_formatted(self, obj):
        """Get formatted duration."""
        if obj.duration:
            hours = obj.duration // 3600
            minutes = (obj.duration % 3600) // 60
            seconds = obj.duration % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "00:00:00"


class TaskTimerUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating a task timer (mainly for stopping timer).
    """
    
    class Meta:
        model = TaskTimer
        fields = ['end_time', 'notes']
    
    def update(self, instance, validated_data):
        """Update timer and calculate duration."""
        if 'end_time' in validated_data and validated_data['end_time']:
            if instance.start_time:
                duration = int((validated_data['end_time'] - instance.start_time).total_seconds())
                validated_data['duration'] = duration
        
        return super().update(instance, validated_data)


class TaskTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for task templates.
    """
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    location_display = serializers.CharField(source='get_location_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = TaskTemplate
        fields = [
            'id', 'title', 'description', 'category', 'category_display',
            'location', 'location_display', 'priority', 'priority_display',
            'is_external', 'external_url', 'subtasks', 'is_active'
        ]
        read_only_fields = [
            'id', 'category_display', 'location_display', 'priority_display'
        ]

