"""Binds the logging SDK's correlation id for the lifetime of a request.

Uses the inbound ``X-Request-ID`` when present, otherwise a generated id.
The id is echoed on the response so clients can correlate their logs.
"""

from __future__ import annotations

from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.logging_setup import log_id_scope

REQUEST_ID_HEADER = "X-Request-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        with log_id_scope(request.headers.get(REQUEST_ID_HEADER)) as request_id:
            response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
