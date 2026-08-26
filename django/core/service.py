import uuid
from typing import Union, Any, Optional, Type
from ninja.errors import HttpError
from pydantic.alias_generators import to_snake
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db.models import QuerySet, Model, Q
from core.iam.models import Workspace, ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal

User = get_user_model()


class ServiceUtils:
    @staticmethod
    def get_workspace(
        principal: Union[User, ServiceAccount, AnonymousPrincipal],
        workspace_id: uuid.UUID,
        override_view_permissions=False,
    ):
        try:
            workspace = Workspace.objects.get(pk=workspace_id)
        except Workspace.DoesNotExist:
            raise HttpError(404, "Workspace does not exist")

        if not principal.can_view(workspace) and not override_view_permissions:
            raise HttpError(404, "Workspace does not exist")

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
        except HttpError as e:
            if e.status_code == 404:
                raise HttpError(400, str(e))
            else:
                raise e

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
            raise HttpError(400, "Fields cannot be repeated in order_by arguments")

        for field in order_by:
            if field not in allowed_fields:
                raise HttpError(400, f"Response cannot be ordered by field '{field}'")
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
    def apply_pagination(
        queryset: QuerySet,
        response: Optional[HttpResponse] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ):
        page = page or 1
        page_size = page_size if page_size is not None else 100

        if page < 1:
            raise ValueError("Page must be greater >= 1.")
        if page_size < 0:
            raise ValueError("Page size must be >= 0.")
        if page_size > 100000:
            raise ValueError("Page size must be <= 100000.")

        count = queryset.count()
        offset = (page - 1) * page_size

        if response:
            response["X-Total-Count"] = str(count)
            response["X-Page-Size"] = str(page_size)

            if page_size > 0:
                response["X-Page"] = str(page)
                response["X-Total-Pages"] = str((count + page_size - 1) // page_size)

        return queryset[offset : offset + page_size], count

    @staticmethod
    def create_linked_resource(
        linked_resource_model: Type[Model],
        parent_field: str,
        parent: Model,
        file,
        link: Optional[str],
        data: Any,
    ):
        if linked_resource_model.objects.filter(
            **{parent_field: parent}, name=data.name
        ).exists():
            raise HttpError(400, "A linked resource with this name already exists")

        if file and link:
            raise HttpError(400, "Cannot provide both a file and a link")

        if file:
            if not settings.MEDIA_STORAGE_ENABLED:
                raise HttpError(400, "Internal file uploads are disabled for this instance")

            linked_resource = linked_resource_model(
                **{parent_field: parent},
                name=data.name,
                description=data.description,
                type=data.type,
                file=file,
            )
        elif link:
            linked_resource = linked_resource_model(
                **{parent_field: parent},
                name=data.name,
                description=data.description,
                type=data.type,
                url=link,
            )
        else:
            raise HttpError(400, "Either a file or a link is required")

        try:
            linked_resource.full_clean()
        except ValidationError as e:
            raise HttpError(422, "; ".join(e.messages))

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
            raise HttpError(404, "Linked resource does not exist")

        if name:
            if linked_resource_model.objects.filter(
                **{parent_field: parent}, name=name
            ).exclude(id=linked_resource_id).exists():
                raise HttpError(400, "A linked resource with this name already exists")
            linked_resource.name = name
        elif name is not None:
            raise HttpError(400, "Name cannot be blank")

        if description is not None:
            linked_resource.description = description or None

        if type:
            linked_resource.type = type
        elif type is not None:
            raise HttpError(400, "Type cannot be blank")

        if file and link:
            raise HttpError(400, "Cannot provide both a file and a link")

        stored_file = None
        if file:
            if not linked_resource.file:
                raise HttpError(
                    400,
                    "Cannot switch a linked resource from external to hosted — "
                    "delete it and create a new one instead",
                )
            if not settings.MEDIA_STORAGE_ENABLED:
                raise HttpError(400, "Internal file uploads are disabled for this instance")
            stored_file = linked_resource.file
            linked_resource.file = file
        elif link:
            if not linked_resource.url:
                raise HttpError(
                    400,
                    "Cannot switch a linked resource from hosted to external — "
                    "delete it and create a new one instead",
                )
            linked_resource.url = link
        elif link is not None:
            raise HttpError(400, "Link cannot be blank")

        try:
            linked_resource.full_clean()
        except ValidationError as e:
            raise HttpError(422, "; ".join(e.messages))

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
            raise HttpError(404, "Linked resource does not exist")

        if linked_resource.file:
            linked_resource.file.delete(save=False)
        linked_resource.delete()


class VocabularyService(ServiceUtils):
    def list(
        self,
        vocabulary_model: Type[Model],
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
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

        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return queryset.values_list("name", flat=True)
