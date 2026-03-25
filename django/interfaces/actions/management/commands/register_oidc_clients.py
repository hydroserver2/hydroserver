from urllib.parse import urlparse

from allauth.idp.oidc.models import Client
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


def _values_to_text(values):
    return "\n".join(values)


def _validate_redirect_uris(client_key, redirect_uris):
    if not redirect_uris:
        raise CommandError(f"OIDC client '{client_key}' must define at least one redirect URI.")

    for uri in redirect_uris:
        parsed = urlparse(uri)
        if not parsed.scheme or not parsed.netloc:
            raise CommandError(
                f"OIDC client '{client_key}' has invalid redirect URI: {uri}"
            )


def _validate_cors_origins(client_key, cors_origins):
    for origin in cors_origins:
        parsed = urlparse(origin)
        if not parsed.scheme or not parsed.netloc:
            raise CommandError(
                f"OIDC client '{client_key}' has invalid CORS origin: {origin}"
            )
        if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
            raise CommandError(
                f"OIDC client '{client_key}' CORS origin must not include a path: {origin}"
            )


class Command(BaseCommand):
    help = "Create or update the bundled HydroServer OIDC clients."

    @transaction.atomic
    def handle(self, *args, **options):
        clients = getattr(settings, "OIDC_BUNDLED_CLIENTS", {})
        if not clients:
            self.stdout.write(self.style.WARNING("No bundled OIDC clients configured."))
            return

        for client_key, client_config in clients.items():
            redirect_uris = list(client_config.get("redirect_uris", []))
            cors_origins = list(client_config.get("cors_origins", []))

            _validate_redirect_uris(client_key, redirect_uris)
            _validate_cors_origins(client_key, cors_origins)

            client, created = Client.objects.update_or_create(
                id=client_config["id"],
                defaults={
                    "name": client_config["name"],
                    "type": Client.Type.PUBLIC,
                    "scopes": _values_to_text(["openid", "profile", "email"]),
                    "default_scopes": _values_to_text(["openid", "profile", "email"]),
                    "grant_types": _values_to_text(
                        [
                            Client.GrantType.AUTHORIZATION_CODE,
                            Client.GrantType.REFRESH_TOKEN,
                        ]
                    ),
                    "response_types": _values_to_text(["code"]),
                    "redirect_uris": _values_to_text(redirect_uris),
                    "cors_origins": _values_to_text(cors_origins),
                    "allow_uri_wildcards": False,
                    "skip_consent": True,
                },
            )

            action = "Created" if created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{action} OIDC client '{client_key}' ({client.id}) with "
                    f"{len(redirect_uris)} redirect URI(s)."
                )
            )
