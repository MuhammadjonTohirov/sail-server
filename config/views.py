from __future__ import annotations

from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse


def admin_set_language(request: HttpRequest):
    """Simple admin helper to switch UI language via cookie.

    Expects POST with form field 'lang' in {'ru','uz'} and redirects back.
    """
    lang = (request.POST or {}).get("lang")
    if lang not in {"ru", "uz"}:
        # ignore invalid, just redirect back
        next_url = request.META.get("HTTP_REFERER") or reverse("admin:index")
        return HttpResponseRedirect(next_url)
    next_url = request.META.get("HTTP_REFERER") or reverse("admin:index")
    resp = HttpResponseRedirect(next_url)
    resp.set_cookie("django_language", lang, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return resp

