import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core.interfaces.api.urls import api
from core.interfaces.auth.urls import auth_api


SCHEMA_TARGETS = {
    "data.openapi.json": (api, "/api/data/"),
    "auth.openapi.json": (auth_api, "/api/auth/"),
}


def serialize_schema(schema):
    if hasattr(schema, "model_dump"):
        return schema.model_dump(mode="json", by_alias=True, exclude_none=True)
    if hasattr(schema, "dict"):
        return schema.dict(by_alias=True, exclude_none=True)
    return schema


class Command(BaseCommand):
    help = "Export backend-owned OpenAPI schemas for HydroServer clients."

    def add_arguments(self, parser):
        parser.add_argument(
            "--out-dir",
            default=str(Path(settings.BASE_DIR) / "contracts" / "openapi"),
            help="Directory where OpenAPI schema files should be written.",
        )

    def handle(self, *args, **options):
        out_dir = Path(options["out_dir"]).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        for filename, (ninja_api, path_prefix) in SCHEMA_TARGETS.items():
            schema = serialize_schema(
                ninja_api.get_openapi_schema(path_prefix=path_prefix)
            )
            out_file = out_dir / filename
            out_file.write_text(
                json.dumps(schema, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            self.stdout.write(
                self.style.SUCCESS(f"Exported OpenAPI schema to {out_file}")
            )
