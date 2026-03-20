from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from domains.etl.models import Task, TaskRun


class Command(BaseCommand):
    help = "Removes old TaskRun records, keeping the most recent per Task."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=14,
            help="Number of days to keep TaskRun records. Older runs will be deleted. Default is 14.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        now = timezone.now()
        cutoff = now - timedelta(days=days)

        total_deleted = 0

        tasks = Task.objects.filter(
            taskrun__started_at__lt=cutoff
        ).distinct()

        for task in tasks:
            most_recent_run = TaskRun.objects.filter(task=task).order_by("-started_at").first()

            deleted, _ = TaskRun.objects.filter(
                task=task,
                started_at__lt=cutoff
            ).exclude(pk=most_recent_run.pk).delete()

            total_deleted += deleted

        self.stdout.write(
            self.style.SUCCESS(
                f"Cleanup complete. Deleted {total_deleted} old TaskRun records older than {days} days."
            )
        )
