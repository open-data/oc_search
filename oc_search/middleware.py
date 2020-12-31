from django.conf import settings
from django.http import HttpResponse

class CanadaBilingualMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.
        self.path_toggle = settings.SEARCH_LANG_USE_PATH
        self.EN_HOST = ''
        self.FR_HOST = ''
        if not self.path_toggle:
            self.EN_HOST = settings.SEARCH_EN_HOSTNAME
            self.FR_HOST = settings.SEARCH_FR_HOSTNAME

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        if self.path_toggle:
            subpaths = request.path.split('/')
            if 'fr' in subpaths:
                request.LANGUAGE_CODE = 'fr'
            else:
                request.LANGUAGE_CODE = 'en'
        else:
            if request.get_host() == self.FR_HOST:
                request.LANGUAGE_CODE = 'fr'
            else:
                request.LANGUAGE_CODE = 'en'
        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response