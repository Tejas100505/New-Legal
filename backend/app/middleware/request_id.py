"""
Request-ID middleware.

Assigns a unique UUID to every incoming request for traceability across
logs, error responses, and downstream service calls. The ID is propagated
via the `X-Request-ID` response header and available in loguru context.
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from loguru import logger


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Adds a unique request ID to every request/response cycle."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Use client-provided ID if present, otherwise generate one
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Store on request state for access in route handlers
        request.state.request_id = request_id

        # Bind to loguru context for correlated log entries
        with logger.contextualize(request_id=request_id):
            logger.info(
                "{method} {path}",
                method=request.method,
                path=request.url.path,
            )
            response = await call_next(request)

        response.headers["X-Request-ID"] = request_id
        return response
