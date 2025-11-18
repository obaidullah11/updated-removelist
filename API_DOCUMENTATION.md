# RemoveList API Documentation

## Overview

The RemoveList API is a RESTful web service that provides comprehensive moving management functionality. All endpoints return JSON responses in a consistent format.

## Base URL

```
http://localhost:8000/api/
```

## Authentication

The API uses JWT (JSON Web Token) authentication. Include the access token in the Authorization header:

```
Authorization: Bearer {access_token}
```

## Response Format

All API responses follow this consistent structure:

```json
{
  "success": true|false,
  "message": "Human-readable message",
  "data": {
    // Response data (null for errors)
  },
  "errors": {
    // Field-specific errors (only for validation failures)
  },
  "status": 200|400|401|403|404|500
}
```

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (validation errors) |
| 401 | Unauthorized (authentication required) |
| 403 | Forbidden (permission denied) |
| 404 | Not Found |
| 500 | Internal Server Error |

---

## Authentication Endpoints

### Register User

**POST** `/auth/register/email/`

Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "phone_number": "+1234567890",
  "password": "securePassword123",
  "confirm_password": "securePassword123",
  "first_name": "John",
  "last_name": "Doe",
  "agree_to_terms": true
}
```

**Success Response (201):**
```json
{
  "success": true,
  "message": "Registration successful! Please check your email for verification.",
  "data": {
    "user_id": "uuid",
    "email": "user@example.com",
    "verification_required": true
  }
}
```

### Login

**POST** `/auth/login/`

Authenticate user and receive JWT tokens.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Login successful!",
  "data": {
    "access_token": "jwt_token",
    "refresh_token": "refresh_token",
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "is_email_verified": true,
      "avatar": "url_or_null"
    }
  }
}
```

### Verify Email

**POST** `/auth/verify-email/`

Verify user email address with token.

**Request Body:**
```json
{
  "token": "verification_token"
}
```

### Refresh Token

**POST** `/auth/refresh/`

Refresh JWT access token.

**Request Body:**
```json
{
  "refresh_token": "refresh_token"
}
```

### Logout

**POST** `/auth/logout/`

**Headers:** `Authorization: Bearer {access_token}`

**Request Body:**
```json
{
  "refresh_token": "refresh_token"
}
```

### Get Profile

**GET** `/auth/profile/`

**Headers:** `Authorization: Bearer {access_token}`

**Success Response (200):**
```json
{
  "success": true,
  "message": "Profile retrieved successfully",
  "data": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1234567890",
    "avatar": "url_or_null",
    "is_email_verified": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### Update Profile

**PUT** `/auth/profile/`

**Headers:** `Authorization: Bearer {access_token}`

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890"
}
```

---

## Move Management Endpoints

### Create Move

**POST** `/move/create/`

**Headers:** `Authorization: Bearer {access_token}`

**Request Body:**
```json
{
  "move_date": "2024-04-15",
  "current_location": "123 Main St, New York, NY",
  "destination_location": "456 Oak Ave, Los Angeles, CA",
  "property_type": "apartment",
  "property_size": "2bedroom",
  "special_items": "Piano, artwork",
  "additional_details": "Third floor walkup",
  "first_name": "John",
  "last_name": "Doe",
  "email": "user@example.com"
}
```

**Property Types:**
- `apartment`, `house`, `townhouse`, `office`, `storage`, `other`

**Property Sizes:**
- `studio`, `1bedroom`, `2bedroom`, `3bedroom`, `4bedroom`
- `small_office`, `medium_office`, `large_office`

### Get Move Details

**GET** `/move/get/{move_id}/`

**Headers:** `Authorization: Bearer {access_token}`

### Get User Moves

**GET** `/move/user-moves/`

**Headers:** `Authorization: Bearer {access_token}`

**Query Parameters:**
- `page` (optional): Page number for pagination

### Update Move

**PUT** `/move/update/{move_id}/`

**Headers:** `Authorization: Bearer {access_token}`

### Delete Move

**DELETE** `/move/delete/{move_id}/`

**Headers:** `Authorization: Bearer {access_token}`

---

## Booking Endpoints

### Get Available Time Slots

**GET** `/booking/slots/?date=2024-04-15`

**Headers:** `Authorization: Bearer {access_token}`

**Success Response (200):**
```json
{
  "success": true,
  "message": "Available slots retrieved",
  "data": {
    "date": "2024-04-15",
    "slots": [
      {
        "id": 1,
        "start_time": "08:00",
        "end_time": "10:00",
        "available": true,
        "price": 200
      }
    ]
  }
}
```

### Book Time Slot

**POST** `/booking/book/`

**Headers:** `Authorization: Bearer {access_token}`

**Request Body:**
```json
{
  "move_id": "move_uuid",
  "time_slot": 1,
  "phone_number": "+1234567890"
}
```

### Get User Bookings

**GET** `/booking/user-bookings/`

**Headers:** `Authorization: Bearer {access_token}`

### Cancel Booking

**PATCH** `/booking/{booking_id}/cancel/`

**Headers:** `Authorization: Bearer {access_token}`

---

## Inventory Management Endpoints

### Get Rooms

**GET** `/inventory/rooms/?move_id={move_id}`

**Headers:** `Authorization: Bearer {access_token}`

### Create Room

**POST** `/inventory/rooms/`

**Headers:** `Authorization: Bearer {access_token}`

**Request Body:**
```json
{
  "name": "Living Room",
  "type": "living_room",
  "move_id": "move_uuid"
}
```

**Room Types:**
- `living_room`, `kitchen`, `bedroom`, `bathroom`
- `office`, `garage`, `basement`, `attic`, `other`

### Update Room

**PUT** `/inventory/rooms/{room_id}/`

**Headers:** `Authorization: Bearer {access_token}`

**Request Body:**
```json
{
  "name": "Master Living Room",
  "items": ["Sofa", "Coffee Table", "TV Stand", "Bookshelf"],
  "boxes": 6,
  "heavy_items": 3
}
```

### Mark Room as Packed

**PATCH** `/inventory/rooms/{room_id}/packed/`

**Headers:** `Authorization: Bearer {access_token}`

**Request Body:**
```json
{
  "packed": true
}
```

### Upload Room Image

**POST** `/inventory/rooms/{room_id}/image/`

**Headers:** `Authorization: Bearer {access_token}`

**Content-Type:** `multipart/form-data`

**Request Body:**
```
image: [file]
```

---

## Timeline & Checklist Endpoints

### Get Timeline Events

**GET** `/timeline/events/?move_id={move_id}`

**Headers:** `Authorization: Bearer {access_token}`

### Update Timeline Event

**PATCH** `/timeline/events/{event_id}/`

**Headers:** `Authorization: Bearer {access_token}`

**Request Body:**
```json
{
  "completed": true
}
```

### Get Checklist Items

**GET** `/checklist/items/?move_id={move_id}`

**Headers:** `Authorization: Bearer {access_token}`

**Success Response (200):**
```json
{
  "success": true,
  "message": "Checklist items retrieved",
  "data": [
    {
      "week": 8,
      "title": "8 Weeks Before",
      "subtitle": "Research & Planning",
      "progress": 100,
      "tasks": [
        {
          "id": "task_uuid",
          "title": "Research moving companies",
          "completed": true,
          "priority": "high",
          "week": 8
        }
      ]
    }
  ]
}
```

### Update Checklist Item

**PATCH** `/checklist/items/{item_id}/`

**Headers:** `Authorization: Bearer {access_token}`

**Request Body:**
```json
{
  "completed": true
}
```

### Add Custom Task

**POST** `/checklist/items/`

**Headers:** `Authorization: Bearer {access_token}`

**Request Body:**
```json
{
  "title": "Custom task",
  "week": 6,
  "priority": "medium",
  "move_id": "move_uuid"
}
```

---

## File Management Endpoints

### Upload Floor Plan

**POST** `/files/floor-plans/`

**Headers:** `Authorization: Bearer {access_token}`

**Content-Type:** `multipart/form-data`

**Request Body:**
```
file: [file]
move_id: "move_uuid"
location_type: "current" | "new"
```

### Upload Document

**POST** `/files/documents/`

**Headers:** `Authorization: Bearer {access_token}`

**Content-Type:** `multipart/form-data`

**Request Body:**
```
file: [file]
document_type: "contract" | "inventory" | "insurance" | "other"
move_id: "move_uuid"
```

### Get User Files

**GET** `/files/user-files/?move_id={move_id}`

**Headers:** `Authorization: Bearer {access_token}`

**Success Response (200):**
```json
{
  "success": true,
  "message": "Files retrieved successfully",
  "data": {
    "floor_plans": [
      {
        "id": "file_uuid",
        "filename": "current_floor_plan.pdf",
        "url": "https://example.com/files/floor_plans/file_uuid.pdf",
        "location_type": "current",
        "uploaded_at": "2024-01-01T00:00:00Z"
      }
    ],
    "documents": [
      {
        "id": "file_uuid",
        "filename": "moving_contract.pdf",
        "url": "https://example.com/files/documents/file_uuid.pdf",
        "document_type": "contract",
        "uploaded_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

### Delete File

**DELETE** `/files/{file_id}/`

**Headers:** `Authorization: Bearer {access_token}`

---

## Validation Rules

### Email Format
- Must be valid email format
- Must be unique in the system

### Phone Number Format
- Must start with `+` followed by country code
- Total length: 10-15 digits after country code
- Regex: `^\+\d{10,15}$`

### Password Requirements
- Minimum 6 characters
- No maximum length restriction

### Name Fields
- Minimum 3 characters
- No special character restrictions

### Date Validation
- Move dates must be in the future
- Format: YYYY-MM-DD

### File Upload Requirements
- Max size: 10MB
- Supported formats: PNG, JPG, JPEG, PDF
- File name sanitization applied

---

## Rate Limiting

- **Auth endpoints:** 5 requests/minute per IP
- **General endpoints:** 100 requests/minute per user

---

## Pagination

For endpoints that support pagination, use the `page` query parameter:

```
GET /api/move/user-moves/?page=2
```

Paginated responses include:
```json
{
  "success": true,
  "message": "Data retrieved successfully",
  "data": {
    "results": [...],
    "count": 100,
    "next": "https://api.example.com/endpoint/?page=3",
    "previous": "https://api.example.com/endpoint/?page=1",
    "page": 2,
    "total_pages": 10
  }
}
```

---

## Health Check

**GET** `/health/`

Check API health status.

**Response (200):**
```json
{
  "success": true,
  "message": "RemoveList API is healthy",
  "status": "ok"
}
```
