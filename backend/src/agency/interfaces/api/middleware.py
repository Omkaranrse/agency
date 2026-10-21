"""FastAPI middleware for request correlation and payload size enforcement."""

import json
import re
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_REGEX = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Correlation middleware generating or validating incoming X-Request-ID headers."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        header_val = request.headers.get("X-Request-ID")
        if header_val and REQUEST_ID_REGEX.match(header_val):
            req_id = header_val
        else:
            req_id = uuid.uuid4().hex

        request.state.request_id = req_id

        from agency.infrastructure.observability.logging import bind_context

        with bind_context(request_id=req_id):
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforces upper bounds on incoming request body size."""

    def __init__(self, app: Any, max_size_bytes: int = 1_048_576) -> None:
        super().__init__(app)
        self.max_size_bytes = max_size_bytes

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        content_length = request.headers.get("content-length")
        req_id = getattr(request.state, "request_id", "unknown")

        if content_length:
            try:
                length = int(content_length)
                if length > self.max_size_bytes:
                    payload = {
                        "error": {
                            "code": "REQUEST_TOO_LARGE",
                            "message": (
                                f"Request body exceeds maximum limit of "
                                f"{self.max_size_bytes} bytes."
                            ),
                            "request_id": req_id,
                            "details": {
                                "max_bytes": self.max_size_bytes,
                                "received_bytes": length,
                            },
                        }
                    }
                    return Response(
                        content=json.dumps(payload),
                        status_code=413,
                        media_type="application/json",
                        headers={"X-Request-ID": req_id},
                    )
            except ValueError:
                pass

        return await call_next(request)
