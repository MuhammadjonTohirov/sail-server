from decimal import Decimal, InvalidOperation

from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import CurrencyService


class CurrencyConfigView(APIView):
    """
    Get currency configuration including all active currencies and exchange rates.
    Client will use this to perform currency conversions locally.
    """

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["currency"],
        summary="Get currency configuration",
        description="Get all active currencies, exchange rates, and the default currency.",
        examples=[
            OpenApiExample(
                "Success",
                value={"success": True, "data": {"currencies": [{"code": "UZS", "name": "Uzbek Sum", "symbol": "so'm"}], "exchange_rates": {"USD_UZS": 12500.0}, "default_currency": "UZS"}, "error": None, "code": 200},
                response_only=True,
            ),
        ],
    )
    def get(self, request):
        currencies = CurrencyService.get_active_currencies()
        exchange_rates = CurrencyService.get_exchange_rates()
        default_currency = CurrencyService.get_default_currency()

        return Response(
            {
                "currencies": currencies,
                "exchange_rates": exchange_rates,
                "default_currency": default_currency.code if default_currency else "UZS",
            }
        )


class CurrencyConvertView(APIView):
    """
    Convert amount from one currency to another.
    Query params: amount, from, to
    """

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["currency"],
        summary="Convert currency",
        description="Convert an amount from one currency to another.",
        parameters=[
            OpenApiParameter(name="amount", description="Amount to convert", required=True, type=float),
            OpenApiParameter(name="from", description="Source currency code (e.g. USD)", required=True, type=str),
            OpenApiParameter(name="to", description="Target currency code (e.g. UZS)", required=True, type=str),
        ],
        examples=[
            OpenApiExample(
                "Success",
                value={"success": True, "data": {"amount": 100.0, "from": "USD", "to": "UZS", "converted": 1250000.0, "rate": 12500.0}, "error": None, "code": 200},
                response_only=True,
            ),
        ],
    )
    def get(self, request):
        try:
            amount = Decimal(request.query_params.get("amount", "0"))
            from_currency = request.query_params.get("from", "").upper()
            to_currency = request.query_params.get("to", "").upper()

            if not from_currency or not to_currency:
                return Response(
                    {"detail": "Both 'from' and 'to' currency codes are required"}, status=400
                )

            converted = CurrencyService.convert_price(amount, from_currency, to_currency)

            if converted is None:
                return Response(
                    {"detail": f"Exchange rate not found for {from_currency} to {to_currency}"},
                    status=404,
                )

            return Response(
                {
                    "amount": float(amount),
                    "from": from_currency,
                    "to": to_currency,
                    "converted": float(converted),
                    "rate": float(
                        CurrencyService.get_exchange_rate(from_currency, to_currency) or 0
                    ),
                }
            )

        except (InvalidOperation, ValueError) as e:
            return Response({"detail": f"Invalid amount: {str(e)}"}, status=400)
