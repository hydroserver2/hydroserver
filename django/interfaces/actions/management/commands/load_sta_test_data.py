from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Loads test data from fixtures"

    def handle(self, *args, **kwargs):
        fixtures = [
            "tests/fixtures/test_users.yaml",
            "tests/fixtures/test_workspaces.yaml",
            "tests/fixtures/test_roles.yaml",
            "tests/fixtures/test_collaborators.yaml",
            "tests/fixtures/test_things.yaml",
            "tests/fixtures/test_observed_properties.yaml",
            "tests/fixtures/test_processing_levels.yaml",
            "tests/fixtures/test_result_qualifiers.yaml",
            "tests/fixtures/test_sensors.yaml",
            "tests/fixtures/test_units.yaml",
            "tests/fixtures/test_datastreams.yaml",
            "tests/fixtures/test_observations.yaml",
        ]

        for fixture in fixtures:
            self.stdout.write(self.style.NOTICE(f"Loading fixture: {fixture}"))
            try:
                call_command("loaddata", fixture)
                self.stdout.write(self.style.SUCCESS(f"Successfully loaded {fixture}"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to load {fixture}: {e}"))
