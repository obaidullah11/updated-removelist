"""
Views for booking and scheduling.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from django.conf import settings
from datetime import datetime, timedelta, time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import os
import pytz
import gspread

from .models import TimeSlot, Booking
from .serializers import (
    TimeSlotSerializer, BookingCreateSerializer,
    BookingDetailSerializer, BookingListSerializer
)
from apps.authentication.tasks import send_booking_confirmation_email
from apps.common.utils import success_response, error_response, paginated_response

def get_google_sheet():
    """
    Helper function to get the Google Sheet.
    """
    try:
        # Get settings from Django settings
        SERVICE_ACCOUNT_FILE = settings.GOOGLE_SERVICE_ACCOUNT_JSON
        SHEET_ID = settings.GOOGLE_SHEET_ID
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

        # Create credentials
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )

        # Authorize and get sheet
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SHEET_ID)

        # Try to use the "Bookings Data" worksheet if it exists, otherwise use sheet1
        try:
            sheet = spreadsheet.worksheet("Bookings Data")
            print("Using 'Bookings Data' worksheet")
        except:
            sheet = spreadsheet.sheet1
            print("Using default worksheet (Sheet1)")

        return sheet
    except Exception as e:
        print(f"Error getting Google Sheet: {e}")
        return None

def append_booking_to_sheet(booking):
    """
    Append booking + move details to Google Sheet
    Add labels if sheet is empty.
    """
    try:
        sheet = get_google_sheet()
        if not sheet:
            return False

        move = booking.move

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

        row = [
            str(booking.confirmation_number),
            booking.user.username,
            booking.user.email,
            booking.phone_number,
            str(booking.date),
            str(booking.start_time),
            str(booking.end_time),
            move.current_location or "",
            move.destination_location or "",
            move.from_property_type or "",
            move.to_property_type or "",
            move.special_items or "",
            move.additional_details or "",
            move.first_name or "",
            move.last_name or "",
            move.email or "",
            booking.status,
            str(booking.created_at),
        ]

        # Check if sheet has any records
        if len(sheet.get_all_values()) == 0:
            # Add headers first
            sheet.append_row(headers)

        # Append booking row
        sheet.append_row(row)

        print(f"Booking {booking.confirmation_number} added to Google Sheet successfully")
        return True

    except Exception as e:
        print(f"Google Sheets error: {e}")
        return False

def update_booking_status_in_sheet(booking):
    """
    Update booking status in Google Sheet.
    """
    try:
        sheet = get_google_sheet()
        if not sheet:
            return False

        # Get all values from the sheet
        all_values = sheet.get_all_values()
        if len(all_values) == 0:
            print("Sheet is empty, cannot update booking status")
            return False

        # Find the confirmation number column index
        headers = all_values[0]
        try:
            conf_num_col = headers.index("Confirmation Number")
            status_col = headers.index("Status")
        except ValueError:
            # Try to find by position if headers don't match exactly
            conf_num_col = 0  # Assuming first column is confirmation number
            status_col = 16   # Assuming 17th column is status (0-indexed)
            print(f"Using default column indices: conf_num_col={conf_num_col}, status_col={status_col}")

        # Find the row with the matching confirmation number
        found = False
        for i, row in enumerate(all_values[1:], start=1):  # Skip header row
            if i < len(all_values) and conf_num_col < len(row) and row[conf_num_col] == str(booking.confirmation_number):
                # Update the status cell
                sheet.update_cell(i + 1, status_col + 1, booking.status)  # +1 because gspread is 1-indexed
                found = True
                print(f"Updated booking {booking.confirmation_number} status to {booking.status} in Google Sheet")
                break

        if not found:
            print(f"Booking {booking.confirmation_number} not found in Google Sheet")
            return False

        return True

    except Exception as e:
        print(f"Error updating booking status in Google Sheet: {e}")
        return False

def get_google_calendar_service():
    """
    Helper function to get authenticated Google Calendar service.
    """
    try:
        # Get settings from Django settings
        SERVICE_ACCOUNT_FILE = settings.GOOGLE_SERVICE_ACCOUNT_JSON
        SCOPES = ["https://www.googleapis.com/auth/calendar"]

        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        return build("calendar", "v3", credentials=credentials)
    except Exception as e:
        print(f"Error creating Google Calendar service: {e}")
        return None


def delete_google_calendar_event(booking):
    """
    Delete the Google Calendar event for a specific booking using stored event ID.
    """
    try:
        # Get calendar ID from settings
        CALENDAR_ID = settings.GOOGLE_CALENDAR_ID

        # If we have the event ID stored, use it for direct deletion
        if booking.google_calendar_event_id:
            service = get_google_calendar_service()
            if not service:
                print("Could not create Google Calendar service")
                return False

            try:
                service.events().delete(
                    calendarId=CALENDAR_ID,
                    eventId=booking.google_calendar_event_id
                ).execute()

                print(f"Deleted Google Calendar event {booking.google_calendar_event_id} for booking {booking.confirmation_number}")
                return True

            except Exception as e:
                # Event might not exist anymore, clear the stored ID
                if "Not Found" in str(e):
                    print(f"Google Calendar event {booking.google_calendar_event_id} not found, clearing stored ID")
                    booking.google_calendar_event_id = None
                    booking.save()
                else:
                    print(f"Error deleting Google Calendar event: {e}")
                return False

        # Fallback: try to find and delete by searching (for backward compatibility)
        else:
            print(f"No Google Calendar event ID stored for booking {booking.confirmation_number}, attempting search-based deletion")
            return delete_google_calendar_event_by_search(booking)

    except Exception as e:
        print(f"Error in delete_google_calendar_event: {e}")
        return False


def delete_google_calendar_event_by_search(booking):
    """
    Fallback method to find and delete Google Calendar event by searching.
    """
    try:
        # Get calendar ID from settings
        CALENDAR_ID = settings.GOOGLE_CALENDAR_ID

        service = get_google_calendar_service()
        if not service:
            print("Could not create Google Calendar service")
            return False

        # Create timezone-aware datetime objects for the search
        tz = pytz.timezone("Asia/Karachi")
        start_datetime = tz.localize(datetime.combine(booking.date, booking.start_time))
        end_datetime = tz.localize(datetime.combine(booking.date, booking.end_time))

        # Search for events in the time range
        time_min = start_datetime.isoformat()
        time_max = end_datetime.isoformat()

        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        # Find the specific event for this booking
        for event in events:
            event_start = event['start'].get('dateTime', '')
            event_end = event['end'].get('dateTime', '')
            event_summary = event.get('summary', '')

            # Check if this event matches our booking
            if (event_summary.startswith(f"Move Booking - {booking.user.username}") and
                event_start.startswith(f"{booking.date}T{booking.start_time.strftime('%H:%M')}") and
                event_end.startswith(f"{booking.date}T{booking.end_time.strftime('%H:%M')}")):

                # Delete the event
                service.events().delete(
                    calendarId=CALENDAR_ID,
                    eventId=event['id']
                ).execute()

                print(f"Deleted Google Calendar event {event['id']} for booking {booking.confirmation_number}")
                return True

        print(f"No matching Google Calendar event found for booking {booking.confirmation_number}")
        return False

    except Exception as e:
        print(f"Error deleting Google Calendar event by search: {e}")
        return False


def get_free_slots(date, calendar_id):
    """
    Get free 30-min slots from Google Calendar between 09:00–20:00
    """
    # Get settings from Django settings
    SERVICE_ACCOUNT_FILE = settings.GOOGLE_SERVICE_ACCOUNT_JSON
    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    # Check if service account file exists
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(f"Google service account file not found: {SERVICE_ACCOUNT_FILE}")

    # Authenticate
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build("calendar", "v3", credentials=credentials)

    # Define working hours - create timezone-aware datetimes
    tz = pytz.timezone("Asia/Karachi")  # your working timezone
    start_of_day = tz.localize(datetime.combine(date, time(9, 0)))
    end_of_day = tz.localize(datetime.combine(date, time(20, 0)))

    # FreeBusy query
    freebusy_query = {
        "timeMin": start_of_day.isoformat(),
        "timeMax": end_of_day.isoformat(),
        "timeZone": "Asia/Karachi",
        "items": [{"id": calendar_id}],
    }
    busy_times = service.freebusy().query(body=freebusy_query).execute()
    busy_slots = busy_times["calendars"][calendar_id].get("busy", [])

    # Convert busy slots to datetime ranges
    busy_periods = [
        (
            datetime.fromisoformat(busy["start"].replace("Z", "+00:00")),
            datetime.fromisoformat(busy["end"].replace("Z", "+00:00")),
        )
        for busy in busy_slots
    ]

    # Generate 30-min slots
    slots = []
    start_time = start_of_day

    while start_time < end_of_day:
        slot_end = start_time + timedelta(minutes=30)

        # Check if slot overlaps with any busy period
        is_busy = any(
            start_time < busy_end and slot_end > busy_start
            for busy_start, busy_end in busy_periods
        )

        if not is_busy:
            slots.append(
                {
                    "start": start_time.strftime("%Y-%m-%d %H:%M"),
                    "end": slot_end.strftime("%Y-%m-%d %H:%M"),
                }
            )

        start_time = slot_end

    return slots


def get_mock_slots(date):
    """
    Generate mock time slots when Google Calendar is not available.
    Returns 30-minute slots from 9:00 AM to 8:00 PM.
    """
    slots = []
    tz = pytz.timezone("Asia/Karachi")
    
    # Create timezone-aware datetime for the date
    start_of_day = tz.localize(datetime.combine(date, time(9, 0)))
    end_of_day = tz.localize(datetime.combine(date, time(20, 0)))
    
    current_time = start_of_day
    while current_time < end_of_day:
        slot_end = current_time + timedelta(minutes=30)
        
        slots.append({
            "start": current_time.strftime("%Y-%m-%d %H:%M"),
            "end": slot_end.strftime("%Y-%m-%d %H:%M"),
        })
        
        current_time = slot_end
    
    return slots


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def available_slots(request):
    """
    Get available time slots for a specific date from Google Calendar.
    """
    date_str = request.GET.get("date")

    if not date_str:
        return error_response(
            "Date parameter required",
            {"date": ["This parameter is required"]},
            status.HTTP_400_BAD_REQUEST,
        )

    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return error_response(
            "Invalid date format",
            {"date": ["Date must be in YYYY-MM-DD format"]},
            status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get calendar ID from settings
        CALENDAR_ID = settings.GOOGLE_CALENDAR_ID
        slots = get_free_slots(date, CALENDAR_ID)
    except Exception as e:
        # Fallback to mock data if Google Calendar is not available
        print(f"Google Calendar not available, using mock data: {e}")
        slots = get_mock_slots(date)

    return success_response(
        "Available slots retrieved",
        {
            "date": date_str,
            "slots": slots,
        },
    )



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def book_slot(request):
    """
    Book a time slot for a move (no DB TimeSlot model required).
    Creates event on Google Calendar as well.
    """
    serializer = BookingCreateSerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        booking = serializer.save()

        # ---- GOOGLE CALENDAR EVENT ----
        try:
            # Get settings from Django settings
            SERVICE_ACCOUNT_FILE = settings.GOOGLE_SERVICE_ACCOUNT_JSON
            CALENDAR_ID = settings.GOOGLE_CALENDAR_ID
            SCOPES = ["https://www.googleapis.com/auth/calendar"]

            credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            service = build("calendar", "v3", credentials=credentials)

            event = {
                "summary": f"Move Booking - {booking.user.username}",
                "description": f"Phone: {booking.phone_number}, Confirmation: {booking.confirmation_number}",
                "start": {
                    "dateTime": f"{booking.date}T{booking.start_time}",
                    "timeZone": "Asia/Karachi",
                },
                "end": {
                    "dateTime": f"{booking.date}T{booking.end_time}",
                    "timeZone": "Asia/Karachi",
                },
            }

            created_event = service.events().insert(
                calendarId=CALENDAR_ID,
                body=event
            ).execute()
            booking.google_calendar_event_id = created_event['id']
            booking.save()
            print(f"Google Calendar event created: {created_event['id']}")
        except Exception as e:
            # Log but don't block booking
            print(f"Google Calendar error: {e}")

        # ---- SEND CONFIRMATION EMAIL ----
        booking_data = {
            'move_date': booking.date.strftime('%B %d, %Y'),
            'time_slot': booking.time_slot_display,
            'confirmation_number': booking.confirmation_number,
            'phone_number': booking.phone_number,
        }
        send_booking_confirmation_email(booking.user.id, booking_data)


        # ---- RETURN RESPONSE ----
        detail_serializer = BookingDetailSerializer(booking)
        sheet_result = append_booking_to_sheet(booking)
        response_data = detail_serializer.data
        response_data['google_sheet_added'] = sheet_result

        return success_response(
            "Booking requested successfully",
            response_data,
            status.HTTP_201_CREATED
        )

    return error_response(
        "Booking failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_bookings(request):
    """
    Get all bookings for the authenticated user.
    """
    bookings = Booking.objects.filter(user=request.user)

    # Check if pagination is requested
    if request.GET.get('page'):
        return paginated_response(
            bookings,
            BookingListSerializer,
            request,
            "Bookings retrieved successfully"
        )

    # Return all bookings without pagination
    serializer = BookingListSerializer(bookings, many=True)

    return success_response(
        "Bookings retrieved successfully",
        serializer.data
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def booking_detail(request, booking_id):
    """
    Get booking details by ID.
    """
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    serializer = BookingDetailSerializer(booking)

    return success_response(
        "Booking details retrieved",
        serializer.data
    )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def cancel_booking(request, booking_id):
    """
    Cancel a booking.
    """
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    # Check if booking can be cancelled
    if booking.status in ['completed', 'cancelled']:
        return error_response(
            "Cannot cancel booking",
            {'detail': ['This booking cannot be cancelled']},
            status.HTTP_400_BAD_REQUEST
        )

    # Try to delete the Google Calendar event first
    event_deleted = delete_google_calendar_event(booking)

    # Cancel the booking
    booking.status = 'cancelled'
    booking.save()

    # Update move status back to planning if needed
    if booking.move.status == 'scheduled':
        # Check if there are other active bookings for this move
        other_bookings = Booking.objects.filter(
            move=booking.move,
            status__in=['confirmed', 'in_progress']
        ).exclude(id=booking.id)

        if not other_bookings.exists():
            booking.move.status = 'planning'
            booking.move.save()

    serializer = BookingDetailSerializer(booking)

    # Update booking status in Google Sheet
    sheet_updated = update_booking_status_in_sheet(booking)

    # Include information about Google Calendar event deletion and Google Sheet update in response
    response_data = serializer.data
    if event_deleted:
        response_data['google_calendar_event'] = 'deleted'
    else:
        response_data['google_calendar_event'] = 'not_found_or_error'

    response_data['google_sheet_updated'] = sheet_updated

    return success_response(
        "Booking cancelled successfully",
        response_data
    )