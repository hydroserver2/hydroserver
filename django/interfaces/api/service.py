import json
import uuid
from typing import Union, Any, Optional, Type
from pydantic.alias_generators import to_snake
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import EmptyResultSet
from django.db import connection
from django.db.models import QuerySet, Model, Q
from core.iam.models import Workspace, ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from interfaces.api.http.errors import BadRequestError, NotFoundError
from interfaces.api.schemas.base import PaginationMeta

User = get_user_model()


class APIService:
    @staticmethod
    def get_workspace(
        principal: Union[User, ServiceAccount, AnonymousPrincipal],
        workspace_id: uuid.UUID,
        override_view_permissions=False,
    ):
        try:
            workspace = Workspace.objects.get(pk=workspace_id)
        except Workspace.DoesNotExist:
            raise NotFoundError("Workspace does not exist")

        if not principal.can_view(workspace) and not override_view_permissions:
            raise NotFoundError("Workspace does not exist")

        permissions = [
            action
            for action in ("view", "edit", "delete")
            if getattr(principal, f"can_{action}")(workspace)
        ]

        return workspace, permissions

    @staticmethod
    def handle_http_404_error(operation, *args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except NotFoundError as e:
            raise BadRequestError(e.message)

    @staticmethod
    def apply_filters(queryset: QuerySet, field_name: str, values: Optional[Any]):
        if values is None:
            return queryset

        if isinstance(values, (list, tuple, set)):
            values = list(values)
            if len(values) == 1:
                if values[0] is None:
                    return queryset.filter(**{f"{field_name}__isnull": True})
                else:
                    return queryset.filter(**{field_name: values[0]})
            elif len(values) > 1:
                if None in values:
                    return queryset.filter(
                        Q(
                            **{
                                f"{field_name}__in": [
                                    value for value in values if value is not None
                                ]
                            }
                        )
                        | Q(**{f"{field_name}__isnull": True})
                    )
                else:
                    return queryset.filter(**{f"{field_name}__in": values})
            else:
                return queryset
        else:
            return queryset.filter(**{field_name: values})

    @staticmethod
    def apply_ordering(
        queryset: QuerySet,
        order_by: list[str],
        allowed_fields: list[str],
        field_aliases: Optional[dict[str, str]] = None,
    ):
        order_by_fields = []
        field_aliases = field_aliases or {}

        stripped_fields = [field.lstrip("-") for field in order_by]
        if len(stripped_fields) != len(set(stripped_fields)):
            raise BadRequestError("Fields cannot be repeated in order_by arguments")

        for field in order_by:
            if field not in allowed_fields:
                raise BadRequestError(f"Response cannot be ordered by field '{field}'")
            descending = field.startswith("-")
            stripped_field = field.lstrip("-")
            resolved_field = field_aliases.get(stripped_field, to_snake(stripped_field))
            order_by_fields.append(f"-{resolved_field}" if descending else resolved_field)

        # Requested fields (e.g. "name") are rarely unique, so rows that tie on
        # them have no guaranteed relative order. Since results are fetched a
        # page at a time via separate queries (see paginatedFetch on the
        # client), an unstable tie order lets rows shift between pages and
        # silently drop out of every page. Appending the primary key as a
        # final tiebreaker makes the ordering - and therefore pagination -
        # deterministic.
        if "id" not in stripped_fields:
            order_by_fields.append("id")

        return queryset.order_by(*order_by_fields)

    @staticmethod
    def build_pagination_meta(
        count: int,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> PaginationMeta:
        offset = offset or 0
        limit = limit if limit is not None else 100

        return PaginationMeta(
            limit=limit,
            offset=offset,
            total_count=count,
        )

    @classmethod
    def apply_pagination(
        cls,
        queryset: QuerySet,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        count: Optional[int] = None,
    ):
        offset = offset or 0
        limit = limit if limit is not None else 100

        if offset < 0:
            raise BadRequestError("Offset must be >= 0.")
        if limit < 0:
            raise BadRequestError("Limit must be >= 0.")
        if limit > 100000:
            raise BadRequestError("Limit must be <= 100000.")

        if count is None:
            count = queryset.count()

        meta = cls.build_pagination_meta(count, offset, limit)

        return queryset[offset : offset + limit], meta

    @staticmethod
    def estimate_count(queryset: QuerySet) -> int:
        """Postgres's EXPLAIN row-estimate for the queryset's filter, without executing it."""

        try:
            sql, params = queryset.order_by().values("pk").query.sql_with_params()
        except EmptyResultSet:
            return 0

        with connection.cursor() as cursor:
            cursor.execute(f"EXPLAIN (FORMAT JSON) {sql}", params)
            raw = cursor.fetchone()[0]
        plan = raw if isinstance(raw, list) else json.loads(raw)

        return plan[0]["Plan"]["Plan Rows"]

    @classmethod
    def resolve_count(cls, queryset: QuerySet, threshold: int = 10_000) -> int:
        """
        Exact count for queries estimated at or under `threshold` rows; the estimate
        itself otherwise, to avoid an expensive COUNT(*) over a large filtered result.
        """

        estimated = cls.estimate_count(queryset)
        if estimated <= threshold:
            return queryset.count()

        return estimated

    @staticmethod
    def create_linked_resource(
        linked_resource_model: Type[Model],
        parent_field: str,
        parent: Model,
        file,
        link: Optional[str],
        data: Any,
    ):
        if file and not settings.MEDIA_STORAGE_ENABLED:
            raise BadRequestError("Internal file uploads are disabled for this instance")

        linked_resource = linked_resource_model(
            **{parent_field: parent},
            name=data.name,
            description=data.description,
            type=data.type,
            file=file or "",
            url=link or "",
        )
        linked_resource.full_clean()
        linked_resource.save()

        return linked_resource

    @staticmethod
    def update_linked_resource_fields(
        linked_resource_model: Type[Model],
        parent_field: str,
        parent: Model,
        linked_resource_id: uuid.UUID,
        name: Optional[str],
        description: Optional[str],
        type: Optional[str],
        file,
        link: Optional[str],
    ):
        try:
            linked_resource = linked_resource_model.objects.get(
                **{parent_field: parent}, id=linked_resource_id
            )
        except linked_resource_model.DoesNotExist:
            raise NotFoundError("Linked resource does not exist")

        if name is not None:
            linked_resource.name = name
        if description is not None:
            linked_resource.description = description or None
        if type is not None:
            linked_resource.type = type

        stored_file = None
        if file:
            if not settings.MEDIA_STORAGE_ENABLED:
                raise BadRequestError("Internal file uploads are disabled for this instance")
            stored_file = linked_resource.file
            linked_resource.file = file
        if link is not None:
            linked_resource.url = link

        linked_resource.full_clean()
        linked_resource.save()

        if stored_file:
            stored_file.delete(save=False)

        return linked_resource

    @staticmethod
    def delete_linked_resource(
        linked_resource_model: Type[Model],
        parent_field: str,
        parent: Model,
        linked_resource_id: uuid.UUID,
    ):
        try:
            linked_resource = linked_resource_model.objects.get(
                **{parent_field: parent}, id=linked_resource_id
            )
        except linked_resource_model.DoesNotExist:
            raise NotFoundError("Linked resource does not exist")

        if linked_resource.file:
            linked_resource.file.delete(save=False)
        linked_resource.delete()


class VocabularyAPIService(APIService):
    def list(
        self,
        vocabulary_model: Type[Model],
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        order_desc: bool = False,
    ):
        queryset = vocabulary_model.objects

        queryset = self.apply_ordering(
            queryset,
            ["-name"] if order_desc else ["name"],
            [
                "name",
            ],
        )

        queryset, meta = self.apply_pagination(queryset, offset, limit)

        return {
            "data": list(queryset.values_list("name", flat=True)),
            "meta": meta,
        }


build_pagination_meta = APIService.build_pagination_meta
