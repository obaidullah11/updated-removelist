"""
Models for file upload and storage.
"""
import uuid
import os
from django.db import models
from django.contrib.auth import get_user_model
from apps.moves.models import Move
from apps.common.utils import ChoicesMixin, sanitize_filename
from apps.common.validators import validate_file_size, validate_document_file

User = get_user_model()


def floor_plan_upload_path(instance, filename):
    """Generate upload path for floor plans."""
    filename = sanitize_filename(filename)
    return f'floor_plans/{instance.move.user.id}/{instance.move.id}/{filename}'


def document_upload_path(instance, filename):
    """Generate upload path for documents."""
    filename = sanitize_filename(filename)
    return f'documents/{instance.move.user.id}/{instance.move.id}/{filename}'


class FloorPlan(models.Model, ChoicesMixin):
    """
    Model for floor plan files.
    """
    
    LOCATION_TYPE_CHOICES = [
        ('current', 'Current Location'),
        ('new', 'New Location'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    move = models.ForeignKey(Move, on_delete=models.CASCADE, related_name='floor_plans')
    
    # File details
    file = models.FileField(
        upload_to=floor_plan_upload_path,
        validators=[validate_file_size, validate_document_file]
    )
    filename = models.CharField(max_length=255)
    size = models.BigIntegerField()  # File size in bytes
    location_type = models.CharField(max_length=10, choices=LOCATION_TYPE_CHOICES)
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'floor_plans'
        verbose_name = 'Floor Plan'
        verbose_name_plural = 'Floor Plans'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.filename} ({self.get_location_type_display()}) - {self.move}"
    
    def save(self, *args, **kwargs):
        """Set filename and size on save."""
        if self.file:
            self.filename = os.path.basename(self.file.name)
            self.size = self.file.size
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Delete file from storage when model is deleted."""
        if self.file:
            self.file.delete(save=False)
        super().delete(*args, **kwargs)


class Document(models.Model, ChoicesMixin):
    """
    Model for document files.
    """
    
    DOCUMENT_TYPE_CHOICES = [
        ('contract', 'Contract'),
        ('inventory', 'Inventory'),
        ('insurance', 'Insurance'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    move = models.ForeignKey(Move, on_delete=models.CASCADE, related_name='documents')
    
    # File details
    file = models.FileField(
        upload_to=document_upload_path,
        validators=[validate_file_size, validate_document_file]
    )
    filename = models.CharField(max_length=255)
    size = models.BigIntegerField()  # File size in bytes
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'documents'
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.filename} ({self.get_document_type_display()}) - {self.move}"
    
    def save(self, *args, **kwargs):
        """Set filename and size on save."""
        if self.file:
            self.filename = os.path.basename(self.file.name)
            self.size = self.file.size
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Delete file from storage when model is deleted."""
        if self.file:
            self.file.delete(save=False)
        super().delete(*args, **kwargs)
