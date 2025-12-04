def _lang_from_request(request) -> str:
    # Priority: explicit ?lang=uz|ru, else Accept-Language
    lang = request.query_params.get("lang")
    if lang in {"ru", "uz"}:
        return lang
    header = (request.META.get("HTTP_ACCEPT_LANGUAGE") or "").lower()
    if header.startswith("uz"):
        return "uz"
    return "ru"
