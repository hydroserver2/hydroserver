from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.db import connection, transaction
DEFAULT_FIXTURES = [
    "core/iam/fixtures/default_user_types.yaml",
    "core/iam/fixtures/default_organization_types.yaml",
    "core/iam/fixtures/default_roles.yaml",
    "core/sta/fixtures/default_datastream_aggregations.yaml",
    "core/sta/fixtures/default_datastream_statuses.yaml",
    "core/sta/fixtures/default_file_attachment_types.yaml",
    "core/sta/fixtures/default_method_types.yaml",
    "core/sta/fixtures/default_processing_levels.yaml",
    "core/sta/fixtures/default_sampled_mediums.yaml",
    "core/sta/fixtures/default_site_types.yaml",
    "core/sta/fixtures/default_units.yaml",
    "core/sta/fixtures/default_variable_types.yaml",
]


class Command(BaseCommand):
    help = "Reset and seed the database for deterministic end-to-end browser tests."

    def _flush_database(self):
        tables = connection.introspection.django_table_names(only_existing=True)
        sql_statements = connection.ops.sql_flush(
            no_style(),
            tables,
            reset_sequences=True,
            allow_cascade=True,
        )
        with connection.cursor() as cursor:
            for statement in sql_statements:
                cursor.execute(statement)

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Applying migrations..."))
        call_command("migrate", interactive=False, verbosity=0)

        self.stdout.write(self.style.NOTICE("Flushing database..."))
        self._flush_database()

        parsed_proxy_url = urlparse(settings.PROXY_BASE_URL)
        Site.objects.update_or_create(
            id=settings.SITE_ID,
            defaults={
                "domain": parsed_proxy_url.netloc or "127.0.0.1:14173",
                "name": "HydroServer E2E",
            },
        )

        with transaction.atomic():
            for fixture in DEFAULT_FIXTURES:
                self.stdout.write(self.style.NOTICE(f"Loading default fixture: {fixture}"))
                call_command("loaddata", fixture, verbosity=0)

        self.stdout.write(
            self.style.SUCCESS(
                "E2E database setup complete. Individual tests create and "
                "clean up isolated factory-built scenarios."
            )
        )
