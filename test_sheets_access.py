"""
Test script to verify Google Sheets integration and fix sheet structure.
"""
import os
import sys
import django
from pathlib import Path

# Set up Django environment
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'removealist_backend.settings')
django.setup()

# Import after Django setup
from django.conf import settings
from google.oauth2.service_account import Credentials
import gspread

def test_and_fix_google_sheets():
    """Test accessing and writing to Google Sheets, and fix sheet structure if needed."""
    try:
        # Get settings from Django
        SERVICE_ACCOUNT_FILE = settings.GOOGLE_SERVICE_ACCOUNT_JSON
        SHEET_ID = settings.GOOGLE_SHEET_ID
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
        
        print(f"Using service account file: {SERVICE_ACCOUNT_FILE}")
        print(f"Using sheet ID: {SHEET_ID}")
        print(f"Accessing Google Sheet at: https://docs.google.com/spreadsheets/d/{SHEET_ID}/")
        
        # Create credentials
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        
        # Authorize and get sheet
        client = gspread.authorize(creds)
        
        # Try to open the spreadsheet
        print("Opening spreadsheet...")
        spreadsheet = client.open_by_key(SHEET_ID)
        print(f"Spreadsheet title: {spreadsheet.title}")
        
        # Get the first worksheet
        sheet = spreadsheet.sheet1
        print(f"Worksheet title: {sheet.title}")
        
        # Test reading
        print("\nCurrent data in sheet:")
        values = sheet.get_all_values()
        if values:
            print(f"Sheet has {len(values)} rows")
            
            # Check if data is offset (not starting from column A)
            first_row = values[0] if values else []
            offset_detected = False
            offset_column = 0
            
            for i, cell in enumerate(first_row):
                if cell and cell.strip():
                    offset_column = i
                    if i > 0:
                        offset_detected = True
                    break
            
            if offset_detected:
                print(f"WARNING: Data appears to be offset, starting at column {chr(65 + offset_column)}")
                print("Checking if we need to fix the sheet structure...")
                
                # Check if there's actual data in the offset columns
                has_meaningful_data = False
                for row in values:
                    if any(cell.strip() for cell in row[:offset_column]):
                        has_meaningful_data = True
                        break
                
                if not has_meaningful_data:
                    print("No meaningful data found in offset columns. Creating a new sheet with proper structure...")
                    
                    # Create a new sheet
                    new_sheet = spreadsheet.add_worksheet(title="Bookings Data", rows=100, cols=20)
                    print(f"Created new worksheet: {new_sheet.title}")
                    
                    # Add headers
                    headers = [
                        "Confirmation Number",
                        "Username",
                        "User Email",
                        "Phone Number",
                        "Date",
                        "Start Time",
                        "End Time",
                        "Current Location",
                        "Destination Location",
                        "From Property Type",
                        "To Property Type",
                        "Special Items",
                        "Additional Details",
                        "First Name",
                        "Last Name",
                        "Email",
                        "Status",
                        "Created At",
                    ]
                    new_sheet.append_row(headers)
                    print("Added headers to new sheet")
                    
                    # Add test data
                    test_row = ["TEST123", "testuser", "test@example.com", "1234567890", 
                               "2023-10-01", "10:00:00", "11:00:00", 
                               "123 Test St", "456 Example Ave", "house", "apartment",
                               "Special items", "Additional details", "Test", "User",
                               "test@example.com", "confirmed", "2023-10-01 10:00:00"]
                    new_sheet.append_row(test_row)
                    print("Added test data to new sheet")
                    
                    print(f"\nPlease use this new sheet for your data: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid={new_sheet.id}")
                    return True
            
            print(f"First row: {first_row}")
            if len(values) > 1:
                print(f"Second row: {values[1]}")
        else:
            print("Sheet is empty")
        
        # Test writing
        test_row = ["TEST", "This is a test", "From test script", str(os.getlogin()), "Will be removed"]
        print(f"\nAppending test row: {test_row}")
        sheet.append_row(test_row)
        print("Test row added successfully")
        
        # Verify the row was added
        updated_values = sheet.get_all_values()
        print(f"Sheet now has {len(updated_values)} rows")
        
        print("\nGoogle Sheets integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error testing Google Sheets access: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_and_fix_google_sheets()