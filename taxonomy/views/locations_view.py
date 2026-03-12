from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Location
from ..serializers import LocationSerializer
from ._utils import _lang_from_request


class LocationsView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    @extend_schema(
        tags=["taxonomy"],
        summary="List locations",
        description="List root locations or children of a specific parent location.",
        parameters=[
            OpenApiParameter(name="parent_id", description="Filter by parent location ID", required=False, type=int),
        ],
        examples=[
            OpenApiExample(
                "Success",
                value={"success": True, "data": [{"id": 1, "name": "Tashkent", "slug": "tashkent"}], "error": None, "code": 200},
                response_only=True,
            ),
        ],
    )
    def get(self, request):
        parent_id = request.query_params.get("parent_id")
        if parent_id:
            try:
                pid = int(parent_id)
            except ValueError:
                return Response([], status=200)
            qs = Location.objects.filter(parent_id=pid).order_by("name")
        else:
            roots = list(Location.objects.filter(parent__isnull=True).order_by("name"))
            if len(roots) == 1 and roots[0].kind == Location.Kind.COUNTRY:
                qs = Location.objects.filter(parent=roots[0]).order_by("name")
            else:
                qs = roots
        return Response(LocationSerializer(qs, many=True, context={"request": request}).data)
