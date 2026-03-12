from uuid import UUID
from datetime import datetime, timedelta, timezone
from django.core.management.base import BaseCommand
from django.core.management import call_command
from domains.sta.models import Datastream
from interfaces.actions.management.utils import generate_test_timeseries


class Command(BaseCommand):
    help = "Create test datastreams with observations"

    def add_arguments(self, parser):
        parser.add_argument(
            "num_observations", type=int, help="The number of observations to create"
        )

    def handle(self, *args, **kwargs):
        num_observations = kwargs["num_observations"]

        fixtures = [
            "tests/fixtures/test_users.yaml",
            "tests/fixtures/test_workspaces.yaml",
            "tests/fixtures/test_roles.yaml",
            "tests/fixtures/test_collaborators.yaml",
            "tests/fixtures/bulk_test_data.yaml",
        ]

        for fixture in fixtures:
            self.stdout.write(self.style.NOTICE(f"Loading fixture: {fixture}"))
            try:
                call_command("loaddata", fixture)
                self.stdout.write(self.style.SUCCESS(f"Successfully loaded {fixture}"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to load {fixture}: {e}"))

        phenomenon_begin_time = datetime(2010, 1, 1, tzinfo=timezone.utc)
        phenomenon_end_time = phenomenon_begin_time + timedelta(
            minutes=15 * num_observations
        )

        datastream = Datastream.objects.create(
            name=f"Test Datastream with {num_observations} observations.",
            description=f"Test Datastream with {num_observations} observations.",
            thing_id=UUID("97d08ec5-0c29-49e4-906a-9b3f7a09e5ac"),
            sensor_id=UUID("c830a6b5-cb53-4596-90d9-b4d99bdc314d"),
            observed_property_id=UUID("ebc5664e-0e1c-48a0-8fe0-c64dae472e30"),
            processing_level_id=UUID("9ce74667-e709-416d-96e2-bf54db2025ed"),
            unit_id=UUID("41afe53b-2c81-499b-bab3-94cad15b0bd1"),
            observation_type="Observation",
            result_type="Time Series",
            status="Test",
            sampled_medium="Air",
            value_count=num_observations,
            no_data_value=-9999,
            intended_time_spacing=15,
            intended_time_spacing_unit="minutes",
            aggregation_statistic="Continuous",
            time_aggregation_interval=0,
            time_aggregation_interval_unit="minutes",
            phenomenon_begin_time=phenomenon_begin_time,
            phenomenon_end_time=phenomenon_end_time,
            is_private=False,
            is_visible=True,
        )

        generate_test_timeseries(datastream.id)
