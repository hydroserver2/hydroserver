import uuid
from typing import Union, Any, Optional, Type
from ninja.errors import HttpError
from pydantic.alias_generators import to_snake
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db.models import QuerySet, Model, Q
from domains.iam.models import Workspace, APIKey

User = get_user_model()


class ServiceUtils:
    @staticmethod
    def get_workspace(
        principal: Union[User, APIKey],
        workspace_id: uuid.UUID,
        override_view_permissions=False,
    ):
        try:
            workspace = Workspace.objects.get(pk=workspace_id)
        except Workspace.DoesNotExist:
            raise HttpError(404, "Workspace does not exist")

        workspace_permissions = workspace.get_principal_permissions(principal=principal)

        if (
            "view" not in workspace_permissions
            and workspace.is_private is True
            and not override_view_permissions
        ):
            raise HttpError(404, "Workspace does not exist")

        return workspace, workspace_permissions

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
            order_by_fields.append(field_aliases.get(field, to_snake(field)))

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
