"""
Custom middleware for the RemoveList application.
"""
import logging
import time
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(MiddlewareMixin):
    """
    Middleware to handle unhandled exceptions and return consistent JSON responses.
    """
    
    def process_exception(self, request, exception):
        """
        Handle unhandled exceptions.
        """
        logger.error(f"Unhandled exception: {exception}", exc_info=True)
        
        # Only handle API requests (those starting with /api/)
        if request.path.startswith('/api/'):
            return JsonResponse({
                'success': False,
                'message': 'Internal server error',
                'data': None,
                'errors': {'detail': ['An unexpected error occurred']},
                'status': 500
            }, status=500)
        
        # Let Django handle non-API requests normally
        return None


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log API requests and responses.
    """
    
    def process_request(self, request):
        """
        Log incoming requests.
        """
        if request.path.startswith('/api/'):
            request.start_time = time.time()
            logger.info(f"API Request: {request.method} {request.path} from {request.META.get('REMOTE_ADDR')}")
    
    def process_response(self, request, response):
        """
        Log response information.
        """
        if hasattr(request, 'start_time') and request.path.startswith('/api/'):
            duration = time.time() - request.start_time
            logger.info(f"API Response: {request.method} {request.path} - {response.status_code} ({duration:.3f}s)")
        
        return response
