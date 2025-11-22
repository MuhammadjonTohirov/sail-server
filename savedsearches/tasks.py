from __future__ import annotations

from datetime import datetime, timezone

from celery import shared_task

from .models import SavedSearch
from searchapp.opensearch_client import get_client
from searchapp.index import index_name


@shared_task(name="savedsearches.run")
def task_run_saved_searches():
    client = get_client()
    if not client:
        return {"status": "skipped", "reason": "no-opensearch"}
    processed = 0
    for s in SavedSearch.objects.filter(is_active=True).iterator():
        q = s.query or {}
        body = q.get("body") or {"query": {"bool": {}}}
        client.search(index=index_name(), body=body)
        s.last_sent_at = datetime.now(timezone.utc)
        s.save(update_fields=["last_sent_at"])
        processed += 1
    return {"status": "ok", "processed": processed}

