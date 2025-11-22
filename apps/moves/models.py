"""
Models for move management.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.common.validators import validate_future_date
from apps.common.utils import ChoicesMixin

User = get_user_model()


class Move(models.Model, ChoicesMixin):
    """
    Model representing a user's move.
    """
    
    PROPERTY_TYPE_CHOICES = [
        ('apartment', 'Apartment'),
        ('house', 'House'),
        ('townhouse', 'Townhouse'),
        ('office', 'Office'),
        ('storage', 'Storage'),
        ('other', 'Other'),
    ]
    
    PROPERTY_SIZE_CHOICES = [
        ('studio', 'Studio'),
        ('1bedroom', '1 Bedroom'),
        ('2bedroom', '2 Bedroom'),
        ('3bedroom', '3 Bedroom'),
        ('4bedroom', '4+ Bedroom'),
        ('small_office', 'Small Office'),
        ('medium_office', 'Medium Office'),
        ('large_office', 'Large Office'),
    ]
    
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    DISCOUNT_TYPE_CHOICES = [
        ('none', 'No Discount'),
        ('first_home_buyer', 'First Home Buyer'),
        ('seniors', 'Seniors Discount'),
        ('single_parent', 'Single Parent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='moves')
    
    # Move details
    move_date = models.DateField(validators=[validate_future_date])
    current_location = models.TextField()
    destination_location = models.TextField()
    from_property_type = models.CharField(max_length=20, choices=PROPERTY_TYPE_CHOICES)
    to_property_type = models.CharField(max_length=20, choices=PROPERTY_TYPE_CHOICES)
    
    # Property floor maps
    current_property_floor_map = models.ImageField(upload_to='property_floor_maps/', blank=True, null=True, help_text="Floor map of current property")
    new_property_floor_map = models.ImageField(upload_to='property_floor_maps/', blank=True, null=True, help_text="Floor map of new property")
    
    # Discount information
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='none')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Budget information
    estimated_budget = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Estimated moving budget")
    
    special_items = models.TextField(blank=True, null=True)
    additional_details = models.TextField(blank=True, null=True)
    
    # Contact info (can be different from user's info)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField()
    
    # Status and progress
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    progress = models.IntegerField(default=0)  # Percentage (0-100)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'moves'
        verbose_name = 'Move'
        verbose_name_plural = 'Moves'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Move from {self.current_location} to {self.destination_location} on {self.move_date}"
    
    def calculate_progress(self):
        """
        Calculate move progress based on completed tasks and checklist items.
        """
        # This will be implemented when we have timeline and checklist models
        total_tasks = 0
        completed_tasks = 0
        
        # Count timeline events
        if hasattr(self, 'timeline_events'):
            timeline_events = self.timeline_events.all()
            total_tasks += timeline_events.count()
            completed_tasks += timeline_events.filter(completed=True).count()
        
        # Count checklist items
        if hasattr(self, 'checklist_items'):
            checklist_items = self.checklist_items.all()
            total_tasks += checklist_items.count()
            completed_tasks += checklist_items.filter(completed=True).count()
        
        # Count inventory rooms (if packed)
        if hasattr(self, 'inventory_rooms'):
            rooms = self.inventory_rooms.all()
            total_tasks += rooms.count()
            completed_tasks += rooms.filter(packed=True).count()
        
        if total_tasks > 0:
            progress = int((completed_tasks / total_tasks) * 100)
            self.progress = min(progress, 100)
            self.save(update_fields=['progress'])
        
        return self.progress
    
    @property
    def is_upcoming(self):
        """Check if the move is upcoming (within 30 days)."""
        return (self.move_date - timezone.now().date()).days <= 30
    
    @property
    def days_until_move(self):
        """Get days until move date."""
        return (self.move_date - timezone.now().date()).days
        
    def clean(self):
        """Validate model fields."""
        super().clean()
        # Removed URL domain validation - allow any URLs
    
    def calculate_discount_amount(self, base_amount):
        """Calculate discount amount based on type."""
        if self.discount_type == 'none':
            return 0
        return (base_amount * self.discount_percentage) / 100
    
    def get_final_amount(self, base_amount):
        """Get final amount after discount."""
        discount = self.calculate_discount_amount(base_amount)
        return base_amount - discount


class MoveCollaborator(models.Model):
    """Model for move collaborators (family, friends)"""
    
    ROLE_CHOICES = [
        ('owner', 'Move Owner'),
        ('family', 'Family Member'),
        ('friend', 'Friend'),
        ('helper', 'Helper'),
    ]
    
    PERMISSION_CHOICES = [
        ('view_tasks', 'View Tasks Only'),
        ('edit_tasks', 'Edit Tasks'),
        ('full_access', 'Full Access (No Budget)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    move = models.ForeignKey(Move, on_delete=models.CASCADE, related_name='collaborators')
    email = models.EmailField()
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='helper')
    permissions = models.CharField(max_length=20, choices=PERMISSION_CHOICES, default='view_tasks')
    
    # Invitation status
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    invitation_token = models.CharField(max_length=100, unique=True, blank=True, null=True)
    
    # User reference (if they have an account)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='collaborations')
    
    class Meta:
        unique_together = ['move', 'email']
        db_table = 'move_collaborators'
        verbose_name = 'Move Collaborator'
        verbose_name_plural = 'Move Collaborators'
        
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email}) - {self.role}"
        
    def save(self, *args, **kwargs):
        """Generate invitation token if not present."""
        if not self.invitation_token:
            import secrets
            self.invitation_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)


class TaskAssignment(models.Model):
    """Assign tasks to collaborators"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timeline_event = models.ForeignKey('timeline.TimelineEvent', on_delete=models.CASCADE, related_name='assignments')
    collaborator = models.ForeignKey(MoveCollaborator, on_delete=models.CASCADE, related_name='assigned_tasks')
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ['timeline_event', 'collaborator']
        db_table = 'task_assignments'
        verbose_name = 'Task Assignment'
        verbose_name_plural = 'Task Assignments'
        
    def __str__(self):
        return f"Task: {self.timeline_event.title} assigned to {self.collaborator.first_name}"


class MoveExpense(models.Model):
    """
    Model representing an expense for a move (ledger entry).
    """
    
    CATEGORY_CHOICES = [
        ('moving_company', 'Moving Company'),
        ('packing_supplies', 'Packing Supplies'),
        ('storage', 'Storage'),
        ('utilities', 'Utilities Setup'),
        ('cleaning', 'Cleaning Services'),
        ('insurance', 'Insurance'),
        ('transportation', 'Transportation'),
        ('food', 'Food & Meals'),
        ('accommodation', 'Accommodation'),
        ('other', 'Other'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    move = models.ForeignKey(Move, on_delete=models.CASCADE, related_name='expenses')
    
    # Expense details
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash')
    expense_date = models.DateField(default=timezone.now)
    receipt = models.ImageField(upload_to='expense_receipts/', blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'move_expenses'
        verbose_name = 'Move Expense'
        verbose_name_plural = 'Move Expenses'
        ordering = ['-expense_date', '-created_at']
    
    def __str__(self):
        return f"{self.description} - ${self.amount} ({self.move})"
