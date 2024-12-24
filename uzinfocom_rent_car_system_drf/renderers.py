from http import HTTPStatus
from rest_framework.renderers import JSONRenderer
from datetime import datetime

class ApiRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        status_code = renderer_context['response'].status_code

        # Handle error responses
        if not str(status_code).startswith('2'):
            return super(ApiRenderer, self).render({
                "status": HTTPStatus(status_code).phrase,
                "code": status_code,
                "errors": data
            }, accepted_media_type, renderer_context)

        # Handle success responses
        response = {
            "status": HTTPStatus(status_code).phrase,
            "code": status_code,
            "data": data,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "version": "1.0"
            }
        }
        return super(ApiRenderer, self).render(response, accepted_media_type, renderer_context)