from django.core.management.base import BaseCommand

from listings.models import Listing
from searchapp.views.index import index_listing, index_name
from searchapp.views.opensearch_client import get_client


class Command(BaseCommand):
    help = "Reindex all listings into OpenSearch"

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all documents from the index before reindexing'
        )
        parser.add_argument(
            '--delete-stale',
            action='store_true',
            help='Delete documents from index that no longer exist in database'
        )
        parser.add_argument(
            '--if-empty',
            action='store_true',
            help='Only reindex when the index is missing or empty; never fail when '
                 'OpenSearch is unreachable. Safe to run as a deploy hook.'
        )

    def handle(self, *args, **options):
        client = get_client()
        if not client:
            self.stdout.write(self.style.ERROR("OpenSearch client not available"))
            return

        idx = index_name()

        # Deploy-safe guard: with --if-empty, only reindex a missing/empty index and
        # never fail when OpenSearch is unreachable (e.g. during a build with no network).
        if options.get('if_empty'):
            try:
                if not client.ping():
                    self.stdout.write(self.style.WARNING("OpenSearch unreachable; skipping reindex."))
                    return
                if client.indices.exists(index=idx) and client.count(index=idx).get("count", 0) > 0:
                    self.stdout.write("Index already populated; skipping reindex.")
                    return
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"Could not check index state ({type(e).__name__}); skipping reindex."
                ))
                return

        # Clear index if requested
        if options.get('clear'):
            self.stdout.write("Clearing index...")
            try:
                client.delete_by_query(
                    index=idx,
                    body={"query": {"match_all": {}}}
                )
                self.stdout.write(self.style.SUCCESS("Index cleared"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Failed to clear index: {e}"))

        # Delete stale documents
        if options.get('delete_stale'):
            self.stdout.write("Checking for stale documents...")
            try:
                # Get all document IDs from OpenSearch
                response = client.search(
                    index=idx,
                    body={
                        "query": {"match_all": {}},
                        "size": 10000,
                        "_source": False
                    }
                )

                index_ids = {hit['_id'] for hit in response['hits']['hits']}
                db_ids = set(Listing.objects.values_list('id', flat=True))

                stale_ids = index_ids - {str(id) for id in db_ids}

                if stale_ids:
                    self.stdout.write(f"Found {len(stale_ids)} stale documents")
                    for stale_id in stale_ids:
                        try:
                            client.delete(index=idx, id=stale_id)
                            self.stdout.write(f"Deleted stale document: {stale_id}")
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"Failed to delete {stale_id}: {e}"))
                else:
                    self.stdout.write("No stale documents found")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Failed to check stale documents: {e}"))

        # Reindex all listings
        qs = Listing.objects.filter(status=Listing.Status.ACTIVE).only("id")
        count = qs.count()
        self.stdout.write(f"Reindexing {count} active listings...")

        success = 0
        failed = 0
        for l in qs.iterator():
            try:
                index_listing(l.id)
                success += 1
                if success % 100 == 0:
                    self.stdout.write(f"Indexed {success}/{count}...")
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.WARNING(f"Failed to index {l.id}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"Reindex complete. Success: {success}, Failed: {failed}"
        ))

