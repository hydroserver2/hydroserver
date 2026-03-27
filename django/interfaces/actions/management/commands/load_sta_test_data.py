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
            BASE_DIR / "tests/fixtures/test_things.yaml",
            BASE_DIR / "tests/fixtures/test_observed_properties.yaml",
            BASE_DIR / "tests/fixtures/test_processing_levels.yaml",
            BASE_DIR / "tests/fixtures/test_result_qualifiers.yaml",
            BASE_DIR / "tests/fixtures/test_sensors.yaml",
            BASE_DIR / "tests/fixtures/test_units.yaml",
            BASE_DIR / "tests/fixtures/test_datastreams.yaml",
            BASE_DIR / "tests/fixtures/test_observations.yaml",
        ]

        for fixture in fixtures:
            self.stdout.write(self.style.NOTICE(f"Loading fixture: {fixture}"))
            call_command("loaddata", str(fixture))
            self.stdout.write(self.style.SUCCESS(f"Successfully loaded {fixture}"))
