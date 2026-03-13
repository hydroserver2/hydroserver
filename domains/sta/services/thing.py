import uuid
from collections import defaultdict
from typing import Optional, Literal, List, get_args
from ninja.errors import HttpError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import IntegrityError
from django.db.models import QuerySet, F, Q, FloatField
from django.db.models.functions import Cast
from domains.iam.models import APIKey
from domains.sta.cache import (
    get_public_thing_markers_cache,
    set_public_thing_markers_cache,
)
from domains.sta.models import (
    Thing,
    Location,
    ThingTag,
    ThingFileAttachment,
    SamplingFeatureType,
    SiteType,
    FileAttachmentType,
)
from interfaces.api.schemas import (
    TagGetResponse,
    ThingSummaryResponse,
    ThingDetailResponse,
    ThingPostBody,
    ThingPatchBody,
    TagPostBody,
    TagDeleteBody,
    FileAttachmentDeleteBody,
    FileAttachmentPatchBody,
)
from interfaces.api.schemas.thing import ThingFields, LocationFields, ThingOrderByFields
from interfaces.api.service import ServiceUtils

User = get_user_model()


class ThingService(ServiceUtils):
    MARKER_PUBLIC_FILTER = {
        "thing__workspace__is_private": False,
        "thing__is_private": False,
    }

    def get_thing_for_action(
        self,
        principal: User | APIKey,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        expand_related: Optional[bool] = None,
    ):
        try:
            thing = Thing.objects
            if expand_related:
                thing = self.select_expanded_fields(thing)
            else:
                thing = thing.prefetch_related(
                    "thing_tags", "thing_file_attachments"
                ).with_location()
            thing = thing.get(pk=uid)
        except Thing.DoesNotExist:
            raise HttpError(404, "Thing does not exist")

        thing_permissions = thing.get_principal_permissions(principal=principal)

        if "view" not in thing_permissions:
            raise HttpError(404, "Thing does not exist")

        if action not in thing_permissions:
            raise HttpError(403, f"You do not have permission to {action} this Thing")

        return thing

    @staticmethod
    def select_expanded_fields(queryset: QuerySet) -> QuerySet:
        return (
            queryset.select_related("workspace")
            .prefetch_related("thing_tags", "thing_file_attachments")
            .with_location()
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
                locations__longitude__gte=min_lon,
                locations__longitude__lte=max_lon,
                locations__latitude__gte=min_lat,
                locations__latitude__lte=max_lat,
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

            queryset = queryset.filter(thing_tags__key=key, thing_tags__value=value)

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
                queryset, "thing__workspace_id", filtering["workspace_id"]
            )

        if "site_type" in filtering:
            queryset = ServiceUtils.apply_filters(
                queryset, "thing__site_type", filtering["site_type"]
            )

        return queryset

    @staticmethod
    def serialize_marker_rows(marker_rows) -> list[dict]:
        return [
            {
                "id": str(marker["thing_id"]),
                "workspace_id": str(marker["thing__workspace_id"]),
                "name": marker["thing__name"],
                "site_type": marker["thing__site_type"],
                "is_private": marker["thing__is_private"],
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
            "thing_id",
            "thing__workspace_id",
            "thing__name",
            "thing__site_type",
            "thing__is_private",
            "latitude_value",
            "longitude_value",
        )

    @classmethod
    def get_site_summary_values(cls, queryset: QuerySet):
        return queryset.annotate(
            latitude_value=Cast("latitude", FloatField()),
            longitude_value=Cast("longitude", FloatField()),
        ).values(
            "thing_id",
            "thing__workspace_id",
            "thing__name",
            "thing__sampling_feature_code",
            "thing__site_type",
            "thing__is_private",
            "latitude_value",
            "longitude_value",
        )

    @staticmethod
    def get_tags_by_thing_id(
        principal: Optional[User | APIKey],
        thing_ids: list[uuid.UUID],
    ) -> dict[str, list[TagGetResponse]]:
        if not thing_ids:
            return {}

        tags_by_thing_id: dict[str, list[TagGetResponse]] = defaultdict(list)
        tag_rows = (
            ThingTag.objects.visible(principal=principal)
            .filter(thing_id__in=thing_ids)
            .values("thing_id", "key", "value")
            .order_by("thing_id", "key", "value")
            .distinct()
        )
        for tag in tag_rows:
            tags_by_thing_id[str(tag["thing_id"])].append(
                {
                    "key": tag["key"],
                    "value": tag["value"],
                }
            )
        return tags_by_thing_id

    @staticmethod
    def serialize_site_summary_rows(
        site_rows,
        tags_by_thing_id: dict[str, list[TagGetResponse]],
    ) -> list[dict]:
        return [
            {
                "id": str(site["thing_id"]),
                "workspace_id": str(site["thing__workspace_id"]),
                "name": site["thing__name"],
                "sampling_feature_code": site["thing__sampling_feature_code"],
                "site_type": site["thing__site_type"],
                "is_private": site["thing__is_private"],
                "latitude": site["latitude_value"],
                "longitude": site["longitude_value"],
                "tags": tags_by_thing_id.get(str(site["thing_id"]), []),
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

        if filtering.get("site_type"):
            site_types = set(filtering["site_type"])
            filtered_markers = [
                marker
                for marker in filtered_markers
                if marker["site_type"] in site_types
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
        public_markers = get_public_thing_markers_cache()

        if public_markers is None:
            public_marker_queryset = self.get_marker_values(
                Location.objects.filter(**self.MARKER_PUBLIC_FILTER).order_by("thing_id")
            )
            public_markers = self.serialize_marker_rows(public_marker_queryset)
            set_public_thing_markers_cache(public_markers)

        return self.filter_cached_markers(public_markers, filtering=filtering)

    def get_private_markers(
        self,
        principal: Optional[User | APIKey],
        filtering: Optional[dict] = None,
    ) -> list[dict]:
        if not principal:
            return []

        private_marker_queryset = Location.objects.visible(principal=principal).exclude(
            **self.MARKER_PUBLIC_FILTER
        )
        private_marker_queryset = self.apply_marker_filters(
            private_marker_queryset,
            filtering=filtering,
        )
        private_marker_queryset = self.apply_marker_bbox_filter(
            private_marker_queryset,
            filtering.get("bbox") if filtering else None,
        )

        return self.serialize_marker_rows(
            self.get_marker_values(private_marker_queryset.order_by("thing_id").distinct())
        )

    def list_markers(
        self,
        principal: Optional[User | APIKey],
        filtering: Optional[dict] = None,
    ):
        public_markers = self.get_public_markers(filtering=filtering)
        private_markers = self.get_private_markers(principal=principal, filtering=filtering)
        markers = public_markers + private_markers
        markers.sort(key=lambda marker: marker["id"])
        return markers

    def list_site_summaries(
        self,
        principal: Optional[User | APIKey],
        filtering: Optional[dict] = None,
    ) -> list[dict]:
        site_queryset = Location.objects.visible(principal=principal)
        site_queryset = self.apply_marker_filters(site_queryset, filtering=filtering)
        site_rows = list(
            self.get_site_summary_values(
                site_queryset.order_by("thing_id").distinct()
            )
        )
        tags_by_thing_id = self.get_tags_by_thing_id(
            principal=principal,
            thing_ids=[site["thing_id"] for site in site_rows],
        )
        return self.serialize_site_summary_rows(site_rows, tags_by_thing_id)

    def list(
        self,
        principal: Optional[User | APIKey],
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_by: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        expand_related: Optional[bool] = None,
    ):
        queryset = Thing.objects

        for field in [
            "workspace_id",
            "locations__admin_area_1",
            "locations__admin_area_2",
            "locations__country",
            "site_type",
            "sampling_feature_type",
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
                list(get_args(ThingOrderByFields)),
                {
                    "latitude": "location__latitude",
                    "longitude": "location__longitude",
                    "elevation_m": "location__elevation_m",
                    "elevationDatum": "location__elevation_datum",
                    "admin_area_1": "location__admin_area_1",
                    "admin_area_2": "location__admin_area_2",
                    "country": "location__country",
                },
            )
        else:
            queryset = queryset.order_by("id")

        if expand_related:
            queryset = self.select_expanded_fields(queryset)
        else:
            queryset = queryset.prefetch_related(
                "thing_tags", "thing_file_attachments"
            ).with_location()

        queryset = queryset.visible(principal=principal).distinct()

        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return [
            (
                ThingDetailResponse.model_validate(thing)
                if expand_related
                else ThingSummaryResponse.model_validate(thing)
            )
            for thing in queryset.all()
        ]

    def get(
        self,
        principal: Optional[User | APIKey],
        uid: uuid.UUID,
        expand_related: Optional[bool] = None,
    ):
        thing = self.get_thing_for_action(
            principal=principal, uid=uid, action="view", expand_related=expand_related
        )

        return (
            ThingDetailResponse.model_validate(thing)
            if expand_related
            else ThingSummaryResponse.model_validate(thing)
        )

    def create(
        self,
        principal: User | APIKey,
        data: ThingPostBody,
        expand_related: Optional[bool] = None,
    ):
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=data.workspace_id
        )

        if not Thing.can_principal_create(principal=principal, workspace=workspace):
            raise HttpError(403, "You do not have permission to create this Thing")

        try:
            thing = Thing.objects.create(
                pk=data.id,
                workspace=workspace,
                **data.dict(include=set(ThingFields.model_fields.keys())),
            )
        except IntegrityError:
            raise HttpError(409, "The operation could not be completed due to a resource conflict.")

        Location.objects.create(
            name=f"Location for {data.name}",
            description="location",
            encoding_type="application/geo+json",
            thing=thing,
            **data.location.dict(include=set(LocationFields.model_fields.keys())),
        )

        return self.get(
            principal=principal, uid=thing.id, expand_related=expand_related
        )

    def update(
        self,
        principal: User | APIKey,
        uid: uuid.UUID,
        data: ThingPatchBody,
        expand_related: Optional[bool] = None,
    ):
        thing = self.get_thing_for_action(principal=principal, uid=uid, action="edit")
        location = thing.location

        thing_data = data.dict(
            include=set(ThingFields.model_fields.keys()), exclude_unset=True
        )
        location_data = (
            data.location.dict(
                include=set(LocationFields.model_fields.keys()), exclude_unset=True
            )
            if data.location
            else {}
        )

        if thing_data.get("name"):
            location_data["name"] = f"Location for {thing_data['name']}"

        for field, value in thing_data.items():
            setattr(thing, field, value)

        thing.save()

        for field, value in location_data.items():
            setattr(location, field, value)

        location.save()

        return self.get(
            principal=principal, uid=thing.id, expand_related=expand_related
        )

    def delete(self, principal: User | APIKey, uid: uuid.UUID):
        thing = self.get_thing_for_action(
            principal=principal, uid=uid, action="delete", expand_related=True
        )
        location = thing.location

        thing.delete()
        location.delete()

        return "Thing deleted"

    def get_tags(self, principal: Optional[User | APIKey], uid: uuid.UUID):
        thing = self.get_thing_for_action(principal=principal, uid=uid, action="view")

        return thing.thing_tags.all()

    @staticmethod
    def get_tag_keys(
        principal: Optional[User | APIKey],
        workspace_id: Optional[uuid.UUID],
        thing_id: Optional[uuid.UUID],
    ):
        queryset = ThingTag.objects

        if workspace_id:
            queryset = queryset.filter(thing__workspace_id=workspace_id)

        if thing_id:
            queryset = queryset.filter(thing_id=thing_id)

        tags = (
            queryset.visible(principal=principal)
            .values("key")
            .annotate(values=ArrayAgg(F("value"), distinct=True))
        )

        return {entry["key"]: entry["values"] for entry in tags}

    def add_tag(self, principal: User | APIKey, uid: uuid.UUID, data: TagPostBody):
        thing = self.get_thing_for_action(principal=principal, uid=uid, action="edit")

        if ThingTag.objects.filter(thing=thing, key=data.key).exists():
            raise HttpError(400, "Tag already exists")

        return ThingTag.objects.create(thing=thing, key=data.key, value=data.value)

    def update_tag(self, principal: User | APIKey, uid: uuid.UUID, data: TagPostBody):
        thing = self.get_thing_for_action(principal=principal, uid=uid, action="edit")

        try:
            tag = ThingTag.objects.get(thing=thing, key=data.key)
        except ThingTag.DoesNotExist:
            raise HttpError(404, "Tag does not exist")

        tag.value = data.value
        tag.save()

        return tag

    def remove_tag(self, principal: User | APIKey, uid: uuid.UUID, data: TagDeleteBody):
        thing = self.get_thing_for_action(principal=principal, uid=uid, action="edit")

        queryset = ThingTag.objects.filter(thing=thing, key=data.key)

        if data.value is not None:
            queryset = queryset.filter(value=data.value)

        deleted_count, _ = queryset.delete()

        if deleted_count == 0:
            raise HttpError(404, "Tag does not exist")

        return f"{deleted_count} tag(s) deleted"

    @staticmethod
    def _normalize_attachment_type(attachment_type: str) -> str:
        normalized = (attachment_type or "").strip()
        if not normalized:
            raise HttpError(400, "File attachment type is required")
        return normalized

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized = (name or "").strip()
        if not normalized:
            raise HttpError(400, "File attachment name is required")
        return normalized

    def get_file_attachments(
        self,
        principal: Optional[User | APIKey],
        uid: uuid.UUID,
        attachment_types: Optional[List[str]] = None,
    ):
        thing = self.get_thing_for_action(principal=principal, uid=uid, action="view")
        queryset = thing.thing_file_attachments.all()

        if attachment_types:
            normalized_types = [
                self._normalize_attachment_type(item) for item in attachment_types if item
            ]
            if normalized_types:
                queryset = queryset.filter(file_attachment_type__in=normalized_types)

        return queryset.order_by("file_attachment_type", "name")

    def get_file_attachment_for_action(
        self,
        principal: Optional[User | APIKey],
        uid: uuid.UUID,
        attachment_id: int,
        action: Literal["view", "edit", "delete"],
    ) -> ThingFileAttachment:
        thing = self.get_thing_for_action(principal=principal, uid=uid, action=action)

        try:
            return ThingFileAttachment.objects.get(pk=attachment_id, thing=thing)
        except ThingFileAttachment.DoesNotExist:
            raise HttpError(404, "File attachment does not exist")

    def add_file_attachment(
        self,
        principal: User | APIKey,
        uid: uuid.UUID,
        file,
        file_attachment_type: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        thing = self.get_thing_for_action(principal=principal, uid=uid, action="edit")
        normalized_name = self._normalize_name(name or file.name)
        normalized_type = self._normalize_attachment_type(file_attachment_type)
        normalized_description = (description or "").strip()

        if ThingFileAttachment.objects.filter(thing=thing, name=normalized_name).exists():
            raise HttpError(400, "File attachment already exists")

        return ThingFileAttachment.objects.create(
            thing=thing,
            name=normalized_name,
            description=normalized_description,
            file_attachment=file,
            file_attachment_type=normalized_type,
        )

    def update_file_attachment(
        self,
        principal: User | APIKey,
        uid: uuid.UUID,
        attachment_id: int,
        data: FileAttachmentPatchBody,
    ) -> ThingFileAttachment:
        file_attachment = self.get_file_attachment_for_action(
            principal=principal, uid=uid, attachment_id=attachment_id, action="edit"
        )
        body = data.dict(exclude_unset=True)

        if "name" in body:
            new_name = self._normalize_name(body["name"])
            if (
                new_name != file_attachment.name
                and ThingFileAttachment.objects.filter(
                    thing_id=file_attachment.thing_id,
                    name=new_name,
                ).exists()
            ):
                raise HttpError(400, "File attachment already exists")
            file_attachment.name = new_name

        if "description" in body:
            file_attachment.description = (body["description"] or "").strip()

        file_attachment.save()
        return file_attachment

    def replace_file_attachment(
        self,
        principal: User | APIKey,
        uid: uuid.UUID,
        attachment_id: int,
        file,
    ) -> ThingFileAttachment:
        file_attachment = self.get_file_attachment_for_action(
            principal=principal, uid=uid, attachment_id=attachment_id, action="edit"
        )

        old_name = file_attachment.file_attachment.name
        file_attachment.file_attachment = file
        file_attachment.save()

        new_name = file_attachment.file_attachment.name
        if old_name and old_name != new_name:
            file_attachment.file_attachment.storage.delete(old_name)

        return file_attachment

    def remove_file_attachment(
        self, principal: User | APIKey, uid: uuid.UUID, data: FileAttachmentDeleteBody
    ):
        thing = self.get_thing_for_action(principal=principal, uid=uid, action="edit")

        try:
            file_attachment = ThingFileAttachment.objects.get(thing=thing, name=data.name)
        except ThingFileAttachment.DoesNotExist:
            raise HttpError(404, "File attachment does not exist")

        file_attachment.file_attachment.delete()
        file_attachment.delete()

        return "File attachment deleted"

    def delete_file_attachment(
        self, principal: User | APIKey, uid: uuid.UUID, attachment_id: int
    ):
        file_attachment = self.get_file_attachment_for_action(
            principal=principal, uid=uid, attachment_id=attachment_id, action="edit"
        )
        file_attachment.file_attachment.delete(save=False)
        file_attachment.delete()

        return "File attachment deleted"

    def get_file_attachment_for_download(
        self,
        principal: Optional[User | APIKey],
        uid: uuid.UUID,
        attachment_id: int,
        token: Optional[str] = None,
    ) -> ThingFileAttachment:
        try:
            file_attachment = ThingFileAttachment.objects.get(
                pk=attachment_id, thing_id=uid
            )
        except ThingFileAttachment.DoesNotExist:
            raise HttpError(404, "File attachment does not exist")

        if token and token == str(file_attachment.download_token):
            return file_attachment

        self.get_thing_for_action(principal=principal, uid=uid, action="view")
        return file_attachment

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

    def list_sampling_feature_types(
        self,
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_desc: bool = False,
    ):
        queryset = SamplingFeatureType.objects.order_by(
            f"{'-' if order_desc else ''}name"
        )
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
