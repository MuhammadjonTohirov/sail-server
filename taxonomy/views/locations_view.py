from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Location
from ..serializers import LocationSerializer
from ._utils import _lang_from_request


class LocationsView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request):
        parent_id = request.query_params.get("parent_id")
        lang = _lang_from_request(request)
        if parent_id:
            try:
                pid = int(parent_id)
            except ValueError:
                return Response([], status=200)
            qs = Location.objects.filter(parent_id=pid).order_by("name")
        else:
            qs = Location.objects.filter(parent__isnull=True).order_by("name")
        return Response(LocationSerializer(qs, many=True, context={"request": request}).data)
