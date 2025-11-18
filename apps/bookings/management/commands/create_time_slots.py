"""
Management command to create default time slots.
"""
from django.core.management.base import BaseCommand
from apps.bookings.models import TimeSlot
from datetime import time


class Command(BaseCommand):
    help = 'Create default time slots for bookings'

    def handle(self, *args, **options):
        """Create default time slots."""
        
        # Clear existing time slots
        TimeSlot.objects.all().delete()
        
        # Define time slots (8 AM to 6 PM, 2-hour slots)
        time_slots = [
            {'start': time(8, 0), 'end': time(10, 0), 'price': 200.00},
            {'start': time(10, 0), 'end': time(12, 0), 'price': 200.00},
            {'start': time(12, 0), 'end': time(14, 0), 'price': 250.00},  # Premium lunch time
            {'start': time(14, 0), 'end': time(16, 0), 'price': 200.00},
            {'start': time(16, 0), 'end': time(18, 0), 'price': 200.00},
        ]
        
        created_count = 0
        for slot_data in time_slots:
            time_slot, created = TimeSlot.objects.get_or_create(
                start_time=slot_data['start'],
                end_time=slot_data['end'],
                defaults={
                    'price': slot_data['price'],
                    'is_active': True
                }
            )
            if created:
                created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} time slots'
            )
        )
