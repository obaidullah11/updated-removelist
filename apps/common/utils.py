"""
Common utility functions for the RemoveList application.
"""
import uuid
import re
from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email
from rest_framework.response import Response
from rest_framework import status


def generate_uuid():
    """Generate a UUID string."""
    return str(uuid.uuid4())


def validate_email(email):
    """
    Validate email format.
    """
    try:
        django_validate_email(email)
        return True
    except ValidationError:
        return False


def validate_phone_number(phone_number):
    """
    Validate phone number format.
    Must start with + followed by country code and 10-15 digits.
    """
    pattern = r'^\+\d{10,15}$'
    return bool(re.match(pattern, phone_number))


def sanitize_filename(filename):
    """
    Sanitize filename for safe storage.
    """
    # Remove any path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Remove or replace dangerous characters
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    
    # Limit length
    if len(filename) > 100:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:95] + ('.' + ext if ext else '')
    
    return filename


def success_response(message, data=None, status_code=status.HTTP_200_OK):
    """
    Create a standardized success response.
    """
    response_data = {
        'success': True,
        'message': message,
        'data': data,
        'status': status_code
    }
    return Response(response_data, status=status_code)


def error_response(message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Create a standardized error response.
    """
    response_data = {
        'success': False,
        'message': message,
        'data': None,
        'errors': errors or {},
        'status': status_code
    }
    return Response(response_data, status=status_code)


def paginated_response(queryset, serializer_class, request, message="Data retrieved successfully"):
    """
    Create a paginated response with consistent format.
    """
    from django.core.paginator import Paginator
    from django.conf import settings
    
    page_size = request.GET.get('page_size', settings.REST_FRAMEWORK['PAGE_SIZE'])
    page_number = request.GET.get('page', 1)
    
    try:
        page_size = int(page_size)
        page_number = int(page_number)
    except (ValueError, TypeError):
        page_size = settings.REST_FRAMEWORK['PAGE_SIZE']
        page_number = 1
    
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page_number)
    
    serializer = serializer_class(page_obj.object_list, many=True, context={'request': request})
    
    data = {
        'results': serializer.data,
        'count': paginator.count,
        'page': page_number,
        'total_pages': paginator.num_pages,
        'next': page_obj.next_page_number() if page_obj.has_next() else None,
        'previous': page_obj.previous_page_number() if page_obj.has_previous() else None,
    }
    
    return success_response(message, data)


class ChoicesMixin:
    """
    Mixin to provide choices as a class method.
    """
    
    @classmethod
    def get_choices_dict(cls):
        """Return choices as a dictionary."""
        if hasattr(cls, 'CHOICES'):
            return dict(cls.CHOICES)
        return {}
    
    @classmethod
    def get_choices_list(cls):
        """Return choices as a list of values."""
        if hasattr(cls, 'CHOICES'):
            return [choice[0] for choice in cls.CHOICES]
        return []
