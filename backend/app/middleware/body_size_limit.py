from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing a maximum payload size limit on incoming requests."""

    def __init__(self, app, max_bytes: int = 1048576):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        # 1. Quick check using Content-Length header if available
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": f"Payload too large. Maximum permitted request size is {self.max_bytes} bytes."},
                    )
            except ValueError:
                pass

        # 2. For state-changing methods with body content, check actual stream size if Content-Length was missing/invalid
        if request.method in ("POST", "PUT", "PATCH"):
            body_bytes = bytearray()
            async for chunk in request.stream():
                body_bytes.extend(chunk)
                if len(body_bytes) > self.max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": f"Payload too large. Maximum permitted request size is {self.max_bytes} bytes."},
                    )

            # Re-inject the consumed stream so downstream endpoint handlers can parse the body
            async def receive():
                return {"type": "http.request", "body": bytes(body_bytes)}

            request._receive = receive

        return await call_next(request)
