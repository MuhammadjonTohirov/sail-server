"""
Shared OpenAPI schema helpers for drf-spectacular.

Provides reusable response schemas that reflect the standard API envelope.
"""
from __future__ import annotations

from drf_spectacular.utils import OpenApiExample, OpenApiResponse, inline_serializer
from rest_framework import serializers


# ---------------------------------------------------------------------------
# Reusable envelope serializers
# ---------------------------------------------------------------------------

def envelope_serializer(name: str, data_serializer=None, data_field=None):
    """
    Build an inline serializer that wraps *data_serializer* (or *data_field*)
    in the standard ``{success, data, error, code}`` envelope.
    """
    if data_field is None and data_serializer is not None:
        data_field = data_serializer()
    fields = {
        "success": serializers.BooleanField(default=True),
        "data": data_field or serializers.JSONField(allow_null=True),
        "error": serializers.CharField(allow_null=True, default=None),
        "code": serializers.IntegerField(default=200),
    }
    return inline_serializer(name=name, fields=fields)


def error_envelope_serializer(name: str = "ErrorResponse"):
    """Envelope for error responses."""
    return inline_serializer(name=name, fields={
        "success": serializers.BooleanField(default=False),
        "data": serializers.JSONField(allow_null=True, default=None),
        "error": serializers.CharField(),
        "code": serializers.IntegerField(),
    })


# ---------------------------------------------------------------------------
# Reusable OpenApiResponse helpers
# ---------------------------------------------------------------------------

def success_response(description: str = "Success", serializer=None, examples=None):
    """Build an OpenApiResponse for 200/201 with envelope."""
    return OpenApiResponse(
        response=serializer,
        description=description,
        examples=examples or [],
    )


def error_response(description: str = "Error", status_code: int = 400):
    """Build an OpenApiResponse for error status codes."""
    return OpenApiResponse(
        response=error_envelope_serializer(f"Error{status_code}Response"),
        description=description,
    )


# ---------------------------------------------------------------------------
# Common response maps (reuse across views)
# ---------------------------------------------------------------------------

COMMON_ERROR_RESPONSES = {
    400: error_response("Bad request", 400),
    401: error_response("Authentication required", 401),
    403: error_response("Permission denied", 403),
    404: error_response("Not found", 404),
    429: error_response("Rate limit exceeded", 429),
}

AUTH_ERROR_RESPONSES = {
    400: error_response("Invalid credentials or data", 400),
    429: error_response("Rate limit exceeded", 429),
}


# ---------------------------------------------------------------------------
# Common examples
# ---------------------------------------------------------------------------

SUCCESS_EXAMPLE = OpenApiExample(
    name="Success",
    value={"success": True, "data": {}, "error": None, "code": 200},
)

ERROR_400_EXAMPLE = OpenApiExample(
    name="Validation error",
    value={"success": False, "data": {"detail": "Invalid input."}, "error": "Invalid input.", "code": 400},
    status_codes=["400"],
)

ERROR_404_EXAMPLE = OpenApiExample(
    name="Not found",
    value={"success": False, "data": {"detail": "Not found"}, "error": "Not found", "code": 404},
    status_codes=["404"],
)
