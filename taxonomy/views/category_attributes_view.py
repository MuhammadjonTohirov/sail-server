from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Attribute, Category
from ..serializers import AttributeSerializer
from ._utils import _lang_from_request


class CategoryAttributesView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request, pk: int):
        lang = _lang_from_request(request)
        # Collect this category and its ancestors to expose inherited attributes
        try:
            cat = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response([], status=200)
        ids = []
        cur = cat
        while cur is not None:
            ids.append(cur.id)
            cur = cur.parent  # type: ignore[attr-defined]
        attrs = Attribute.objects.filter(category_id__in=ids).order_by("key")
        return Response(AttributeSerializer(attrs, many=True, context={"request": request, "lang": lang}).data)
