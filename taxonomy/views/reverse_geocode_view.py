from math import sqrt

from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Location
from ..serializers import LocationSerializer
from ._utils import _lang_from_request


class ReverseGeocodeView(APIView):
    """
    Reverse geocode: given lat/lon coordinates, find the nearest location.
    Returns the most specific location (city/district) if available.
    """
    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request):
        try:
            lat = float(request.query_params.get("lat", 0))
            lon = float(request.query_params.get("lon", 0))
        except (TypeError, ValueError):
            return Response({"error": "Invalid coordinates"}, status=400)

        if lat == 0 and lon == 0:
            return Response({"error": "Coordinates required"}, status=400)

        lang = _lang_from_request(request)

        # Find locations with coordinates
        locations_with_coords = Location.objects.filter(
            lat__isnull=False,
            lon__isnull=False
        ).exclude(lat=0, lon=0)

        if not locations_with_coords.exists():
            return Response({"error": "No locations with coordinates available"}, status=404)

        # Calculate distances and find nearest
        nearest = None
        min_distance = float('inf')

        for loc in locations_with_coords:
            # Simple Euclidean distance (good enough for city-level matching)
            distance = sqrt((loc.lat - lat) ** 2 + (loc.lon - lon) ** 2)
            if distance < min_distance:
                min_distance = distance
                nearest = loc

        if not nearest:
            return Response({"error": "No nearby location found"}, status=404)

        # Build the location path (from root to leaf)
        path_parts = []
        current = nearest
        location_chain = []

        while current:
            location_chain.insert(0, current)
            name = getattr(current, f"name_{lang}", None) or current.name
            path_parts.insert(0, name)
            current = current.parent

        path = " > ".join(path_parts)

        # Serialize the location
        serialized = LocationSerializer(nearest, context={"request": request}).data
        serialized["path"] = path
        serialized["distance"] = min_distance

        return Response(serialized)
