"""
Test script to test the booking API endpoint.
"""
import os
import sys
import django
from pathlib import Path
import json
import requests

# Set up Django environment
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'removealist_backend.settings')
django.setup()

# Import after Django setup
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.bookings.views import append_booking_to_sheet
from apps.bookings.models import Booking
from apps.moves.models import Move
from django.utils import timezone

User = get_user_model()

def test_append_to_sheet_directly():
    """Test the append_booking_to_sheet function directly with an existing booking."""
    try:
        # Try to get an existing booking
        booking = Booking.objects.first()
        
        if not booking:
            print("No bookings found in database. Creating test data...")
            
            # Create test user if needed
            user, created = User.objects.get_or_create(
                email="test@example.com",
                defaults={
                    "username": "testuser",
                    "first_name": "Test",
                    "last_name": "User",
                    "is_active": True
                }
            )
            if created:
                user.set_password("password123")
                user.save()
                print(f"Created test user: {user.email}")
            
            # Create test move
            move = Move.objects.create(
                user=user,
                current_location="123 Test St",
                destination_location="456 Example Ave",
                from_property_type="house",
                to_property_type="apartment",
                first_name="Test",
                last_name="User",
                email="test@example.com",
                status="planning"
            )
            print(f"Created test move: {move.id}")
            
            # Create test booking
            booking = Booking.objects.create(
                user=user,
                move=move,
                date=timezone.now().date(),
                start_time=timezone.now().time(),
                end_time=(timezone.now() + timezone.timedelta(hours=2)).time(),
                phone_number="1234567890",
                status="confirmed"
            )
            print(f"Created test booking: {booking.confirmation_number}")
        
        print(f"\nTesting append_booking_to_sheet with booking: {booking.confirmation_number}")
        result = append_booking_to_sheet(booking)
        
        if result:
            print("✅ Successfully added booking to Google Sheet")
        else:
            print("❌ Failed to add booking to Google Sheet")
            
    except Exception as e:
        print(f"Error in test_append_to_sheet_directly: {e}")

if __name__ == "__main__":
    test_append_to_sheet_directly()