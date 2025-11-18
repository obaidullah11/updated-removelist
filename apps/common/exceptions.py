"""
Custom exception handlers for consistent API responses.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from django.core.exceptions import PermissionDenied, ValidationError
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns consistent API responses.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        custom_response_data = {
            'success': False,
            'message': get_error_message(exc, response),
            'data': None,
            'errors': response.data if isinstance(response.data, dict) else {'detail': response.data},
            'status': response.status_code
        }
        
        # Log the error
        logger.error(f"API Error: {exc} - Status: {response.status_code}")
        
        response.data = custom_response_data
    else:
        # Handle Django exceptions that aren't handled by DRF
        if isinstance(exc, Http404):
            custom_response_data = {
                'success': False,
                'message': 'Resource not found',
                'data': None,
                'errors': {'detail': ['Resource not found']},
                'status': 404
            }
            response = Response(custom_response_data, status=status.HTTP_404_NOT_FOUND)
        elif isinstance(exc, PermissionDenied):
            custom_response_data = {
                'success': False,
                'message': 'Permission denied',
                'data': None,
                'errors': {'detail': ['You do not have permission to perform this action']},
                'status': 403
            }
            response = Response(custom_response_data, status=status.HTTP_403_FORBIDDEN)
        elif isinstance(exc, ValidationError):
            custom_response_data = {
                'success': False,
                'message': 'Validation failed',
                'data': None,
                'errors': exc.message_dict if hasattr(exc, 'message_dict') else {'detail': [str(exc)]},
                'status': 400
            }
            response = Response(custom_response_data, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Log unexpected errors
            logger.error(f"Unexpected error: {exc}", exc_info=True)
            custom_response_data = {
                'success': False,
                'message': 'Internal server error',
                'data': None,
                'errors': {'detail': ['An unexpected error occurred']},
                'status': 500
            }
            response = Response(custom_response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return response


def get_error_message(exc, response):
    """
    Get a user-friendly error message based on the exception and response.
    """
    status_code = response.status_code
    
    if status_code == 400:
        return 'Validation failed'
    elif status_code == 401:
        return 'Authentication required'
    elif status_code == 403:
        return 'Permission denied'
    elif status_code == 404:
        return 'Resource not found'
    elif status_code == 429:
        return 'Too many requests'
    elif status_code >= 500:
        return 'Internal server error'
    else:
        return 'An error occurred'
