import datetime
import http
import logging
from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def create_error_response(
    status_code: int,
    code: str,
    message: str,
    request: Optional[Request] = None,
    headers: Optional[Dict[str, str]] = None,
) -> JSONResponse:
    """Construct a standardized JSON error response."""
    request_id = getattr(request.state, "request_id", "N/A") if request else "N/A"
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    payload = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "timestamp": now_utc,
        },
        "detail": message,
    }

    resp_headers = headers.copy() if headers else {}
    if request_id != "N/A":
        resp_headers["X-Request-ID"] = request_id

    return JSONResponse(status_code=status_code, content=payload, headers=resp_headers)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Centralized handler for HTTPExceptions."""
    status_code = exc.status_code
    try:
        status_name = http.HTTPStatus(status_code).name.upper()
        code = f"HTTP_{status_code}_{status_name}"
    except ValueError:
        code = f"HTTP_{status_code}"

    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    headers = getattr(exc, "headers", None)

    logger.warning(
        "[HTTP_EXCEPTION] RequestID: %s | Status: %d | Code: %s | Message: %s",
        getattr(request.state, "request_id", "N/A"),
        status_code,
        code,
        message,
    )
    return create_error_response(status_code, code, message, request, headers)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Centralized handler for Pydantic RequestValidationErrors."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "VALIDATION_ERROR"
    errors = exc.errors()
    if errors:
        first_err = errors[0]
        loc = " -> ".join(str(item) for item in first_err.get("loc", []))
        msg = first_err.get("msg", "Validation error")
        message = f"Validation failed at '{loc}': {msg}" if loc else msg
    else:
        message = "Invalid request payload or parameters."

    logger.warning(
        "[VALIDATION_ERROR] RequestID: %s | Message: %s",
        getattr(request.state, "request_id", "N/A"),
        message,
    )
    return create_error_response(status_code, code, message, request)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Centralized catch-all handler for unhandled exceptions."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "INTERNAL_SERVER_ERROR"
    message = "An internal server error occurred. Please try again later."

    logger.error(
        "[UNHANDLED_EXCEPTION] RequestID: %s | Path: %s | Error: %s",
        getattr(request.state, "request_id", "N/A"),
        request.url.path,
        exc,
        exc_info=True,
    )
    return create_error_response(status_code, code, message, request)
