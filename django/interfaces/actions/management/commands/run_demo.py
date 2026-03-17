from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command


class Command(BaseCommand):
    help = "Run migrations, setup admin, collect static files, and start the development server"

    def handle(self, *args, **options):
        try:
            call_command("migrate", interactive=False)
            call_command("setup_admin_user")
            call_command("collectstatic", interactive=False, clear=True)
            call_command("runserver", "0.0.0.0:8000")

        except Exception as e:
            raise CommandError(f"Error during startup: {e}")
