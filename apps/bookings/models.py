"""
Models for booking and scheduling.
"""
import uuid
import random
import string
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from apps.moves.models import Move
from apps.common.utils import ChoicesMixin

User = get_user_model()


class TimeSlot(models.Model):
    """
    Model representing available time slots for bookings.
    """
    id = models.AutoField(primary_key=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=200.00)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'time_slots'
        verbose_name = 'Time Slot'
        verbose_name_plural = 'Time Slots'
        ordering = ['start_time']

    def __str__(self):
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"

    def is_available_on_date(self, date):
        """Check if this time slot is available on a specific date."""
        return not Booking.objects.filter(
            time_slot=self,
            date=date,
            status__in=['confirmed', 'in_progress']
        ).exists()


class Booking(models.Model, ChoicesMixin):
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('requested', 'Requested'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    move = models.ForeignKey(Move, on_delete=models.CASCADE, related_name='bookings')

    # Instead of FK, store actual times
    start_time = models.TimeField()
    end_time = models.TimeField()

    # Booking details
    date = models.DateField()
    phone_number = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^[\+\d\s\-\(\)]{8,20}$',
                message='Phone number must be 8-20 characters and can include +, spaces, hyphens, and parentheses'
            )
        ]
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    confirmation_number = models.CharField(max_length=10, unique=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    google_calendar_event_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'bookings'
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'
        ordering = ['-created_at']
        unique_together = ['date', 'start_time', 'end_time']  # prevent double booking

    def __str__(self):
        return f"Booking {self.confirmation_number} - {self.date} {self.start_time}-{self.end_time}"

    def save(self, *args, **kwargs):
        if not self.confirmation_number:
            self.confirmation_number = self.generate_confirmation_number()
        super().save(*args, **kwargs)

    @property
    def time_slot_display(self):
        """Return formatted time slot display."""
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"

    def generate_confirmation_number(self):
        while True:
            confirmation = 'BK' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not Booking.objects.filter(confirmation_number=confirmation).exists():
                return confirmation

    @property
    def time_slot_display(self):
        """Return formatted time slot string."""
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"
