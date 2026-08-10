import uuid
from collections import defaultdict
from typing import Optional, Literal, get_args
from ninja.errors import HttpError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Count, QuerySet, Q, FloatField, Subquery, OuterRef, IntegerField
from django.db.models.functions import Cast, Coalesce
from django.utils import timezone
from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.service import ServiceUtils
from core.sta.cache import (
    get_public_monitoring_site_markers_cache,
    set_public_monitoring_site_markers_cache,
)
from core.sta.models import (
    MonitoringSite,
    MonitoringSiteFileAttachment,
    SiteType,
    FileAttachmentType,
)
from interfaces.api.schemas import (
    MonitoringSiteSummaryResponse,
    MonitoringSiteDetailResponse,
    MonitoringSitePostBody,
    MonitoringSitePatchBody,
    TagPostBody,
    TagDeleteBody,
    FileAttachmentPostBody,
    FileAttachmentDeleteBody,
)
from interfaces.api.schemas.sta.monitoring_site import (
    MonitoringSiteFields,
    MonitoringSiteOrderByFields,
)
from processing.orchestration.attention import attention_filter, latest_run_status_subquery
from processing.products.models import DataProductTask
from processing.monitoring.models import MonitoringTask

User = get_user_model()


class MonitoringSiteService(ServiceUtils):
    MARKER_PUBLIC_FILTER = {
        "workspace__is_private": False,
        "is_private": False,
    }

    def get_monitoring_site_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        expand_related: Optional[bool] = None,
    ):
        queryset = MonitoringSite.objects.filter(pk=uid)
        if expand_related:
            queryset = self.select_expanded_fields(queryset)
        else:
            queryset = queryset.prefetch_related("monitoring_site_file_attachments")
        queryset = principal.annotate_permissions(queryset)

        try:
            monitoring_site = queryset.get()
        except MonitoringSite.DoesNotExist:
            raise HttpError(404, "MonitoringSite does not exist")

        if not principal.can_view(monitoring_site):
            raise HttpError(404, "MonitoringSite does not exist")

        if action != "view" and not getattr(principal, f"can_{action}")(monitoring_site):
            raise HttpError(403, f"You do not have permission to {action} this MonitoringSite")

        return monitoring_site

    @staticmethod
    def select_expanded_fields(queryset: QuerySet) -> QuerySet:
        return (
            queryset.select_related("workspace")
            .prefetch_related("monitoring_site_file_attachments")
        )

    @staticmethod
    def apply_bbox_filter(queryset, bbox: Optional[list[str]]):
        if not bbox:
            return queryset

        bbox_filter = Q()

        for bbox_str in bbox:
            try:
                parts = [float(x) for x in bbox_str.split(",")]
            except ValueError:
                raise ValueError("Bounding box must contain only numeric values")

            if len(parts) != 4:
                raise ValueError(
                    "Bounding box must have exactly 4 comma-separated values: min_lon,min_lat,max_lon,max_lat"
                )

            min_lon, min_lat, max_lon, max_lat = parts

            if min_lon > max_lon or min_lat > max_lat:
                raise ValueError(
                    "Invalid bounding box coordinates: min must be less than or equal to max"
                )

            bbox_filter |= Q(
                longitude__gte=min_lon,
                longitude__lte=max_lon,
                latitude__gte=min_lat,
                latitude__lte=max_lat,
            )

        return queryset.filter(bbox_filter)

    @staticmethod
    def apply_tag_filter(queryset, tags: list[str]):
        if not tags:
            return queryset

        for tag in tags:
            if ":" not in tag:
                raise ValueError(f"Invalid tag format: '{tag}'. Must be 'key:value'.")

            key, value = tag.split(":", 1)
            queryset = queryset.filter(tags__contains={key: value})

        return queryset

    @staticmethod
    def parse_bbox_filters(bbox: Optional[list[str]]) -> list[tuple[float, float, float, float]]:
        parsed_bbox_filters: list[tuple[float, float, float, float]] = []

        if not bbox:
            return parsed_bbox_filters

        for bbox_str in bbox:
            try:
                parts = [float(x) for x in bbox_str.split(",")]
            except ValueError:
                raise ValueError("Bounding box must contain only numeric values")

            if len(parts) != 4:
                raise ValueError(
                    "Bounding box must have exactly 4 comma-separated values: min_lon,min_lat,max_lon,max_lat"
                )

            min_lon, min_lat, max_lon, max_lat = parts

            if min_lon > max_lon or min_lat > max_lat:
                raise ValueError(
                    "Invalid bounding box coordinates: min must be less than or equal to max"
                )

            parsed_bbox_filters.append((min_lon, min_lat, max_lon, max_lat))

        return parsed_bbox_filters

    @classmethod
    def apply_marker_bbox_filter(
        cls,
        queryset: QuerySet,
        bbox: Optional[list[str]],
    ) -> QuerySet:
        parsed_bbox_filters = cls.parse_bbox_filters(bbox)

        if not parsed_bbox_filters:
            return queryset

        bbox_filter = Q()
        for min_lon, min_lat, max_lon, max_lat in parsed_bbox_filters:
            bbox_filter |= Q(
                longitude__gte=min_lon,
                longitude__lte=max_lon,
                latitude__gte=min_lat,
                latitude__lte=max_lat,
            )

        return queryset.filter(bbox_filter)

    @staticmethod
    def apply_marker_filters(queryset: QuerySet, filtering: Optional[dict] = None) -> QuerySet:
        filtering = filtering or {}

        if "workspace_id" in filtering:
            queryset = ServiceUtils.apply_filters(
                queryset, "workspace_id", filtering["workspace_id"]
            )

        if "type" in filtering:
            queryset = ServiceUtils.apply_filters(
                queryset, "type", filtering["type"]
            )

        return queryset

    @staticmethod
    def serialize_marker_rows(marker_rows) -> list[dict]:
        return [
            {
                "id": str(marker["id"]),
                "workspace_id": str(marker["workspace_id"]),
                "name": marker["name"],
                "type": marker["type"],
                "is_private": marker["is_private"],
                "latitude": marker["latitude_value"],
                "longitude": marker["longitude_value"],
            }
            for marker in marker_rows
        ]

    @staticmethod
    def get_marker_values(queryset: QuerySet):
        return queryset.annotate(
            latitude_value=Cast("latitude", FloatField()),
            longitude_value=Cast("longitude", FloatField()),
        ).values(
            "id",
            "workspace_id",
            "name",
            "type",
            "is_private",
            "latitude_value",
            "longitude_value",
        )

    @classmethod
    def get_site_summary_values(cls, queryset: QuerySet):
        return queryset.annotate(
            latitude_value=Cast("latitude", FloatField()),
            longitude_value=Cast("longitude", FloatField()),
        ).values(
            "id",
            "workspace_id",
            "name",
            "code",
            "type",
            "is_private",
            "latitude_value",
            "longitude_value",
            "tags",
        )

    @staticmethod
    def serialize_site_summary_rows(site_rows) -> list[dict]:
        return [
            {
                "id": str(site["id"]),
                "workspace_id": str(site["workspace_id"]),
                "name": site["name"],
                "code": site["code"],
                "type": site["type"],
                "is_private": site["is_private"],
                "latitude": site["latitude_value"],
                "longitude": site["longitude_value"],
                "tags": [
                    {"key": key, "value": value}
                    for key, value in (site["tags"] or {}).items()
                ],
            }
            for site in site_rows
        ]

    @classmethod
    def filter_cached_markers(
        cls, markers: list[dict], filtering: Optional[dict] = None
    ) -> list[dict]:
        filtering = filtering or {}
        filtered_markers = markers

        if filtering.get("workspace_id"):
            workspace_ids = {str(workspace_id) for workspace_id in filtering["workspace_id"]}
            filtered_markers = [
                marker
                for marker in filtered_markers
                if marker["workspace_id"] in workspace_ids
            ]

        if filtering.get("type"):
            site_types = set(filtering["type"])
            filtered_markers = [
                marker
                for marker in filtered_markers
                if marker["type"] in site_types
            ]

        parsed_bbox_filters = cls.parse_bbox_filters(filtering.get("bbox"))
        if parsed_bbox_filters:
            filtered_markers = [
                marker
                for marker in filtered_markers
                if any(
                    min_lon <= marker["longitude"] <= max_lon
                    and min_lat <= marker["latitude"] <= max_lat
                    for min_lon, min_lat, max_lon, max_lat in parsed_bbox_filters
                )
            ]

        return filtered_markers

    def get_public_markers(self, filtering: Optional[dict] = None) -> list[dict]:
        public_markers = get_public_monitoring_site_markers_cache()

        if public_markers is None:
            public_marker_queryset = self.get_marker_values(
                MonitoringSite.objects.filter(**self.MARKER_PUBLIC_FILTER).order_by("id")
            )
            public_markers = self.serialize_marker_rows(public_marker_queryset)
            set_public_monitoring_site_markers_cache(public_markers)

        return self.filter_cached_markers(public_markers, filtering=filtering)

    def get_private_markers(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        filtering: Optional[dict] = None,
    ) -> list[dict]:
        if not principal.is_authenticated:
            return []

        private_marker_queryset = principal.filter_by_permission(
            MonitoringSite.objects, "can_view"
        ).exclude(**self.MARKER_PUBLIC_FILTER)
        private_marker_queryset = self.apply_marker_filters(
            private_marker_queryset,
            filtering=filtering,
        )
        private_marker_queryset = self.apply_marker_bbox_filter(
            private_marker_queryset,
            filtering.get("bbox") if filtering else None,
        )

        return self.serialize_marker_rows(
            self.get_marker_values(private_marker_queryset.order_by("id").distinct())
        )

    def list_markers(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        filtering: Optional[dict] = None,
    ):
        public_markers = self.get_public_markers(filtering=filtering)
        private_markers = self.get_private_markers(principal=principal, filtering=filtering)
        markers = public_markers + private_markers
        markers.sort(key=lambda marker: marker["id"])
        return markers

    def list_site_summaries(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        filtering: Optional[dict] = None,
    ) -> list[dict]:
        site_queryset = principal.filter_by_permission(MonitoringSite.objects, "can_view")
        site_queryset = self.apply_marker_filters(site_queryset, filtering=filtering)
        site_rows = list(
            self.get_site_summary_values(
                site_queryset.order_by("id").distinct()
            )
        )
        return self.serialize_site_summary_rows(site_rows)

    @staticmethod
    def list_task_summaries(
        principal: User | ServiceAccount | AnonymousPrincipal,
        workspace_id: Optional[list] = None,
        type: Optional[list] = None,
    ) -> QuerySet:

        now = timezone.now()

        def task_count(task_model, attention_only=False):
            """Correlated per-monitoring_site count subquery.

            Using a subquery (rather than joining the relation into the outer
            query and using Count(distinct=True)) avoids a cartesian product
            between the data_product_tasks and monitoring_tasks relations, which
            would otherwise make this query explode on monitoring_sites with many tasks.
            """
            tasks = task_model.objects.filter(monitoring_site_id=OuterRef("pk"))
            if attention_only:
                tasks = (
                    tasks
                    .annotate(latest_run_status=latest_run_status_subquery())
                    .filter(attention_filter(now))
                )
            return Coalesce(
                Subquery(
                    tasks
                    .values("monitoring_site_id")
                    .annotate(count=Count("pk"))
                    .values("count"),
                    output_field=IntegerField(),
                ),
                0,
            )

        queryset = principal.filter_by_permission(MonitoringSite.objects, "can_view")

        if workspace_id:
            queryset = queryset.filter(workspace_id__in=workspace_id)
        if type:
            queryset = queryset.filter(type__in=type)

        return queryset.annotate(
            product_task_count=task_count(DataProductTask),
            product_task_attention_count=task_count(DataProductTask, attention_only=True),
            monitoring_task_count=task_count(MonitoringTask),
            monitoring_task_attention_count=task_count(MonitoringTask, attention_only=True),
        ).order_by("name")

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_by: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        expand_related: Optional[bool] = None,
    ):
        queryset = MonitoringSite.objects

        for field in [
            "workspace_id",
            "admin_area_1",
            "admin_area_2",
            "country",
            "type",
            "is_private",
        ]:
            if field in filtering:
                if field == "is_private":
                    queryset = self.apply_filters(
                        queryset, f"is_private", filtering[field]
                    )
                    queryset = self.apply_filters(
                        queryset, f"workspace__is_private", filtering[field]
                    )
                else:
                    queryset = self.apply_filters(queryset, field, filtering[field])

        queryset = self.apply_bbox_filter(queryset, filtering.get("bbox"))
        queryset = self.apply_tag_filter(queryset, filtering.get("tag"))

        if order_by:
            queryset = self.apply_ordering(
                queryset,
                order_by,
                list(get_args(MonitoringSiteOrderByFields)),
                {
                    "elevationDatum": "elevation_datum",
                    "adminArea1": "admin_area_1",
                    "adminArea2": "admin_area_2",
                },
            )
        else:
            queryset = queryset.order_by("id")

        if expand_related:
            queryset = self.select_expanded_fields(queryset)
        else:
            queryset = queryset.prefetch_related("monitoring_site_file_attachments")

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()

        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return [
            (
                MonitoringSiteDetailResponse.model_validate(monitoring_site)
                if expand_related
                else MonitoringSiteSummaryResponse.model_validate(monitoring_site)
            )
            for monitoring_site in queryset.all()
        ]

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        expand_related: Optional[bool] = None,
    ):
        monitoring_site = self.get_monitoring_site_for_action(
            principal=principal, uid=uid, action="view", expand_related=expand_related
        )

        return (
            MonitoringSiteDetailResponse.model_validate(monitoring_site)
            if expand_related
            else MonitoringSiteSummaryResponse.model_validate(monitoring_site)
        )

    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: MonitoringSitePostBody,
        expand_related: Optional[bool] = None,
    ):
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=data.workspace_id
        )

        if not principal.can_create("MonitoringSite", workspace=workspace):
            raise HttpError(403, "You do not have permission to create this MonitoringSite")

        tag_keys = [tag.key for tag in data.tags]
        if len(tag_keys) != len(set(tag_keys)):
            raise HttpError(400, "Duplicate tag keys are not allowed")
        tags = {tag.key: tag.value for tag in data.tags}

        try:
            monitoring_site = MonitoringSite.objects.create(
                pk=data.id,
                workspace=workspace,
                tags=tags,
                **data.dict(include=set(MonitoringSiteFields.model_fields.keys()) - {"tags"}),
            )
        except IntegrityError:
            raise HttpError(409, "The operation could not be completed due to a resource conflict.")

        return self.get(
            principal=principal, uid=monitoring_site.id, expand_related=expand_related
        )

    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        data: MonitoringSitePatchBody,
        expand_related: Optional[bool] = None,
    ):
        monitoring_site = self.get_monitoring_site_for_action(principal=principal, uid=uid, action="edit")
        monitoring_site_data = data.dict(
            include=set(MonitoringSiteFields.model_fields.keys()), exclude_unset=True
        )

        for field, value in monitoring_site_data.items():
            setattr(monitoring_site, field, value)

        monitoring_site.save()

        return self.get(
            principal=principal, uid=monitoring_site.id, expand_related=expand_related
        )

    def delete(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID):
        monitoring_site = self.get_monitoring_site_for_action(
            principal=principal, uid=uid, action="delete", expand_related=True
        )
        monitoring_site.delete()

        return "MonitoringSite deleted"

    def get_tags(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID):
        monitoring_site = self.get_monitoring_site_for_action(principal=principal, uid=uid, action="view")

        return [
            {"key": key, "value": value}
            for key, value in (monitoring_site.tags or {}).items()
        ]

    @staticmethod
    def get_tag_keys(
        principal: User | ServiceAccount | AnonymousPrincipal,
        workspace_id: Optional[uuid.UUID],
        monitoring_site_id: Optional[uuid.UUID],
    ):
        queryset = principal.filter_by_permission(MonitoringSite.objects, "can_view")

        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)

        if monitoring_site_id:
            queryset = queryset.filter(id=monitoring_site_id)

        tag_keys: dict[str, set[str]] = defaultdict(set)
        for tags in queryset.values_list("tags", flat=True):
            for key, value in (tags or {}).items():
                tag_keys[key].add(value)

        return {key: sorted(values) for key, values in tag_keys.items()}

    @transaction.atomic
    def add_tag(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID, data: TagPostBody):
        monitoring_site = self.get_monitoring_site_for_action(principal=principal, uid=uid, action="edit")
        monitoring_site = MonitoringSite.objects.select_for_update().get(pk=monitoring_site.pk)

        if data.key in (monitoring_site.tags or {}):
            raise HttpError(400, "Tag already exists")

        monitoring_site.tags = {**(monitoring_site.tags or {}), data.key: data.value}
        monitoring_site.save(update_fields=["tags"])

        return {"key": data.key, "value": data.value}

    @transaction.atomic
    def update_tag(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID, data: TagPostBody):
        monitoring_site = self.get_monitoring_site_for_action(principal=principal, uid=uid, action="edit")
        monitoring_site = MonitoringSite.objects.select_for_update().get(pk=monitoring_site.pk)

        if data.key not in (monitoring_site.tags or {}):
            raise HttpError(404, "Tag does not exist")

        monitoring_site.tags = {**monitoring_site.tags, data.key: data.value}
        monitoring_site.save(update_fields=["tags"])

        return {"key": data.key, "value": data.value}

    @transaction.atomic
    def remove_tag(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID, data: TagDeleteBody):
        monitoring_site = self.get_monitoring_site_for_action(principal=principal, uid=uid, action="edit")
        monitoring_site = MonitoringSite.objects.select_for_update().get(pk=monitoring_site.pk)

        tags = dict(monitoring_site.tags or {})
        if data.key not in tags or (data.value is not None and tags[data.key] != data.value):
            raise HttpError(404, "Tag does not exist")

        del tags[data.key]
        monitoring_site.tags = tags
        monitoring_site.save(update_fields=["tags"])

        return "1 tag(s) deleted"

    def get_file_attachments(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        filtering: Optional[dict] = None,
    ):
        monitoring_site = self.get_monitoring_site_for_action(
            principal=principal, uid=uid, action="view"
        )

        queryset = monitoring_site.monitoring_site_file_attachments

        if filtering.get("file_attachment_type"):
            queryset = self.apply_filters(queryset, "file_attachment_type", filtering["file_attachment_type"])

        return queryset.all()

    def add_file_attachment(
        self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID, file, data: FileAttachmentPostBody
    ):
        monitoring_site = self.get_monitoring_site_for_action(
            principal=principal, uid=uid, action="edit"
        )

        if MonitoringSiteFileAttachment.objects.filter(
            monitoring_site=monitoring_site, name=file.name
        ).exists():
            raise HttpError(400, "File attachment already exists")

        return MonitoringSiteFileAttachment.objects.create(
            monitoring_site=monitoring_site,
            name=file.name,
            description=data.description,
            file_attachment=file,
            file_attachment_type=data.file_attachment_type,
        )

    def replace_file_attachment(
        self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID, file, data: FileAttachmentPostBody
    ):
        self.remove_file_attachment(
            principal=principal, uid=uid, data=FileAttachmentDeleteBody(name=file.name)
        )

        return self.add_file_attachment(
            principal=principal, uid=uid, file=file, data=data
        )

    def remove_file_attachment(
        self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID, data: FileAttachmentDeleteBody
    ):
        monitoring_site = self.get_monitoring_site_for_action(principal=principal, uid=uid, action="edit")

        try:
            file_attachment = MonitoringSiteFileAttachment.objects.get(monitoring_site=monitoring_site, name=data.name)
        except MonitoringSiteFileAttachment.DoesNotExist:
            raise HttpError(404, "File attachment does not exist")

        file_attachment.file_attachment.delete()
        file_attachment.delete()

    def list_site_types(
        self,
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_desc: bool = False,
    ):
        queryset = SiteType.objects.order_by(f"{'-' if order_desc else ''}name")
        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return queryset.values_list("name", flat=True)

    def list_file_attachment_types(
        self,
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_desc: bool = False,
    ):
        queryset = FileAttachmentType.objects.order_by(
            f"{'-' if order_desc else ''}name"
        )
        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return queryset.values_list("name", flat=True)
