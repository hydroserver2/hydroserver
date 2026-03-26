import os
from urllib.parse import urlparse

from allauth.socialaccount.models import SocialApp
from decouple import config
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or update a Google SocialApp for local preview and attach it to the current Site."

    def add_arguments(self, parser):
        parser.add_argument(
            "--client-id",
            default=config("GOOGLE_OAUTH_CLIENT_ID", default=os.getenv("GOOGLE_OAUTH_CLIENT_ID")),
            help="Google OAuth client ID. Defaults to GOOGLE_OAUTH_CLIENT_ID when set.",
        )
        parser.add_argument(
            "--secret",
            default=config(
                "GOOGLE_OAUTH_CLIENT_SECRET",
                default=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
            ),
            help="Google OAuth client secret. Defaults to GOOGLE_OAUTH_CLIENT_SECRET when set.",
        )
        parser.add_argument(
            "--name",
            default="Google",
            help="Display name for the SocialApp.",
        )

    def handle(self, *args, **options):
        parsed_proxy_url = urlparse(settings.PROXY_BASE_URL)
        domain = parsed_proxy_url.hostname or "127.0.0.1"
        site, _ = Site.objects.update_or_create(
            id=settings.SITE_ID,
            defaults={"domain": domain, "name": domain},
        )

        client_id = options["client_id"] or "local-google-preview.apps.googleusercontent.com"
        secret = options["secret"] or "local-google-preview-secret"
        using_placeholder_credentials = not options["client_id"] or not options["secret"]

        social_app = (
            SocialApp.objects.filter(provider="google", provider_id__in=["", "google"])
            .order_by("id")
            .first()
        )
        created = social_app is None
        if social_app is None:
            social_app = SocialApp(provider="google")

        social_app.name = options["name"]
        social_app.provider_id = "google"
        social_app.client_id = client_id
        social_app.secret = secret
        social_app.settings = {
            **(social_app.settings or {}),
            "preview_only": using_placeholder_credentials,
        }
        social_app.save()
        social_app.sites.set([site])

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} Google SocialApp(id={social_app.id}) for Site(id={site.id}, domain={site.domain})."
            )
        )
        if using_placeholder_credentials:
            self.stdout.write(
                self.style.WARNING(
                    "Using placeholder Google credentials so the provider button appears locally. "
                    "Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET or rerun with "
                    "--client-id/--secret to enable a working Google OAuth flow."
                )
            )
