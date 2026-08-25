import uuid
from collections import defaultdict
from typing import Optional, Literal, get_args
from ninja.errors import HttpError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import IntegrityError
from django.db.models import Count, QuerySet, F, Q, FloatField, Subquery, OuterRef, IntegerField
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
    MonitoringSiteTag,
    MonitoringSiteLinkedResource,
    SiteType,
    LinkedResourceType,
)
from interfaces.api.schemas import (
    TagGetResponse,
    MonitoringSiteSummaryResponse,
    MonitoringSiteDetailResponse,
    MonitoringSitePostBody,
    MonitoringSitePatchBody,
    TagPostBody,
    TagDeleteBody,
    LinkedResourcePostBody,
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
            queryset = queryset.prefetch_related(
                "monitoring_site_tags", "monitoring_site_linked_resources"
            )
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
            .prefetch_related("monitoring_site_tags", "monitoring_site_linked_resources")
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

            queryset = queryset.filter(monitoring_site_tags__key=key, monitoring_site_tags__value=value)

        return queryset.distinct()

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
        )

    @staticmethod
    def get_tags_by_monitoring_site_id(
        principal: User | ServiceAccount | AnonymousPrincipal,
        monitoring_site_ids: list[uuid.UUID],
    ) -> dict[str, list[TagGetResponse]]:
        if not monitoring_site_ids:
            return {}

        tags_by_monitoring_site_id: dict[str, list[TagGetResponse]] = defaultdict(list)
        visible_monitoring_sites = principal.filter_by_permission(MonitoringSite.objects, "can_view")
        tag_rows = (
            MonitoringSiteTag.objects.filter(monitoring_site__in=visible_monitoring_sites, monitoring_site_id__in=monitoring_site_ids)
            .values("monitoring_site_id", "key", "value")
            .order_by("monitoring_site_id", "key", "value")
            .distinct()
        )
        for tag in tag_rows:
            tags_by_monitoring_site_id[str(tag["monitoring_site_id"])].append(
                {
                    "key": tag["key"],
                    "value": tag["value"],
                }
            )
        return tags_by_monitoring_site_id

    @staticmethod
    def serialize_site_summary_rows(
        site_rows,
        tags_by_monitoring_site_id: dict[str, list[TagGetResponse]],
    ) -> list[dict]:
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
                "tags": tags_by_monitoring_site_id.get(str(site["id"]), []),
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
        tags_by_monitoring_site_id = self.get_tags_by_monitoring_site_id(
            principal=principal,
            monitoring_site_ids=[site["id"] for site in site_rows],
        )
        return self.serialize_site_summary_rows(site_rows, tags_by_monitoring_site_id)

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
            queryset = queryset.prefetch_related(
                "monitoring_site_tags", "monitoring_site_linked_resources"
            )

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

        try:
            monitoring_site = MonitoringSite.objects.create(
                pk=data.id,
                workspace=workspace,
                **data.dict(include=set(MonitoringSiteFields.model_fields.keys())),
            )
        except IntegrityError:
            raise HttpError(409, "The operation could not be completed due to a resource conflict.")

        if data.tags:
            keys = [tag.key for tag in data.tags]
            if len(keys) != len(set(keys)):
                raise HttpError(400, "Duplicate tag keys are not allowed")
            MonitoringSiteTag.objects.bulk_create([
                MonitoringSiteTag(monitoring_site=monitoring_site, key=tag.key, value=tag.value)
                for tag in data.tags
            ])

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

        return monitoring_site.monitoring_site_tags.all()

    @staticmethod
    def get_tag_keys(
        principal: User | ServiceAccount | AnonymousPrincipal,
        workspace_id: Optional[uuid.UUID],
        monitoring_site_id: Optional[uuid.UUID],
    ):
        queryset = MonitoringSiteTag.objects.filter(
            monitoring_site__in=principal.filter_by_permission(MonitoringSite.objects, "can_view")
        )

        if workspace_id:
            queryset = queryset.filter(monitoring_site__workspace_id=workspace_id)

        if monitoring_site_id:
            queryset = queryset.filter(monitoring_site_id=monitoring_site_id)

        tags = queryset.values("key").annotate(values=ArrayAgg(F("value"), distinct=True))

        return {entry["key"]: entry["values"] for entry in tags}

    def add_tag(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID, data: TagPostBody):
        monitoring_site = self.get_monitoring_site_for_action(principal=principal, uid=uid, action="edit")

        if MonitoringSiteTag.objects.filter(monitoring_site=monitoring_site, key=data.key).exists():
            raise HttpError(400, "Tag already exists")

        return MonitoringSiteTag.objects.create(monitoring_site=monitoring_site, key=data.key, value=data.value)

    def update_tag(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID, data: TagPostBody):
        monitoring_site = self.get_monitoring_site_for_action(principal=principal, uid=uid, action="edit")

        try:
            tag = MonitoringSiteTag.objects.get(monitoring_site=monitoring_site, key=data.key)
        except MonitoringSiteTag.DoesNotExist:
            raise HttpError(404, "Tag does not exist")

        tag.value = data.value
        tag.save()

        return tag

    def remove_tag(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID, data: TagDeleteBody):
        monitoring_site = self.get_monitoring_site_for_action(principal=principal, uid=uid, action="edit")

        queryset = MonitoringSiteTag.objects.filter(monitoring_site=monitoring_site, key=data.key)

        if data.value is not None:
            queryset = queryset.filter(value=data.value)

        deleted_count, _ = queryset.delete()

        if deleted_count == 0:
            raise HttpError(404, "Tag does not exist")

        return f"{deleted_count} tag(s) deleted"

    def get_linked_resources(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        filtering: Optional[dict] = None,
    ):
        monitoring_site = self.get_monitoring_site_for_action(
            principal=principal, uid=uid, action="view"
        )

        queryset = monitoring_site.monitoring_site_linked_resources

        if filtering.get("type"):
            queryset = self.apply_filters(queryset, "type", filtering["type"])

        return queryset.all()

    def add_linked_resource(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        file,
        link: Optional[str],
        data: LinkedResourcePostBody,
    ):
        monitoring_site = self.get_monitoring_site_for_action(
            principal=principal, uid=uid, action="edit"
        )

        return self.create_linked_resource(
            linked_resource_model=MonitoringSiteLinkedResource,
            parent_field="monitoring_site",
            parent=monitoring_site,
            file=file,
            link=link,
            data=data,
        )

    def update_linked_resource(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        linked_resource_id: uuid.UUID,
        name: Optional[str],
        description: Optional[str],
        type: Optional[str],
        file,
        link: Optional[str],
    ):
        monitoring_site = self.get_monitoring_site_for_action(principal=principal, uid=uid, action="edit")

        return self.update_linked_resource_fields(
            linked_resource_model=MonitoringSiteLinkedResource,
            parent_field="monitoring_site",
            parent=monitoring_site,
            linked_resource_id=linked_resource_id,
            name=name,
            description=description,
            type=type,
            file=file,
            link=link,
        )

    def remove_linked_resource(
        self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID, linked_resource_id: uuid.UUID
    ):
        monitoring_site = self.get_monitoring_site_for_action(principal=principal, uid=uid, action="edit")

        self.delete_linked_resource(
            linked_resource_model=MonitoringSiteLinkedResource,
            parent_field="monitoring_site",
            parent=monitoring_site,
            linked_resource_id=linked_resource_id,
        )

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

    def list_linked_resource_types(
        self,
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_desc: bool = False,
    ):
        queryset = LinkedResourceType.objects.order_by(
            f"{'-' if order_desc else ''}name"
        )
        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return queryset.values_list("name", flat=True)
