"""
Custom validators for the RemoveList application.
"""
import re
from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email
from django.utils.translation import gettext_lazy as _


def validate_phone_number(value):
    """
    Validate phone number format.
    Must start with + followed by country code and 10-15 digits.
    """
    pattern = r'^\+\d{10,15}$'
    if not re.match(pattern, value):
        raise ValidationError(
            _('Phone number must start with country code (+) followed by 10-15 digits.'),
            code='invalid_phone'
        )


def validate_password_strength(value):
    """
    Validate password strength.
    Minimum 6 characters as per requirements.
    """
    if len(value) < 6:
        raise ValidationError(
            _('Password must be at least 6 characters long.'),
            code='password_too_short'
        )


def validate_name(value):
    """
    Validate name fields (first_name, last_name).
    Minimum 3 characters as per requirements.
    """
    if len(value.strip()) < 3:
        raise ValidationError(
            _('Name must be at least 3 characters long.'),
            code='name_too_short'
        )


def validate_file_size(value):
    """
    Validate file size (max 10MB).
    """
    max_size = 10 * 1024 * 1024  # 10MB
    if value.size > max_size:
        raise ValidationError(
            _('File size exceeds 10MB limit.'),
            code='file_too_large'
        )


def validate_image_file(value):
    """
    Validate image file format.
    """
    allowed_extensions = ['.jpg', '.jpeg', '.png']
    file_extension = value.name.lower().split('.')[-1]
    
    if f'.{file_extension}' not in allowed_extensions:
        raise ValidationError(
            _('Unsupported file format. Please use PNG, JPG, or JPEG.'),
            code='invalid_image_format'
        )


def validate_document_file(value):
    """
    Validate document file format.
    """
    allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
    file_extension = value.name.lower().split('.')[-1]
    
    if f'.{file_extension}' not in allowed_extensions:
        raise ValidationError(
            _('Unsupported file format. Please use PDF, PNG, JPG, or JPEG.'),
            code='invalid_document_format'
        )


def validate_future_date(value):
    """
    Validate that a date is in the future.
    """
    from django.utils import timezone
    
    if value <= timezone.now().date():
        raise ValidationError(
            _('Date must be in the future.'),
            code='date_not_future'
        )
