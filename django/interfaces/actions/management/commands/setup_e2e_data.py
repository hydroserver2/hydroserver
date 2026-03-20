from urllib.parse import urlparse

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.db import connection, transaction
from domains.iam.models import Organization


User = get_user_model()


E2E_PASSWORD = "HydroServer123!"
FIXTURE_USER_EMAILS = [
    "owner@example.com",
    "editor@example.com",
    "viewer@example.com",
    "unaffiliated@example.com",
    "limited@example.com",
    "inactive@example.com",
    "admin@example.com",
    "staff@example.com",
]
EXTRA_E2E_USERS = {
    "profile@example.com": {
        "first_name": "Profile",
        "last_name": "Example",
        "is_active": True,
        "is_staff": False,
        "is_superuser": False,
        "is_ownership_allowed": True,
        "user_type": "Other",
        "organization": {
            "code": "E2E",
            "name": "E2E Test Organization",
            "description": "Deterministic organization for browser profile tests.",
            "organization_type": "Other",
            "link": "https://example.com/org/e2e-profile",
        },
    },
    "delete-me@example.com": {
        "first_name": "Delete",
        "last_name": "Me",
        "is_active": True,
        "is_staff": False,
        "is_superuser": False,
        "is_ownership_allowed": False,
        "user_type": "Other",
    },
}

DEFAULT_FIXTURES = [
    "domains/iam/fixtures/default_user_types.yaml",
    "domains/iam/fixtures/default_organization_types.yaml",
    "domains/iam/fixtures/default_roles.yaml",
    "domains/sta/fixtures/default_datastream_aggregations.yaml",
    "domains/sta/fixtures/default_datastream_statuses.yaml",
    "domains/sta/fixtures/default_file_attachment_types.yaml",
    "domains/sta/fixtures/default_method_types.yaml",
    "domains/sta/fixtures/default_processing_levels.yaml",
    "domains/sta/fixtures/default_sampled_mediums.yaml",
    "domains/sta/fixtures/default_site_types.yaml",
    "domains/sta/fixtures/default_units.yaml",
    "domains/sta/fixtures/default_variable_types.yaml",
    "domains/etl/fixtures/default_orchestration_systems.yaml",
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

    def _seed_extra_users(self):
        for email, attrs in EXTRA_E2E_USERS.items():
            organization_attrs = attrs.get("organization")
            organization = None
            if organization_attrs:
                organization, _ = Organization.objects.update_or_create(
                    code=organization_attrs["code"],
                    defaults=organization_attrs,
                )

            defaults = {
                "username": email,
                "email": email,
                "first_name": attrs["first_name"],
                "last_name": attrs["last_name"],
                "is_active": attrs["is_active"],
                "is_staff": attrs["is_staff"],
                "is_superuser": attrs["is_superuser"],
                "is_ownership_allowed": attrs["is_ownership_allowed"],
                "user_type": attrs["user_type"],
                "organization": organization,
            }
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User(email=email)
            for field, value in defaults.items():
                setattr(user, field, value)
            user.save()
            user.set_password(E2E_PASSWORD)
            user.save(update_fields=["password"])
            EmailAddress.objects.update_or_create(
                user=user,
                primary=True,
                defaults={
                    "email": user.email,
                    "verified": True,
                },
            )

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

            self.stdout.write(self.style.NOTICE("Loading IAM test data..."))
            call_command("load_iam_test_data")

            self.stdout.write(self.style.NOTICE("Loading STA test data..."))
            call_command("load_sta_test_data")

            self.stdout.write(self.style.NOTICE("Loading ETL test data..."))
            call_command("load_etl_test_data")

            for email in FIXTURE_USER_EMAILS:
                user = User.objects.get(email=email)
                user.set_password(E2E_PASSWORD)
                user.save(update_fields=["password"])
                EmailAddress.objects.update_or_create(
                    user=user,
                    primary=True,
                    defaults={
                        "email": user.email,
                        "verified": True,
                    },
                )

            self.stdout.write(self.style.NOTICE("Seeding dedicated E2E users..."))
            self._seed_extra_users()

        self.stdout.write(
            self.style.SUCCESS(
                "E2E data setup complete. Seeded users use password "
                f"'{E2E_PASSWORD}'."
            )
        )
