from decimal import Decimal, InvalidOperation

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

    def get(self, request):
        try:
            amount = Decimal(request.query_params.get("amount", "0"))
            from_currency = request.query_params.get("from", "").upper()
            to_currency = request.query_params.get("to", "").upper()

            if not from_currency or not to_currency:
                return Response(
                    {"error": "Both 'from' and 'to' currency codes are required"}, status=400
                )

            converted = CurrencyService.convert_price(amount, from_currency, to_currency)

            if converted is None:
                return Response(
                    {"error": f"Exchange rate not found for {from_currency} to {to_currency}"},
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
            return Response({"error": f"Invalid amount: {str(e)}"}, status=400)
