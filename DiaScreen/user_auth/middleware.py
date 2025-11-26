"""
Security middleware for rate limiting and logging
"""
import time
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger('django.security')


class RateLimitMiddleware(MiddlewareMixin):
    """
    Rate limiting middleware to prevent brute force attacks
    """
    def process_request(self, request):
        if request.path in ['/login/', '/register/']:
            ip_address = self.get_client_ip(request)
            cache_key = f'rate_limit_{ip_address}_{request.path}'
            
            attempts = cache.get(cache_key, 0)
            
            max_attempts = 5
            timeout = 900
            
            if attempts >= max_attempts:
                logger.warning(
                    f'Rate limit exceeded for IP {ip_address} on {request.path}'
                )
                return JsonResponse({
                    'error': 'Занадто багато спроб. Спробуйте через 15 хвилин.'
                }, status=429)
            
            cache.set(cache_key, attempts + 1, timeout)
        
        return None
    
    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityLoggingMiddleware(MiddlewareMixin):
    """
    Log security-related events
    """
    def process_response(self, request, response):
        if request.path == '/login/' and request.method == 'POST':
            if response.status_code == 200:
                username = request.POST.get('username', 'unknown')
                ip_address = self.get_client_ip(request)
                logger.warning(
                    f'Failed login attempt: username={username}, IP={ip_address}'
                )
        
        sensitive_paths = ['/admin/', '/api/notifications/', '/card/', '/analytics/']
        if any(request.path.startswith(path) for path in sensitive_paths):
            if request.user.is_authenticated:
                logger.info(
                    f'Access to sensitive endpoint: {request.path} by user {request.user.username}'
                )
            else:
                logger.warning(
                    f'Unauthorized access attempt to {request.path} from IP {self.get_client_ip(request)}'
                )
        
        return response
    
    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

