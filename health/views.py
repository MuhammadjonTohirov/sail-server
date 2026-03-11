from django.http import JsonResponse
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response


def liveness(request):
    return JsonResponse({"status": "ok"})


class ApiHealthView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["health"],
        summary="API health check",
        description="Check if the API server is running and responding.",
        examples=[
            OpenApiExample(
                "Success",
                value={"success": True, "data": {"status": "ok", "service": "server", "version": 1}, "error": None, "code": 200},
                response_only=True,
            ),
        ],
    )
    def get(self, request):
        return Response({"status": "ok", "service": "server", "version": 1})


class I18nView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["health"],
        summary="Get current language",
        description="Get the active language from cookie or Accept-Language header.",
        examples=[
            OpenApiExample(
                "Success",
                value={"success": True, "data": {"lang": "ru"}, "error": None, "code": 200},
                response_only=True,
            ),
        ],
    )
    def get(self, request):
        # Report active language (from cookie or Accept-Language)
        lang = request.COOKIES.get("django_language")
        if not lang:
            header = (request.META.get("HTTP_ACCEPT_LANGUAGE") or "").lower()
            lang = "uz" if header.startswith("uz") else "ru"
        return Response({"lang": lang})

    @extend_schema(
        tags=["health"],
        summary="Set language preference",
        description="Set the active language preference via cookie. Accepts 'ru' or 'uz'.",
        examples=[
            OpenApiExample(
                "Success",
                value={"success": True, "data": {"lang": "uz", "status": "set"}, "error": None, "code": 200},
                response_only=True,
            ),
        ],
    )
    def post(self, request):
        lang = (request.data or {}).get("lang")
        if lang not in {"ru", "uz"}:
            return Response({"detail": "lang must be 'ru' or 'uz'"}, status=400)
        resp = Response({"lang": lang, "status": "set"})
        # Set session cookie used by LocaleMiddleware
        resp.set_cookie("django_language", lang, max_age=60 * 60 * 24 * 365, samesite="Lax")
        return resp
