from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction
from django.conf import settings
from core.web.models import InstanceConfiguration


class Command(BaseCommand):
    help = "Loads default data into database"

    def handle(self, *args, **kwargs):
        if InstanceConfiguration.objects.exists():
            self.stdout.write(
                self.style.NOTICE(
                    "Instance configuration already exists. Skipping default data load."
                )
            )
            return

        with transaction.atomic():
            self.stdout.write("Creating default instance configuration...")
            InstanceConfiguration.get_configuration()

            if settings.LOAD_DEFAULT_DATA:
                self.stdout.write("Loading default fixtures...")
                fixtures = [
                    "core/iam/fixtures/default_user_types.yaml",
                    "core/iam/fixtures/default_organization_types.yaml",
                    "core/iam/fixtures/default_roles.yaml",
                    "core/sta/fixtures/default_datastream_aggregations.yaml",
                    "core/sta/fixtures/default_datastream_statuses.yaml",
                    "core/sta/fixtures/default_method_types.yaml",
                    "core/sta/fixtures/default_processing_levels.yaml",
                    "core/sta/fixtures/default_sampled_mediums.yaml",
                    "core/sta/fixtures/default_units.yaml",
                    "core/sta/fixtures/default_variable_types.yaml",
                ]
                for fixture in fixtures:
                    self.stdout.write(f"Loading {fixture}...")
                    call_command("loaddata", fixture, verbosity=1)

                self.stdout.write(
                    self.style.SUCCESS("Default data loaded successfully.")
                )
