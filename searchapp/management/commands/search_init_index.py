from django.core.management.base import BaseCommand

from searchapp.views.index import ensure_index


class Command(BaseCommand):
    help = "Create the OpenSearch index with mappings if it does not exist"

    def handle(self, *args, **options):
        ensure_index()
        self.stdout.write(self.style.SUCCESS("Index ensured."))

