from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.conf import settings


class Command(BaseCommand):
    help = "Creates a default superuser if no superuser exists"

    def handle(self, *args, **kwargs):
        user_model = get_user_model()

        if not user_model.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.NOTICE(f"\nCreating default superuser..."))

            email = getattr(
                settings, "DEFAULT_SUPERUSER_EMAIL", "admin@hydroserver.org"
            )
            password = getattr(settings, "DEFAULT_SUPERUSER_PASSWORD", "pass")

            try:
                user_model.objects.create_superuser(email=email, password=password)
                self.stdout.write(self.style.SUCCESS(f"Superuser created: {email}"))
            except ValidationError as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed to create default superuser: {e}")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"An unexpected error occurred: {e}")
                )
