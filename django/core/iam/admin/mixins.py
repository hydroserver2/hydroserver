from pathlib import Path

from django.apps import apps as django_apps
from django.core import serializers
from django.core.management import call_command
from django.contrib.admin import ModelAdmin
from django.db.models import ForeignKey
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse


class LoadDefaultsMixin(ModelAdmin):
    default_fixture = None
    change_list_template = "admin/load_defaults_change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        if not self.default_fixture:
            return urls

        app = self.opts.app_label
        model = self.opts.model_name

        return [
            path(
                "load-defaults/",
                self.admin_site.admin_view(self.load_defaults_view),
                name=f"{app}_{model}_load_defaults",
            )
        ] + urls

    def _get_fixture_objects(self):
        fixture_name = self.default_fixture + ".json"

        for app_config in django_apps.get_app_configs():
            fixture_path = Path(app_config.path) / "fixtures" / fixture_name
            if fixture_path.exists():
                with fixture_path.open() as f:
                    return [d.object for d in serializers.deserialize("json", f)]

        return []

    def _build_preview(self):
        all_objects = self._get_fixture_objects()
        primary = [obj for obj in all_objects if isinstance(obj, self.model)]
        related = [obj for obj in all_objects if not isinstance(obj, self.model)]

        primary_by_pk = {str(obj.pk): obj for obj in primary}

        related_by_pk = {}
        for obj in related:
            for field in obj._meta.get_fields():
                if isinstance(field, ForeignKey) and field.related_model == self.model:
                    fk_val = str(getattr(obj, field.attname))
                    # Inject the in-memory parent so __str__ doesn't need a DB hit.
                    setattr(obj, field.name, primary_by_pk.get(fk_val))
                    related_by_pk.setdefault(fk_val, []).append(obj)
                    break

        to_create, to_overwrite = [], []
        for obj in primary:
            children = []
            for rel in related_by_pk.get(str(obj.pk), []):
                try:
                    children.append(str(rel))
                except (
                    Exception,
                ):  # __str__ may depend on relations not in the fixture
                    children.append(f"{rel._meta.verbose_name} ({rel.pk})")  # noqa
            exists = self.model.objects.filter(pk=obj.pk).exists()
            (to_overwrite if exists else to_create).append((obj, children))

        return to_create, to_overwrite

    def load_defaults_view(self, request):
        if request.method == "POST":
            call_command("loaddata", self.default_fixture)
            self.message_user(request, "Default data loaded successfully.")
            app = self.opts.app_label
            model = self.opts.model_name

            return HttpResponseRedirect(reverse(f"admin:{app}_{model}_changelist"))

        to_create, to_overwrite = self._build_preview()
        context = {
            **self.admin_site.each_context(request),
            "title": f"Load default {self.opts.verbose_name_plural}",
            "opts": self.opts,
            "to_create": to_create,
            "to_overwrite": to_overwrite,
        }

        return TemplateResponse(request, "admin/load_defaults_confirm.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        if self.default_fixture:
            app = self.opts.app_label
            model = self.opts.model_name
            extra_context["load_defaults_url"] = reverse(
                f"admin:{app}_{model}_load_defaults"
            )

        return super().changelist_view(request, extra_context=extra_context)
