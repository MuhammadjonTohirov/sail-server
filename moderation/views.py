from __future__ import annotations

from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Report
from .serializers import ReportCreateSerializer, ReportSerializer


class ReportCreateView(generics.CreateAPIView):
    serializer_class = ReportCreateSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        reporter = self.request.user if self.request.user and self.request.user.is_authenticated else None
        serializer.save(reporter=reporter)


class ModerationQueueView(generics.ListAPIView):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return Report.objects.filter(status=Report.Status.OPEN).order_by("-created_at")


REPORT_REASONS = [
    {
        "code": "seller_info",
        "title": {
            "ru": "Неверная информация о продавце",
            "uz": "Sotuvchi haqida noto‘g‘ri maʼlumot",
        },
        "description": {
            "ru": "Например, чужая фотография или контактные данные",
            "uz": "Masalan, begonaning surati yoki noto‘g‘ri aloqa maʼlumoti",
        },
    },
    {
        "code": "product_issue",
        "title": {
            "ru": "Проблема с товаром или услугой",
            "uz": "Mahsulot yoki xizmat bilan muammo",
        },
        "description": {
            "ru": "Запрещённый товар, подделка, нелегальная продажа животных и др.",
            "uz": "Taʼqiqlangan mahsulot, qalbaki tovar, hayvonlarning noqonuniy savdosi va h.k.",
        },
        "children": [
            {
                "code": "banned_goods",
                "title": {
                    "ru": "Запрещённый товар или услуга",
                    "uz": "Taʼqiqlangan mahsulot yoki xizmat",
                },
                "description": {
                    "ru": "Оружие, наркотики, опасные вещества, иные запрещённые предметы",
                    "uz": "Qurol-aslaha, narkotiklar, xavfli modda va boshqa taʼqiqlangan narsalar",
                },
            },
            {
                "code": "counterfeit",
                "title": {
                    "ru": "Контрафактный товар",
                    "uz": "Qalbaki mahsulot",
                },
                "description": {
                    "ru": "Поддельные бренды, подделанные документы и другое",
                    "uz": "Soxta brendlar, qalbaki hujjatlar va boshqalar",
                },
            },
            {
                "code": "illegal_animals",
                "title": {
                    "ru": "Нелегальная продажа животных",
                    "uz": "Hayvonlarning noqonuniy savdosi",
                },
                "description": {
                    "ru": "Редкие виды, незарегистрированные питомники",
                    "uz": "Noyob turlar, ro‘yxatdan o‘tmagan pitomniklar",
                },
            },
        ],
    },
    {
        "code": "misleading",
        "title": {
            "ru": "Вводящее в заблуждение объявление",
            "uz": "Chalg‘ituvchi eʼlon",
        },
        "description": {
            "ru": "Недостоверная или противоречивая информация, обман",
            "uz": "Noto‘g‘ri yoki qarama-qarshi maʼlumot, chalg‘itish",
        },
    },
    {
        "code": "fraud",
        "title": {
            "ru": "Мошенничество",
            "uz": "Firibgarlik",
        },
        "description": {
            "ru": "Попытка получить деньги или данные обманным путём",
            "uz": "Pul yoki maʼlumotlarni aldov bilan qo‘lga kiritishga urinish",
        },
    },
    {
        "code": "abuse",
        "title": {
            "ru": "Жестокость, дискриминация, обнажённое тело",
            "uz": "Zo‘ravonlik, diskriminatsiya, yalang‘ochlik",
        },
        "description": {
            "ru": "Оскорбительный или недопустимый контент",
            "uz": "Haqoratli yoki nomaqbul kontent",
        },
    },
]


class ReportReasonsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        lang = request.query_params.get("lang", "ru")
        if lang not in {"ru", "uz", "en"}:
            lang = "ru"

        def serialize(nodes):
            data = []
            for node in nodes:
                item = {
                    "code": node["code"],
                    "title": node["title"].get(lang) or node["title"].get("ru"),
                }
                description = node.get("description")
                if description:
                    item["description"] = description.get(lang) or description.get("ru")
                children = node.get("children", [])
                if children:
                    item["children"] = serialize(children)
                data.append(item)
            return data

        return Response({"items": serialize(REPORT_REASONS)})
