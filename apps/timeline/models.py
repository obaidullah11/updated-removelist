"""
Models for timeline and task management.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from apps.moves.models import Move
from apps.common.utils import ChoicesMixin

User = get_user_model()


class TimelineEvent(models.Model, ChoicesMixin):
    """
    Model representing a timeline event for a move.
    """
    
    CATEGORY_CHOICES = [
        ('logistics', 'Logistics'),
        ('preparation', 'Preparation'),
        ('supplies', 'Supplies'),
        ('utilities', 'Utilities'),
        ('address_change', 'Address Change'),
        ('packing', 'Packing'),
        ('moving_day', 'Moving Day'),
    ]
    
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    move = models.ForeignKey(Move, on_delete=models.CASCADE, related_name='timeline_events')
    
    # Event details
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    days_from_move = models.IntegerField()  # Negative for days before, positive for days after
    completed = models.BooleanField(default=False)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    estimated_time = models.CharField(max_length=50, blank=True, null=True)  # e.g., "2-3 hours"
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'timeline_events'
        verbose_name = 'Timeline Event'
        verbose_name_plural = 'Timeline Events'
        ordering = ['days_from_move', 'priority']
    
    def __str__(self):
        return f"{self.title} ({self.days_from_move} days from move)"
    
    def save(self, *args, **kwargs):
        """Update move progress when event is saved."""
        super().save(*args, **kwargs)
        # Trigger progress calculation for the move
        if hasattr(self.move, 'calculate_progress'):
            self.move.calculate_progress()
    
    @property
    def due_date(self):
        """Calculate the due date based on move date and days_from_move."""
        from datetime import timedelta
        return self.move.move_date + timedelta(days=self.days_from_move)


class ChecklistItem(models.Model, ChoicesMixin):
    """
    Model representing a checklist item organized by weeks before move.
    """
    
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    move = models.ForeignKey(Move, on_delete=models.CASCADE, related_name='checklist_items')
    
    # Checklist details
    title = models.CharField(max_length=200)
    week = models.IntegerField()  # Weeks before move (8, 6, 4, 2, 1, 0)
    completed = models.BooleanField(default=False)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    is_custom = models.BooleanField(default=False)  # True for user-added tasks
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'checklist_items'
        verbose_name = 'Checklist Item'
        verbose_name_plural = 'Checklist Items'
        ordering = ['-week', 'priority', 'title']
    
    def __str__(self):
        return f"{self.title} (Week {self.week})"
    
    def save(self, *args, **kwargs):
        """Update move progress when item is saved."""
        super().save(*args, **kwargs)
        # Trigger progress calculation for the move
        if hasattr(self.move, 'calculate_progress'):
            self.move.calculate_progress()


class ChecklistTemplate(models.Model):
    """
    Model for default checklist templates that are created for new moves.
    """
    
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Template details
    title = models.CharField(max_length=200)
    week = models.IntegerField()  # Weeks before move
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'checklist_templates'
        verbose_name = 'Checklist Template'
        verbose_name_plural = 'Checklist Templates'
        ordering = ['-week', 'priority', 'title']
    
    def __str__(self):
        return f"{self.title} (Week {self.week})"
