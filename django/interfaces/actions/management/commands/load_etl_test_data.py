from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Loads test data from fixtures"

    def handle(self, *args, **kwargs):
        fixtures = [
            "tests/fixtures/test_etl_data_connections.yaml",
            "tests/fixtures/test_etl_orchestration_systems.yaml",
            "tests/fixtures/test_etl_tasks.yaml",
        ]

        for fixture in fixtures:
            self.stdout.write(self.style.NOTICE(f"Loading fixture: {fixture}"))
            try:
                call_command("loaddata", fixture)
                self.stdout.write(self.style.SUCCESS(f"Successfully loaded {fixture}"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to load {fixture}: {e}"))
