"""Binds the logging SDK's correlation id for the lifetime of a request.

Uses the inbound ``X-Request-ID`` when present, otherwise an id from the
SDK's ``new_log_id()``. The id is bound to ``log_id_var`` and echoed on the
response so clients can correlate their logs with ours.
"""

from __future__ import annotations

from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

try:
    from loggingsdk import log_id_var, new_log_id
except Exception:  # pragma: no cover - SDK unavailable
    log_id_var = None  # type: ignore[assignment]
    new_log_id = None  # type: ignore[assignment]

REQUEST_ID_HEADER = "X-Request-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        inbound = request.headers.get(REQUEST_ID_HEADER)
        if inbound:
            request_id = inbound
        elif new_log_id is not None:
            request_id = new_log_id()
        else:
            request_id = "unknown"

        if log_id_var is None:
            return await call_next(request)

        token = log_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            log_id_var.reset(token)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
