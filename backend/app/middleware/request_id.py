import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware generating and attaching a correlation request ID to every HTTP request/response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Respect existing X-Request-ID header if supplied by edge proxy/gateway, else generate UUID4
        incoming_id = request.headers.get("x-request-id")
        if incoming_id and incoming_id.strip():
            request_id = incoming_id.strip()
        else:
            request_id = f"req_{uuid.uuid4().hex[:12]}"

        # Expose request ID on request state for downstream handlers and exception formatters
        request.state.request_id = request_id

        response = await call_next(request)

        # Attach X-Request-ID to outgoing response headers
        response.headers["X-Request-ID"] = request_id
        return response
