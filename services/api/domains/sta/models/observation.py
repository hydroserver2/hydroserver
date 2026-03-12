import io
import uuid6
import typing
import operator
from typing import Literal, Optional, Union
from django.db import models, connection
from django.db.models import Q, OuterRef, Exists
from domains.iam.models import Workspace, APIKey, Permission, Collaborator
from domains.iam.models.utils import PermissionChecker
from .datastream import Datastream
from .result_qualifier import ResultQualifier

if typing.TYPE_CHECKING:
    from django.contrib.auth import get_user_model
    from domains.iam.models import Workspace

    User = get_user_model()


class ObservationQuerySet(models.QuerySet):
    def visible(self, principal: Optional[Union["User", "APIKey"]]):
        public_filter = Q(
            datastream__thing__workspace__is_private=False,
            datastream__thing__is_private=False,
            datastream__is_private=False,
        )

        if hasattr(principal, "account_type") and principal.account_type == "admin":
            return self

        elif hasattr(principal, "account_type") and principal.account_type != "admin":
            collaborator_subquery = Collaborator.objects.filter(
                workspace=OuterRef("datastream__thing__workspace"),
                user=principal,
                role__permissions__resource_type__in=["*", "Observation"],
                role__permissions__permission_type__in=["*", "view"],
            )

            return self.filter(
                public_filter
                | Q(datastream__thing__workspace__owner=principal)
                | Exists(collaborator_subquery)
            )

        elif hasattr(principal, "workspace"):
            apikey_subquery = APIKey.objects.filter(
                workspace=OuterRef("datastream__thing__workspace"),
                id=principal.id,
                role__permissions__resource_type__in=["*", "Observation"],
                role__permissions__permission_type__in=["*", "view"],
            )

            return self.filter(public_filter | Exists(apikey_subquery))

        else:
            return self.filter(public_filter)

    def removable(self, principal: Optional[Union["User", "APIKey"]]):
        if hasattr(principal, "account_type"):
            if principal.account_type == "admin":
                return self
            else:
                return self.filter(
                    Q(datastream__thing__workspace__owner=principal)
                    | Q(
                        datastream__thing__workspace__collaborators__user=principal,
                        datastream__thing__workspace__collaborators__role__permissions__resource_type__in=[
                            "*",
                            "Observation",
                        ],
                        datastream__thing__workspace__collaborators__role__permissions__permission_type__in=[
                            "*",
                            "delete",
                        ],
                    )
                )
        elif hasattr(principal, "workspace"):
            return self.filter(
                datastream__thing__workspace__apikeys=principal,
                datastream__thing__workspace__apikeys__role__permissions__resource_type__in=[
                    "*",
                    "Observation",
                ],
                datastream__thing__workspace__apikeys__role__permissions__permission_type__in=[
                    "*",
                    "delete",
                ],
            )
        else:
            return self.none()

    def bulk_copy(self, observations, result_qualifiers=None, batch_size=100_000):
        db_table_sql = connection.ops.quote_name(self.model._meta.db_table)  # noqa
        db_fields = [field.column for field in self.model._meta.fields]
        quoted_fields = [connection.ops.quote_name(field) for field in db_fields]
        db_fields_sql = ", ".join(quoted_fields)

        attr_getters = [operator.attrgetter(field) for field in db_fields]

        def escape_pg_copy(value):
            if value is None:
                return r"\N"
            if isinstance(value, str):
                return (
                    value.replace("\\", "\\\\")
                    .replace("\t", "\\t")
                    .replace("\n", "\\n")
                    .replace("\r", "\\r")
                )
            return str(value)

        with connection.cursor() as cursor:
            with cursor.copy(
                f"COPY {db_table_sql} ({db_fields_sql}) FROM STDIN"
            ) as copy:
                buffer = io.StringIO()
                for i in range(0, len(observations), batch_size):
                    batch = observations[i : i + batch_size]
                    lines = []
                    for obs in batch:
                        line = "\t".join(
                            escape_pg_copy(
                                getter(obs) if field != "id" else str(obs.id)
                            )
                            for field, getter in zip(db_fields, attr_getters)
                        )
                        lines.append(line)
                    buffer.write("\n".join(lines) + "\n")
                    buffer.seek(0)
                    copy.write(buffer.read())
                    buffer.truncate(0)
                    buffer.seek(0)

            if result_qualifiers:
                through_model = self.model.result_qualifiers.through
                through_table = connection.ops.quote_name(through_model._meta.db_table)
                through_columns = [
                    through_model._meta.get_field(f).column
                    for f in ["observation", "resultqualifier"]
                ]
                quoted_columns_sql = ", ".join(
                    [connection.ops.quote_name(c) for c in through_columns]
                )

                with cursor.copy(
                    f"COPY {through_table} ({quoted_columns_sql}) FROM STDIN"
                ) as copy:
                    buffer = io.StringIO()
                    for i in range(0, len(result_qualifiers), batch_size):
                        batch = result_qualifiers[i : i + batch_size]
                        lines = [
                            f"{escape_pg_copy(obs_id)}\t{escape_pg_copy(rq_id)}"
                            for obs_id, rq_id in batch
                        ]
                        buffer.write("\n".join(lines) + "\n")
                        buffer.seek(0)
                        copy.write(buffer.read())
                        buffer.truncate(0)
                        buffer.seek(0)

        return observations


class Observation(models.Model, PermissionChecker):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    datastream = models.ForeignKey(Datastream, on_delete=models.DO_NOTHING)
    phenomenon_time = models.DateTimeField()
    result = models.FloatField()
    result_time = models.DateTimeField(null=True, blank=True)
    quality_code = models.CharField(max_length=255, null=True, blank=True)
    result_qualifiers = models.ManyToManyField(
        ResultQualifier, related_name="observations", blank=True
    )

    objects = ObservationQuerySet.as_manager()

    @classmethod
    def can_principal_create(
        cls, principal: Optional[Union["User", "APIKey"]], workspace: "Workspace"
    ):
        return cls.check_create_permissions(
            principal=principal, workspace=workspace, resource_type="Observation"
        )

    @classmethod
    def can_principal_delete(
        cls, principal: Optional[Union["User", "APIKey"]], workspace: "Workspace"
    ):
        if not principal:
            return False

        if hasattr(principal, "account_type"):
            if principal.account_type in [
                "admin",
                "staff",
            ]:
                return True

            if workspace.owner == principal:
                return True

            permissions = Permission.objects.filter(
                role__collaborator_assignments__user=principal,
                role__collaborator_assignments__workspace=workspace,
                resource_type__in=["*", "Observation"],
            ).values_list("permission_type", flat=True)

        elif hasattr(principal, "workspace"):
            if not workspace or principal.workspace != workspace:
                return False

            permissions = Permission.objects.filter(
                role=principal.role,
                resource_type__in=["*", "Observation"],
            ).values_list("permission_type", flat=True)

        else:
            return False

        return any(perm in permissions for perm in ["*", "delete"])

    def get_principal_permissions(
        self, principal: Optional[Union["User", "APIKey"]]
    ) -> list[Literal["edit", "delete", "view"]]:
        permissions = self.check_object_permissions(
            principal=principal,
            workspace=self.datastream.thing.workspace,
            resource_type="Observation",
        )

        if (
            not self.datastream.thing.workspace.is_private
            and not self.datastream.thing.is_private
            and not self.datastream.is_private
            and "view" not in list(permissions)
        ):
            permissions = list(permissions) + ["view"]

        return permissions

    def delete(self, *args, **kwargs):
        self.delete_contents(filter_arg=self, filter_suffix="")
        super().delete(*args, **kwargs)

    @classmethod
    def delete_contents(cls, filter_arg: models.Model, filter_suffix: Optional[str]):
        observation_relation_filter = (
            f"observation__{filter_suffix}" if filter_suffix else "observation"
        )

        cls.result_qualifiers.through.objects.filter(
            **{observation_relation_filter: filter_arg}
        ).delete()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["datastream_id", "phenomenon_time"],
                name="unique_datastream_id_phenomenon_time",
            )
        ]
