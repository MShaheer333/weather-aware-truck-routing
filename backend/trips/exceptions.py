"""Domain errors and the DRF exception handler that turns them into clean JSON responses."""
from rest_framework.response import Response
from rest_framework.views import exception_handler


class ServiceError(Exception):
    """Base class for expected, user-presentable failures."""

    status_code = 400
    code = "bad_request"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class UpstreamError(ServiceError):
    """A third-party API (routing / geocoding / weather) failed or returned nothing usable."""

    status_code = 502
    code = "upstream_error"


class NoRouteFound(ServiceError):
    status_code = 422
    code = "no_route"


class InvalidRequest(ServiceError):
    status_code = 400
    code = "invalid_request"


def api_exception_handler(exc, context):
    if isinstance(exc, ServiceError):
        return Response({"error": {"code": exc.code, "message": exc.message}}, status=exc.status_code)
    response = exception_handler(exc, context)
    if response is not None and isinstance(response.data, dict) and "detail" in response.data:
        response.data = {"error": {"code": "error", "message": str(response.data["detail"])}}
    return response
