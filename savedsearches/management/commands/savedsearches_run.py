from django.core.management.base import BaseCommand

from savedsearches.tasks import task_run_saved_searches


class Command(BaseCommand):
    help = "Run saved searches and update last_sent_at (dev utility)"

    def handle(self, *args, **options):
        result = task_run_saved_searches.apply().get()
        self.stdout.write(self.style.SUCCESS(f"Saved searches run result: {result}"))

