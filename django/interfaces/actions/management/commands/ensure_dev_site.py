from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Ensure the configured django.contrib.sites entry exists for local development."

    def handle(self, *args, **options):
        parsed_proxy_url = urlparse(settings.PROXY_BASE_URL)
        domain = parsed_proxy_url.hostname or "127.0.0.1"
        site, created = Site.objects.update_or_create(
            id=settings.SITE_ID,
            defaults={
                "domain": domain,
                "name": domain,
            },
        )

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} Site(id={site.id}, domain={site.domain}, name={site.name})"
            )
        )
