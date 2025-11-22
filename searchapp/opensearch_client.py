from __future__ import annotations

import os
from typing import Optional
from urllib.parse import urlparse, unquote

from django.conf import settings

try:
    from opensearchpy import OpenSearch
except Exception:  # pragma: no cover - library may be missing in some envs
    OpenSearch = None  # type: ignore


def get_client() -> Optional["OpenSearch"]:
    if OpenSearch is None:
        return None
    url = getattr(settings, "OPENSEARCH_URL", os.environ.get("OPENSEARCH_URL"))
    if not url:
        return None
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 9200)
        scheme = parsed.scheme or "http"
        http_auth = None
        if parsed.username:
            http_auth = (
                unquote(parsed.username),
                unquote(parsed.password or ""),
            )
        verify_env = os.environ.get("OPENSEARCH_VERIFY_CERTS", "false").lower() in {"1", "true", "yes"}
        client = OpenSearch(
            hosts=[{"host": host, "port": port, "scheme": scheme}],
            http_auth=http_auth,
            use_ssl=(scheme == "https"),
            verify_certs=verify_env,
            ssl_show_warn=False,
        )
        return client
    except Exception:
        # fall back to simple constructor; let caller handle ping
        return OpenSearch(hosts=[url])
