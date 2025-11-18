"""
Test script to verify the cancel booking functionality updates the Google Sheet.
"""
import os
import sys
import django
import uuid
from pathlib import Path

# Set up Django environment
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'removealist_backend.settings')
django.setup()

# Import after Django setup
from django.contrib.auth import get_user_model
from apps.bookings.models import Booking
from apps.bookings.views import update_booking_status_in_sheet, get_google_sheet
from django.utils import timezone

User = get_user_model()

def test_update_booking_status():
    """Test updating a booking status in Google Sheets."""
    try:
        # Try to get an existing booking
        booking = Booking.objects.filter(status='confirmed').first() or Booking.objects.filter(status='requested').first()
        
        if not booking:
            print("No active bookings found to test with.")
            return False
        
        print(f"\nFound booking: {booking.confirmation_number}, current status: {booking.status}")
        
        # First, verify we can access the Google Sheet
        sheet = get_google_sheet()
        if not sheet:
            print("Failed to access Google Sheet")
            return False
            
        print("Successfully accessed Google Sheet")
        
        # Get the current status from the sheet
        all_values = sheet.get_all_values()
        if len(all_values) == 0:
            print("Sheet is empty")
            return False
            
        # Find the confirmation number column index
        headers = all_values[0]
        try:
            conf_num_col = headers.index("Confirmation Number")
            status_col = headers.index("Status")
        except ValueError:
            # Try to find by position if headers don't match exactly
            conf_num_col = 0
            status_col = 16
            print(f"Using default column indices: conf_num_col={conf_num_col}, status_col={status_col}")
        
        # Find the current status in the sheet
        current_sheet_status = None
        row_index = None
        for i, row in enumerate(all_values[1:], start=1):
            if i < len(all_values) and conf_num_col < len(row) and row[conf_num_col] == str(booking.confirmation_number):
                if status_col < len(row):
                    current_sheet_status = row[status_col]
                    row_index = i
                break
                
        print(f"Current status in sheet: {current_sheet_status}, row index: {row_index}")
        
        # Now test updating the status
        print(f"Updating booking status to 'cancelled'...")
        
        # Save the original status to restore later
        original_status = booking.status
        
        # Update the booking status
        booking.status = 'cancelled'
        
        # Update the status in the sheet
        result = update_booking_status_in_sheet(booking)
        
        if result:
            print("✅ Successfully updated booking status in Google Sheet")
            
            # Verify the update
            updated_values = sheet.get_all_values()
            updated_status = None
            if row_index is not None and row_index < len(updated_values) and status_col < len(updated_values[row_index]):
                updated_status = updated_values[row_index][status_col]
                
            print(f"Updated status in sheet: {updated_status}")
            
            if updated_status == 'cancelled':
                print("✅ Status correctly updated to 'cancelled' in the sheet")
            else:
                print("❌ Status not updated correctly in the sheet")
        else:
            print("❌ Failed to update booking status in Google Sheet")
        
        # Restore the original status
        booking.status = original_status
        booking.save()
        print(f"Restored booking status to: {original_status}")
        
        # Restore the original status in the sheet
        if row_index is not None:
            sheet.update_cell(row_index + 1, status_col + 1, original_status)
            print(f"Restored sheet status to: {original_status}")
            
        return result
    
    except Exception as e:
        print(f"Error in test_update_booking_status: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_update_booking_status()
