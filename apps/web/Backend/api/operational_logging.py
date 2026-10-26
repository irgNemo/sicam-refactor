"""Logs complement LifecycleEvent; they never store bodies, reasons or credentials."""
import json
import logging
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.http import JsonResponse
from django.utils.cache import patch_vary_headers
from .access import profile_for

logger = logging.getLogger('sicam.operations')


class SafeJSONFormatter(logging.Formatter):
    def format(self, record):
        # Ignore getMessage(), args, exc_info, request and arbitrary extras by design.
        data = {'timestamp': self.formatTime(record), 'level': record.levelname}
        for field in ('event', 'user_id', 'institution_id', 'route', 'status', 'resource_type', 'resource_id'):
            value = getattr(record, field, None)
            if isinstance(value, (str, int)) or value is None:
                data[field] = value
        return json.dumps(data, ensure_ascii=True)


class OperationalLogMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        match = getattr(request, 'resolver_match', None)
        route = str(match.route) if match else 'unresolved'
        if settings.DJANGO_ENV == 'production' and response.status_code >= 500 and request.path.startswith('/api/'):
            # Existing service errors may contain upstream URLs or exception details.
            response = JsonResponse({'error': 'No se pudo completar la operación.', 'code': 'SERVICE_UNAVAILABLE' if response.status_code in (502, 503, 504) else 'INTERNAL_ERROR'}, status=response.status_code)
        if route.startswith(('api/admin-audit/', 'api/auth/', 'api/users/', 'api/institutions/')):
            response['Cache-Control'] = 'private, no-store'
            patch_vary_headers(response, ['Cookie'])
        if response.status_code >= 400 or '/auth/' in '/'+route or '/lifecycle/' in '/'+route:
            user = getattr(request, 'user', None)
            profile = profile_for(user)
            kwargs = match.kwargs if match else {}
            from .services.lifecycle import RESOURCE_MODELS
            logger.log(logging.ERROR if response.status_code >= 500 else logging.WARNING if response.status_code >= 400 else logging.INFO,
                       'request_outcome', extra={'event': 'request_outcome',
                       'user_id': user.pk if user and user.is_authenticated else None,
                       'institution_id': profile.institution_id if profile else None,
                       'route': route, 'status': response.status_code,
                       'resource_type': kwargs.get('resource') if kwargs.get('resource') in RESOURCE_MODELS else None,
                       'resource_id': kwargs.get('pk') if str(kwargs.get('pk', '')).isdigit() else None})
        return response
