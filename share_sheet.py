"""
Script to share the Google Sheet with a specific user.
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

def share_google_sheet(email):
    """Share the Google Sheet with a specific user."""
    try:
        # Get settings from Django
        SERVICE_ACCOUNT_FILE = settings.GOOGLE_SERVICE_ACCOUNT_JSON
        SHEET_ID = settings.GOOGLE_SHEET_ID
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets", 
                 "https://www.googleapis.com/auth/drive"]
        
        print(f"Using service account file: {SERVICE_ACCOUNT_FILE}")
        print(f"Using sheet ID: {SHEET_ID}")
        print(f"Accessing Google Sheet at: https://docs.google.com/spreadsheets/d/{SHEET_ID}/")
        
        # Create credentials with drive scope
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        
        # Authorize and get sheet
        client = gspread.authorize(creds)
        
        # Open the spreadsheet
        print(f"Opening spreadsheet...")
        spreadsheet = client.open_by_key(SHEET_ID)
        print(f"Spreadsheet title: {spreadsheet.title}")
        
        # Share the spreadsheet
        print(f"Sharing spreadsheet with {email}...")
        spreadsheet.share(
            email,
            perm_type='user',
            role='writer',
            notify=True,
            email_message="This is the RemoveAlist Booking Details spreadsheet shared from your Django application."
        )
        
        print(f"Successfully shared spreadsheet with {email}")
        print(f"You should receive an email invitation to access the spreadsheet.")
        print(f"You can also access it directly at: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
        
        return True
        
    except Exception as e:
        print(f"Error sharing Google Sheet: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python share_sheet.py YOUR_EMAIL@example.com")
        sys.exit(1)
    
    email = sys.argv[1]
    share_google_sheet(email)
