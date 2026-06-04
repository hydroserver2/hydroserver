from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from processing.orchestration.models import Task, TaskRun
from processing.orchestration.tasks import STALE_PENDING_MINUTES


class Command(BaseCommand):
    help = "Removes old TaskRun records, keeping the most recent per Task."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=14,
            help="Number of days to keep TaskRun records. Older runs will be deleted. Default is 14.",
        )
        parser.add_argument(
            "--stale-pending-minutes",
            type=int,
            default=STALE_PENDING_MINUTES,
            help=f"Delete PENDING runs older than this many minutes. Default is {STALE_PENDING_MINUTES}.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        stale_pending_minutes = options["stale_pending_minutes"]
        now = timezone.now()
        cutoff = now - timedelta(days=days)
        pending_cutoff = now - timedelta(minutes=stale_pending_minutes)

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

        stale_deleted, _ = TaskRun.objects.filter(
            status="PENDING", started_at__lt=pending_cutoff
        ).delete()
        total_deleted += stale_deleted

        self.stdout.write(
            self.style.SUCCESS(
                f"Cleanup complete. Deleted {total_deleted - stale_deleted} old TaskRun records older than {days} days"
                f" and {stale_deleted} stale PENDING runs."
            )
        )
