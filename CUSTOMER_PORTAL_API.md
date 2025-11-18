# RemoveAlist Customer Portal API Documentation

## Overview
This document provides comprehensive API documentation for the RemoveAlist Customer Portal backend system.

## Base URL
```
http://localhost:8000/api/
```

## Authentication
All protected endpoints require JWT authentication:
```
Authorization: Bearer <access_token>
```

## API Endpoints

### Authentication (`/api/auth/`)
- `POST /register/` - Register new user
- `POST /login/` - User login
- `POST /logout/` - User logout
- `POST /refresh/` - Refresh access token
- `POST /verify-email/` - Verify email address
- `POST /forgot-password/` - Request password reset
- `POST /reset-password/` - Reset password

### Moves (`/api/move/`)
- `GET /` - Get user's moves
- `POST /create/` - Create new move
- `GET /<move_id>/` - Get move details
- `PUT /<move_id>/update/` - Update move
- `DELETE /<move_id>/delete/` - Delete move
- `POST /invite-collaborator/` - Invite collaborator
- `GET /<move_id>/collaborators/` - Get move collaborators
- `DELETE /collaborator/<collaborator_id>/remove/` - Remove collaborator
- `POST /assign-task/` - Assign task to collaborator
- `GET /<move_id>/task-assignments/` - Get task assignments

### Inventory (`/api/inventory/`)

#### Rooms
- `GET /rooms/?move_id=<uuid>` - Get rooms for move
- `POST /rooms/` - Create room
- `GET /rooms/<room_id>/` - Get room details
- `PUT /rooms/<room_id>/` - Update room
- `PATCH /rooms/<room_id>/packed/` - Mark room as packed
- `DELETE /rooms/<room_id>/` - Delete room
- `POST /rooms/<room_id>/image/` - Upload room image

#### Boxes
- `GET /boxes/?move_id=<uuid>` - Get boxes for move
- `POST /boxes/` - Create box
- `GET /boxes/<box_id>/` - Get box details
- `PUT /boxes/<box_id>/` - Update box
- `DELETE /boxes/<box_id>/` - Delete box

#### Heavy Items
- `GET /heavy-items/?move_id=<uuid>` - Get heavy items for move
- `POST /heavy-items/` - Create heavy item
- `GET /heavy-items/<item_id>/` - Get heavy item details
- `PUT /heavy-items/<item_id>/` - Update heavy item
- `DELETE /heavy-items/<item_id>/` - Delete heavy item

#### High Value Items
- `GET /high-value-items/?move_id=<uuid>` - Get high value items for move
- `POST /high-value-items/` - Create high value item
- `GET /high-value-items/<item_id>/` - Get high value item details
- `PUT /high-value-items/<item_id>/` - Update high value item
- `DELETE /high-value-items/<item_id>/` - Delete high value item

#### Storage Items
- `GET /storage-items/?move_id=<uuid>` - Get storage items for move
- `POST /storage-items/` - Create storage item
- `GET /storage-items/<item_id>/` - Get storage item details
- `PUT /storage-items/<item_id>/` - Update storage item
- `DELETE /storage-items/<item_id>/` - Delete storage item

### Tasks (`/api/tasks/`)
- `GET /?move_id=<uuid>` - Get tasks for move
- `POST /create/` - Create task
- `GET /<task_id>/` - Get task details
- `PUT /<task_id>/update/` - Update task
- `DELETE /<task_id>/delete/` - Delete task
- `POST /from-template/` - Create task from template

#### Task Timers
- `GET /timers/?task_id=<uuid>` - Get task timers
- `POST /timers/start/` - Start task timer
- `PUT /timers/<timer_id>/stop/` - Stop task timer
- `GET /timers/active/` - Get active timer

#### Task Templates
- `GET /templates/` - Get task templates
- `GET /templates/<template_id>/` - Get task template details

### Services (`/api/services/`)
- `GET /?move_id=<uuid>` - Get available services
- `GET /<service_id>/` - Get service details
- `GET /categories/` - Get service categories

#### Service Bookings
- `GET /bookings/?move_id=<uuid>` - Get service bookings
- `POST /bookings/create/` - Create service booking
- `GET /bookings/<booking_id>/` - Get booking details
- `PUT /bookings/<booking_id>/update/` - Update booking
- `DELETE /bookings/<booking_id>/cancel/` - Cancel booking

#### Service Reviews
- `GET /reviews/?provider_id=<uuid>` - Get provider reviews
- `POST /reviews/create/` - Create service review
- `GET /reviews/<review_id>/` - Get review details
- `PUT /reviews/<review_id>/update/` - Update review
- `DELETE /reviews/<review_id>/delete/` - Delete review

#### Service Quotes
- `GET /quotes/?booking_id=<uuid>` - Get service quotes
- `GET /quotes/<quote_id>/` - Get quote details

### Timeline (`/api/timeline/`)
- `GET /?move_id=<uuid>` - Get timeline events for move
- `POST /create/` - Create timeline event
- `GET /<event_id>/` - Get timeline event details
- `PUT /<event_id>/update/` - Update timeline event
- `DELETE /<event_id>/delete/` - Delete timeline event
- `PATCH /<event_id>/complete/` - Mark event as complete

### Pricing (`/api/pricing/`)
- `GET /plans/` - Get pricing plans
- `GET /plans/<plan_id>/` - Get pricing plan details

#### Subscriptions
- `GET /subscription/` - Get user subscription
- `POST /subscription/create/` - Create subscription
- `PUT /subscription/update/` - Update subscription
- `POST /subscription/cancel/` - Cancel subscription

#### Payments
- `GET /payments/` - Get payment history

#### Discount Codes
- `POST /discount/validate/` - Validate discount code
- `GET /discount/usage/` - Get discount usage history

#### User Plan Info
- `GET /user/plan-info/` - Get user plan information

## Data Models

### Move
```json
{
  "id": "uuid",
  "move_date": "2024-01-15",
  "current_location": "123 Current St, Sydney NSW 2000",
  "destination_location": "456 New St, Melbourne VIC 3000",
  "from_property_type": "apartment",
  "to_property_type": "house",
  "current_property_url": "https://domain.com.au/property",
  "new_property_url": "https://realestate.com.au/property",
  "discount_type": "first_home_buyer",
  "discount_percentage": 15.00,
  "status": "planning",
  "progress": 25,
  "created_at": "2024-01-01T10:00:00Z"
}
```

### Inventory Box
```json
{
  "id": "uuid",
  "type": "medium",
  "label": "Kitchen Box 1",
  "contents": "Dishes, utensils, small appliances",
  "weight": "15kg",
  "fragile": true,
  "packed": false,
  "qr_code": "base64_encoded_qr_data",
  "room_name": "Kitchen",
  "created_at": "2024-01-01T10:00:00Z"
}
```

### Task
```json
{
  "id": "uuid",
  "title": "Council Kerbside Booking",
  "description": "Book council kerbside collection",
  "category": "council",
  "location": "current",
  "priority": "medium",
  "completed": false,
  "due_date": "2024-01-10T09:00:00Z",
  "assigned_to_name": "John Doe",
  "is_external": true,
  "external_url": "https://council.nsw.gov.au/kerbside",
  "subtasks": ["Sort items", "Book online"],
  "time_spent": 3600,
  "created_at": "2024-01-01T10:00:00Z"
}
```

### Service
```json
{
  "id": "uuid",
  "name": "Professional Moving Service",
  "description": "Full-service residential moving",
  "category": "movers",
  "price_from": 150.00,
  "price_unit": "hour",
  "features": ["Insured", "Licensed", "Same-day service"],
  "provider": {
    "id": "uuid",
    "name": "Sydney Movers Pro",
    "rating": 4.8,
    "review_count": 127,
    "verification_status": "verified"
  }
}
```

### Service Booking
```json
{
  "id": "uuid",
  "service": {
    "name": "Professional Moving Service",
    "category": "movers"
  },
  "provider": {
    "name": "Sydney Movers Pro",
    "rating": 4.8
  },
  "preferred_date": "2024-01-15",
  "preferred_time": "morning",
  "status": "pending",
  "quoted_price": 800.00,
  "notes": "3 bedroom apartment, 2nd floor",
  "created_at": "2024-01-01T10:00:00Z"
}
```

### Pricing Plan
```json
{
  "id": "uuid",
  "name": "Plan +",
  "plan_type": "plus",
  "description": "Enhanced features for a smoother moving experience",
  "price_monthly": 49.00,
  "price_yearly": 490.00,
  "calculated_price_monthly": 58.80,
  "calculated_price_yearly": 588.00,
  "features": [
    "Everything in Free",
    "Advanced inventory with QR codes",
    "Task management with timers",
    "Service provider marketplace",
    "Priority support",
    "1-2 date changes allowed"
  ],
  "date_changes_allowed": 2,
  "is_popular": true
}
```

## Error Responses
All error responses follow this format:
```json
{
  "success": false,
  "message": "Error description",
  "errors": {
    "field_name": ["Error message"]
  },
  "status_code": 400
}
```

## Success Responses
All success responses follow this format:
```json
{
  "success": true,
  "message": "Success description",
  "data": { ... },
  "status_code": 200
}
```

## Pagination
Paginated endpoints support these query parameters:
- `page` - Page number (starts from 1)
- `page_size` - Items per page (default: 20, max: 100)

Paginated response format:
```json
{
  "success": true,
  "message": "Data retrieved successfully",
  "data": {
    "count": 150,
    "next": "http://api.example.com/endpoint/?page=3",
    "previous": "http://api.example.com/endpoint/?page=1",
    "results": [ ... ]
  }
}
```

## Filtering and Search
Many endpoints support filtering:
- `search` - Text search across relevant fields
- `status` - Filter by status
- `category` - Filter by category
- `location` - Filter by location
- `completed` - Filter by completion status (true/false)

Example:
```
GET /api/tasks/?move_id=123&category=utilities&completed=false&search=electricity
```

## File Uploads
File upload endpoints accept multipart/form-data:
- Maximum file size: 10MB
- Supported formats: PNG, JPG, JPEG, PDF
- Files are stored securely and accessible via URLs

## Rate Limiting
API endpoints are rate limited:
- Authenticated users: 1000 requests per hour
- Anonymous users: 100 requests per hour

## WebSocket Support
Real-time updates are available via WebSocket connections:
- Task updates
- Move progress updates
- Service booking status changes
- Collaborator notifications

## Development Notes
- All UUIDs are version 4
- Timestamps are in ISO 8601 format (UTC)
- Currency amounts are in AUD
- Phone numbers follow Australian format
- Addresses support Australian postal codes
- QR codes contain base64-encoded JSON data

## Testing
Use the provided test endpoints:
- `GET /health/` - Health check
- `POST /api/auth/test-token/` - Test JWT token validity

## Support
For API support, contact: api-support@removealist.com.au

