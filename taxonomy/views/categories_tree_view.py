from typing import Any, Dict, List

from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Category
from ..serializers import CategoryNodeSerializer
from ._utils import _lang_from_request


class CategoriesTreeView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request):
        parent_id = request.query_params.get("parent_id")
        lang = _lang_from_request(request)
        qs = Category.objects.all().order_by("order", "name")
        if parent_id:
            try:
                pid = int(parent_id)
                qs = qs.filter(parent_id=pid)
                # Only return direct children as a flat list
                data = [
                    {
                        "id": c.id,
                        "name": (c.name_uz if lang == "uz" else c.name_ru) or c.name,
                        "slug": c.slug,
                        "icon": c.icon,
                        "icon_url": (c.icon_image.url if c.icon_image else ""),
                        "is_leaf": c.is_leaf,
                        "order": c.order,
                        "children": [],
                    }
                    for c in qs
                ]
                return Response(CategoryNodeSerializer(data, many=True).data)
            except ValueError:
                pass

        # Build full tree from roots
        categories = list(qs)
        nodes: Dict[int, Dict[str, Any]] = {}
        roots: List[Dict[str, Any]] = []
        for c in categories:
            nodes[c.id] = {
                "id": c.id,
                "name": (c.name_uz if lang == "uz" else c.name_ru) or c.name,
                "slug": c.slug,
                "icon": c.icon,
                "icon_url": (c.icon_image.url if c.icon_image else ""),
                "is_leaf": c.is_leaf,
                "order": c.order,
                "children": [],
            }
        for c in categories:
            node = nodes[c.id]
            if c.parent_id and c.parent_id in nodes:
                nodes[c.parent_id]["children"].append(node)
            else:
                roots.append(node)
        # Ensure child order
        def sort_children(arr: List[Dict[str, Any]]):
            arr.sort(key=lambda n: (n.get("order", 0), n.get("name", "")))
            for n in arr:
                sort_children(n["children"])  # type: ignore

        sort_children(roots)
        return Response(CategoryNodeSerializer(roots, many=True).data)
