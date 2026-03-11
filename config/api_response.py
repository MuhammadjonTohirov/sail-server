"""
Standardized API response wrapper.

All API responses follow this format:
{
    "success": true/false,
    "data": <payload or null>,
    "error": <string or null>,
    "code": <http status code>
}
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


# ---------------------------------------------------------------------------
# Helper to build consistent response dicts
# ---------------------------------------------------------------------------

def api_envelope(*, data=None, error: str | None = None, code: int = 200) -> dict:
    """Build the standard envelope dict."""
    return {
        "success": 200 <= code < 300,
        "data": data,
        "error": error,
        "code": code,
    }


# ---------------------------------------------------------------------------
# Custom renderer – wraps every DRF Response automatically
# ---------------------------------------------------------------------------

class ApiRenderer(JSONRenderer):
    """
    Wraps all JSON responses in the standard envelope.

    Skips wrapping if the response already contains the envelope keys
    (to avoid double-wrapping).
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response") if renderer_context else None
        status_code = response.status_code if response else 200

        # Already wrapped (e.g. by custom exception handler)?
        if isinstance(data, dict) and "success" in data and "code" in data:
            return super().render(data, accepted_media_type, renderer_context)

        is_success = 200 <= status_code < 300

        if is_success:
            envelope = api_envelope(data=data, code=status_code)
        else:
            # For error responses, extract a human-readable message
            error_msg = _extract_error_message(data)
            envelope = api_envelope(data=data, error=error_msg, code=status_code)

        return super().render(envelope, accepted_media_type, renderer_context)


def _extract_error_message(data) -> str:
    """Extract a single error string from various DRF error formats."""
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        # {"detail": "..."} – most common
        if "detail" in data:
            detail = data["detail"]
            return str(detail)
        # {"field": ["error1", ...]} – validation errors
        messages = []
        for key, value in data.items():
            if isinstance(value, list):
                messages.append(f"{key}: {', '.join(str(v) for v in value)}")
            else:
                messages.append(f"{key}: {value}")
        return "; ".join(messages) if messages else "Unknown error"
    if isinstance(data, list):
        return "; ".join(str(item) for item in data)
    return str(data) if data else "Unknown error"


# ---------------------------------------------------------------------------
# Custom exception handler
# ---------------------------------------------------------------------------

def api_exception_handler(exc, context):
    """
    Catch DRF exceptions and return them in the standard envelope.

    Falls back to DRF's default handler for the heavy lifting, then
    re-wraps the response body.
    """
    response = drf_exception_handler(exc, context)

    if response is None:
        # DRF didn't handle it (unexpected server error)
        return None

    error_msg = _extract_error_message(response.data)
    response.data = api_envelope(
        data=response.data,
        error=error_msg,
        code=response.status_code,
    )
    return response


# ---------------------------------------------------------------------------
# Custom pagination – embeds paginated results inside the envelope
# ---------------------------------------------------------------------------

class ApiPagination(PageNumberPagination):
    """
    Page-number pagination that returns results in a structure
    compatible with the ApiRenderer wrapper.

    Inner payload (before the renderer wraps it):
    {
        "results": [...],
        "count": 42,
        "page": 1,
        "per_page": 20,
        "next": "http://...",
        "previous": null
    }
    """
    page_size = 20
    page_size_query_param = "per_page"
    max_page_size = 100
    page_query_param = "page"

    def get_paginated_response(self, data):
        return Response({
            "results": data,
            "count": self.page.paginator.count,
            "page": self.page.number,
            "per_page": self.get_page_size(self.request),
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
        })

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean", "example": True},
                "data": {
                    "type": "object",
                    "properties": {
                        "results": schema,
                        "count": {"type": "integer", "example": 42},
                        "page": {"type": "integer", "example": 1},
                        "per_page": {"type": "integer", "example": 20},
                        "next": {"type": "string", "nullable": True},
                        "previous": {"type": "string", "nullable": True},
                    },
                },
                "error": {"type": "string", "nullable": True},
                "code": {"type": "integer", "example": 200},
            },
        }
