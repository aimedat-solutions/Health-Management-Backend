import threading
from django.utils.deprecation import MiddlewareMixin

_user = threading.local()

class AuditMiddleware(MiddlewareMixin):
    def process_request(self, request):
        _user.value = request.user if request.user.is_authenticated else None

    def process_response(self, request, response):
        _user.value = None
        return response

def get_current_user():
    return getattr(_user, "value", None)
