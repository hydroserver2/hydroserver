from pathlib import Path

from django.core.management.base import BaseCommand
from django.core.management import call_command


BASE_DIR = Path(__file__).resolve().parents[4]


class Command(BaseCommand):
    help = "Loads test data from fixtures"

    def handle(self, *args, **kwargs):
        fixtures = [
            BASE_DIR / "tests/fixtures/test_users.yaml",
            BASE_DIR / "tests/fixtures/test_workspaces.yaml",
            BASE_DIR / "tests/fixtures/test_roles.yaml",
            BASE_DIR / "tests/fixtures/test_collaborators.yaml",
            BASE_DIR / "tests/fixtures/test_api_keys.yaml",
        ]

        for fixture in fixtures:
            self.stdout.write(self.style.NOTICE(f"Loading fixture: {fixture}"))
            call_command("loaddata", str(fixture))
            self.stdout.write(self.style.SUCCESS(f"Successfully loaded {fixture}"))
