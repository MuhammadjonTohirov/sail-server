from __future__ import annotations

import os
import sys
import json
from typing import Any, Dict

from django.core.management.base import BaseCommand
from django.conf import settings

from searchapp.opensearch_client import get_client
from searchapp.views.index import index_name


class Command(BaseCommand):
    help = "Check connectivity to OpenSearch and report basic health and index status"

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbose-json",
            action="store_true",
            help="Output raw JSON for info/health responses",
        )

    def handle(self, *args, **options):  # noqa: C901
        ok = True
        verbose_json = bool(options.get("verbose_json"))

        url = getattr(settings, "OPENSEARCH_URL", os.environ.get("OPENSEARCH_URL"))
        verify = os.environ.get("OPENSEARCH_VERIFY_CERTS", "false")
        idx = index_name()

        self.stdout.write("OpenSearch configuration:")
        self.stdout.write(f"  OPENSEARCH_URL: {url or '(not set)'}")
        self.stdout.write(f"  OPENSEARCH_VERIFY_CERTS: {verify}")
        self.stdout.write(f"  Index: {idx}")

        client = get_client()
        if client is None:
            self.stderr.write(self.style.ERROR("opensearch-py is not available or OPENSEARCH_URL is not set."))
            sys.exit(1)

        # Ping
        try:
            if not client.ping():  # type: ignore[attr-defined]
                self.stderr.write(self.style.ERROR("Ping failed — OpenSearch not reachable."))
                ok = False
            else:
                self.stdout.write(self.style.SUCCESS("Ping OK"))
        except Exception as e:  # pragma: no cover
            self.stderr.write(self.style.ERROR(f"Ping error: {type(e).__name__}: {e}"))
            ok = False

        # Info
        try:
            info: Dict[str, Any] = client.info()  # type: ignore[attr-defined]
            name = info.get("name") or info.get("cluster_name")
            version = (info.get("version") or {}).get("number")
            self.stdout.write(f"Cluster info: name={name}, version={version}")
            if verbose_json:
                self.stdout.write(json.dumps(info, indent=2, ensure_ascii=False))
        except Exception as e:  # pragma: no cover
            self.stderr.write(self.style.WARNING(f"Could not fetch cluster info: {type(e).__name__}: {e}"))

        # Health
        try:
            health: Dict[str, Any] = client.cluster.health()  # type: ignore[attr-defined]
            status = health.get("status")
            nodes = health.get("number_of_nodes")
            self.stdout.write(f"Cluster health: status={status}, nodes={nodes}")
            if verbose_json:
                self.stdout.write(json.dumps(health, indent=2, ensure_ascii=False))
            if status not in {"green", "yellow"}:
                ok = False
        except Exception as e:  # pragma: no cover
            self.stderr.write(self.style.WARNING(f"Could not fetch cluster health: {type(e).__name__}: {e}"))

        # Index existence and count
        try:
            exists = client.indices.exists(index=idx)  # type: ignore[attr-defined]
            if not exists:
                self.stderr.write(self.style.WARNING(f"Index '{idx}' does not exist."))
                ok = False
            else:
                self.stdout.write(self.style.SUCCESS(f"Index '{idx}' exists."))
                try:
                    cnt = client.count(index=idx).get("count", 0)  # type: ignore[attr-defined]
                    self.stdout.write(f"Documents in index: {cnt}")
                except Exception as e:
                    self.stderr.write(self.style.WARNING(f"Could not count documents: {type(e).__name__}: {e}"))
        except Exception as e:  # pragma: no cover
            self.stderr.write(self.style.ERROR(f"Index check error: {type(e).__name__}: {e}"))
            ok = False

        if ok:
            self.stdout.write(self.style.SUCCESS("OpenSearch connectivity looks OK."))
            sys.exit(0)
        else:
            self.stderr.write(self.style.ERROR("OpenSearch connectivity has problems. See messages above."))
            sys.exit(2)
