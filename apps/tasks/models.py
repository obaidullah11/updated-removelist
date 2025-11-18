"""
Models for task management system.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from apps.moves.models import Move, MoveCollaborator
from apps.common.utils import ChoicesMixin

User = get_user_model()


class Task(models.Model, ChoicesMixin):
    """
    Model representing a task in the task management system.
    """
    
    CATEGORY_CHOICES = [
        ('general', 'General'),
        ('council', 'Council'),
        ('address_change', 'Address Change'),
        ('first_night', 'First Night'),
        ('utilities', 'Utilities'),
        ('electricity', 'Electricity'),
        ('gas', 'Gas'),
        ('water', 'Water'),
        ('internet', 'Internet'),
        ('phone', 'Phone'),
        ('insurance', 'Insurance'),
        ('vehicles', 'Vehicles'),
        ('registration', 'Registration'),
        ('garage_sale', 'Garage Sale'),
        ('packing', 'Packing'),
        ('cleaning', 'Cleaning'),
    ]
    
    LOCATION_CHOICES = [
        ('current', 'Current Address'),
        ('new', 'New Address'),
        ('utilities', 'Utilities'),
        ('vehicles', 'Vehicles'),
        ('garage_sale', 'Garage Sale'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    move = models.ForeignKey(Move, on_delete=models.CASCADE, related_name='tasks')
    
    # Task details
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES, default='current')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Task status
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    
    # Assignment
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='task_assignments')
    collaborator = models.ForeignKey(MoveCollaborator, on_delete=models.SET_NULL, null=True, blank=True, related_name='task_assignments')
    
    # External task (like council booking)
    is_external = models.BooleanField(default=False)
    external_url = models.URLField(blank=True, null=True)
    
    # Subtasks
    subtasks = models.JSONField(default=list, blank=True)
    
    # Time tracking
    time_spent = models.IntegerField(default=0)  # in seconds
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tasks'
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'
        ordering = ['-priority', 'due_date', 'created_at']
    
    def __str__(self):
        return f"{self.title} - {self.move}"
    
    def save(self, *args, **kwargs):
        """Update move progress when task is saved."""
        super().save(*args, **kwargs)
        # Trigger progress calculation for the move
        if hasattr(self.move, 'calculate_progress'):
            self.move.calculate_progress()


class TaskTimer(models.Model):
    """
    Model for tracking time spent on tasks.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='timers')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_timers')
    
    # Timer details
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(default=0)  # in seconds
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'task_timers'
        verbose_name = 'Task Timer'
        verbose_name_plural = 'Task Timers'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Timer for {self.task.title} - {self.duration}s"
    
    def save(self, *args, **kwargs):
        """Calculate duration when timer is saved."""
        if self.start_time and self.end_time:
            self.duration = int((self.end_time - self.start_time).total_seconds())
        super().save(*args, **kwargs)
        
        # Update task's total time spent
        if self.task:
            total_time = TaskTimer.objects.filter(task=self.task).aggregate(
                total=models.Sum('duration')
            )['total'] or 0
            self.task.time_spent = total_time
            self.task.save(update_fields=['time_spent'])


class TaskTemplate(models.Model):
    """
    Model for predefined task templates.
    """
    
    CATEGORY_CHOICES = Task.CATEGORY_CHOICES
    LOCATION_CHOICES = Task.LOCATION_CHOICES
    PRIORITY_CHOICES = Task.PRIORITY_CHOICES
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Template details
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # External task details
    is_external = models.BooleanField(default=False)
    external_url = models.URLField(blank=True, null=True)
    
    # Subtasks
    subtasks = models.JSONField(default=list, blank=True)
    
    # Template status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'task_templates'
        verbose_name = 'Task Template'
        verbose_name_plural = 'Task Templates'
        ordering = ['category', 'priority', 'title']
    
    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"
    
    def create_task_for_move(self, move, assigned_to=None, collaborator=None):
        """Create a task from this template for a specific move."""
        return Task.objects.create(
            move=move,
            title=self.title,
            description=self.description,
            category=self.category,
            location=self.location,
            priority=self.priority,
            is_external=self.is_external,
            external_url=self.external_url,
            subtasks=self.subtasks.copy() if self.subtasks else [],
            assigned_to=assigned_to,
            collaborator=collaborator
        )
