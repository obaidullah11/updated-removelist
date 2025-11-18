# RemoveList Backend API

A comprehensive Django REST API for the RemoveList moving platform, providing authentication, move management, booking, inventory tracking, timeline management, and file storage capabilities.

## 🚀 Features

- **User Authentication & Management**
  - JWT-based authentication with refresh tokens
  - Email verification and password reset
  - User profiles with avatar upload
  
- **Move Management**
  - Create and manage moving projects
  - Track move progress and status
  - Property type and size categorization
  
- **Booking & Scheduling**
  - Time slot availability checking
  - Move booking with confirmation
  - Email notifications for bookings
  
- **Inventory Management**
  - Room-based inventory organization
  - Item tracking and box counting
  - Room image uploads
  
- **Timeline & Task Management**
  - Moving timeline with events
  - Week-based checklist system
  - Custom task creation
  - Progress tracking
  
- **File Management**
  - Floor plan uploads
  - Document storage
  - Secure file access control
  
- **Email System**
  - HTML email templates
  - Automated notifications
  - Celery-based async email sending

## 📋 Requirements

- Python 3.8+
- PostgreSQL 12+
- Redis 6+
- Django 4.2+

## 🛠️ Installation & Setup

### 1. Clone and Setup Environment

```bash
# Navigate to the backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup

```bash
# Install PostgreSQL and create database
createdb removealist_db

# Or using PostgreSQL command line:
psql -U postgres
CREATE DATABASE removealist_db;
\q
```

### 3. Environment Configuration

```bash
# Copy environment template
cp env.example .env

# Edit .env file with your configuration
# Update database credentials, email settings, etc.
```

### 4. Django Setup

```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Create default data
python manage.py create_checklist_templates
python manage.py create_time_slots

# Collect static files (for production)
python manage.py collectstatic
```

### 5. Redis Setup

```bash
# Install and start Redis
# On Ubuntu/Debian:
sudo apt-get install redis-server
sudo systemctl start redis-server

# On macOS with Homebrew:
brew install redis
brew services start redis

# On Windows: Download from https://redis.io/download
```

### 6. Start Development Server

```bash
# Start Django development server
python manage.py runserver

# In another terminal, start Celery worker (for emails)
celery -A removealist_backend worker --loglevel=info

# In another terminal, start Celery beat (for scheduled tasks)
celery -A removealist_backend beat --loglevel=info
```

## 📚 API Documentation

### Base URL
```
http://localhost:8000/api/
```

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register/email/` | Register new user |
| POST | `/auth/login/` | User login |
| POST | `/auth/logout/` | User logout |
| POST | `/auth/refresh/` | Refresh JWT token |
| POST | `/auth/verify-email/` | Verify email address |
| POST | `/auth/resend-email/` | Resend verification email |
| POST | `/auth/forgot-password/` | Request password reset |
| POST | `/auth/reset-password/` | Reset password with token |
| POST | `/auth/change-password/` | Change password (authenticated) |
| GET | `/auth/profile/` | Get user profile |
| PUT | `/auth/profile/` | Update user profile |
| POST | `/auth/profile/avatar/` | Upload avatar |

### Move Management Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/move/create/` | Create new move |
| GET | `/move/get/{move_id}/` | Get move details |
| GET | `/move/user-moves/` | Get user's moves |
| PUT | `/move/update/{move_id}/` | Update move |
| DELETE | `/move/delete/{move_id}/` | Delete move |

### Booking Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/booking/slots/?date=YYYY-MM-DD` | Get available time slots |
| POST | `/booking/book/` | Book time slot |
| GET | `/booking/user-bookings/` | Get user bookings |
| GET | `/booking/{booking_id}/` | Get booking details |
| PATCH | `/booking/{booking_id}/cancel/` | Cancel booking |

### Inventory Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/inventory/rooms/?move_id={id}` | Get rooms for move |
| POST | `/inventory/rooms/` | Create room |
| GET | `/inventory/rooms/{room_id}/` | Get room details |
| PUT | `/inventory/rooms/{room_id}/` | Update room |
| PATCH | `/inventory/rooms/{room_id}/packed/` | Mark room as packed |
| DELETE | `/inventory/rooms/{room_id}/` | Delete room |
| POST | `/inventory/rooms/{room_id}/image/` | Upload room image |

### Timeline & Checklist Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/timeline/events/?move_id={id}` | Get timeline events |
| PATCH | `/timeline/events/{event_id}/` | Update timeline event |
| GET | `/checklist/items/?move_id={id}` | Get checklist items |
| PATCH | `/checklist/items/{item_id}/` | Update checklist item |
| POST | `/checklist/items/` | Add custom task |
| DELETE | `/checklist/items/{item_id}/` | Delete custom task |

### File Management Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/files/floor-plans/` | Upload floor plan |
| POST | `/files/documents/` | Upload document |
| GET | `/files/user-files/?move_id={id}` | Get user files |
| DELETE | `/files/{file_id}/` | Delete file |

## 🔧 API Response Format

All API responses follow this consistent format:

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

## 🔐 Authentication

The API uses JWT (JSON Web Tokens) for authentication:

1. **Login** to get access and refresh tokens
2. **Include** access token in Authorization header: `Bearer {access_token}`
3. **Refresh** tokens when they expire using the refresh endpoint
4. **Logout** to blacklist refresh tokens

## 📧 Email Configuration

### Gmail Setup (Development)

1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password: Google Account → Security → App passwords
3. Use your Gmail address and app password in `.env`:

```env
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-16-character-app-password
```

### Production Email Setup

For production, consider using:
- **SendGrid**: Professional email service
- **Amazon SES**: AWS Simple Email Service
- **Mailgun**: Developer-friendly email API

## 🚀 Production Deployment

### Environment Variables

Set these environment variables in production:

```env
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DB_HOST=your-production-db-host
DB_PASSWORD=your-production-db-password
USE_S3=True
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
```

### Database Migration

```bash
# Run migrations in production
python manage.py migrate

# Create default data
python manage.py create_checklist_templates
python manage.py create_time_slots
```

### Static Files & Media

For production, configure AWS S3 or similar cloud storage:

```env
USE_S3=True
AWS_STORAGE_BUCKET_NAME=your-bucket-name
```

### Process Management

Use a process manager like Supervisor or systemd to manage:
- Django application (Gunicorn)
- Celery worker
- Celery beat scheduler

Example Gunicorn command:
```bash
gunicorn removealist_backend.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

## 🧪 Testing

```bash
# Run all tests
python manage.py test

# Run tests for specific app
python manage.py test apps.authentication

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

## 📊 Monitoring & Logging

### Health Check

The API includes a health check endpoint:
```
GET /health/
```

### Logging

Logs are written to:
- Console (development)
- `logs/django.log` (file logging)

Configure log levels in `settings.py` for different environments.

### Performance Monitoring

Consider integrating:
- **Sentry** for error tracking
- **New Relic** or **DataDog** for performance monitoring
- **Django Debug Toolbar** for development debugging

## 🔒 Security Considerations

### Production Security Checklist

- [ ] Set `DEBUG=False`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Enable HTTPS (`SECURE_SSL_REDIRECT=True`)
- [ ] Set secure cookie flags
- [ ] Configure CORS properly
- [ ] Use environment variables for secrets
- [ ] Regular security updates
- [ ] Database connection encryption
- [ ] File upload validation
- [ ] Rate limiting implementation

### Rate Limiting

The API includes basic rate limiting:
- Auth endpoints: 5 requests/minute per IP
- General endpoints: 100 requests/minute per user

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Email: support@removealist.com
- Documentation: [API Docs](http://localhost:8000/admin/doc/)
- Issues: GitHub Issues

## 🔄 Version History

### v1.0.0 (Current)
- Initial release
- Complete authentication system
- Move management
- Booking system
- Inventory tracking
- Timeline management
- File uploads
- Email notifications
