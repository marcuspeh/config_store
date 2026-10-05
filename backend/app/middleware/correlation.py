"""FastAPI middleware that binds the logging SDK's correlation id per request.

Every request gets a unique id (``X-Request-ID`` header if the caller
provided one, otherwise a fresh UUID4). The id is bound to the SDK's
``log_id_var`` contextvar for the lifetime of the request so any
``logging.info(...)`` call — including those routed through the SDK — ends
up correlated in the logging collector.

The id is echoed back on the response so clients can correlate their
own logs with ours.
"""

from __future__ import annotations

import uuid
from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

try:
    import loggingsdk
    from loggingsdk import log_id_var
except Exception:  # pragma: no cover - SDK unavailable
    loggingsdk = None  # type: ignore[assignment]
    log_id_var = None  # type: ignore[assignment]

REQUEST_ID_HEADER = "X-Request-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex

        if log_id_var is None:
            # SDK unavailable, skip the binding — every event gets
            # "unknown" as the correlation id.
            return await call_next(request)

        token = log_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            log_id_var.reset(token)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response