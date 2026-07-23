from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class PayloadTooLargeError(Exception):
    """Internal exception raised when streaming request body exceeds max_bytes."""

    pass


class BodySizeLimitMiddleware:
    """Pure ASGI middleware enforcing a maximum payload size limit on incoming requests."""

    def __init__(self, app: ASGIApp, max_bytes: int = 1048576):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 1. Quick check using Content-Length header if available
        headers = dict(scope.get("headers", []))
        content_length_bytes = headers.get(b"content-length")
        if content_length_bytes:
            try:
                length = int(content_length_bytes.decode("latin-1"))
                if length > self.max_bytes:
                    response = JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"Payload too large. Maximum permitted request size is {self.max_bytes} bytes."
                        },
                    )
                    await response(scope, receive, send)
                    return
            except (ValueError, UnicodeDecodeError):
                pass

        # 2. For state-changing methods with body content, check actual stream size
        method = scope.get("method", "GET").upper()
        if method not in ("POST", "PUT", "PATCH"):
            await self.app(scope, receive, send)
            return

        received_bytes = 0
        response_started = False

        async def custom_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        async def custom_receive() -> Message:
            nonlocal received_bytes
            message = await receive()
            if message.get("type") == "http.request":
                body = message.get("body", b"")
                received_bytes += len(body)
                if received_bytes > self.max_bytes:
                    raise PayloadTooLargeError()
            return message

        try:
            await self.app(scope, custom_receive, custom_send)
        except PayloadTooLargeError:
            if not response_started:
                response = JSONResponse(
                    status_code=413,
                    content={
                        "detail": f"Payload too large. Maximum permitted request size is {self.max_bytes} bytes."
                    },
                )
                await response(scope, receive, send)
            else:
                raise
