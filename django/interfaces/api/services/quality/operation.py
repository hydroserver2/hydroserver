import uuid

from typing import Any, Literal, Optional, get_args
from pydantic import BaseModel, ConfigDict
from django.db import transaction
from django.contrib.auth import get_user_model

from core.types import Unset
from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from processing.quality.models import QCHistory, QCSession, QCOperation, OperationType, SessionStatus
from interfaces.api.http.errors import BadRequestError, NotFoundError
from interfaces.api.service import APIService
from interfaces.api.services.quality.session import QCSessionAPIService
from interfaces.api.schemas.quality.operation import (
    QualityControlOperationOrderByFields,
    QualityControlOperationResponse,
)

User = get_user_model()

qc_session_service = QCSessionAPIService()


class OperationInput(BaseModel):
    order: int
    operation_type: OperationType
    comment: Optional[str] = None
    arguments: dict[str, Any] | list[Any] | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class QCOperationAPIService(APIService):

    order_by_fields = {"id", "order", "operation_type", "created_at"}

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        history: uuid.UUID | QCHistory,
        session: uuid.UUID | QCSession,
        operation: uuid.UUID | QCOperation,
        action: Literal["view", "edit"] = "view",
    ) -> QCOperation:
        session = qc_session_service.get(principal=principal, history=history, session=session, action=action)

        if isinstance(operation, uuid.UUID):
            try:
                operation = QCOperation.objects.select_related("session").get(pk=operation, session=session)
            except QCOperation.DoesNotExist:
                raise NotFoundError(f"QC operation with ID {str(operation)} does not exist.")
        elif operation.session_id != session.pk:
            raise NotFoundError(f"QC operation with ID {str(operation.id)} does not exist.")

        return operation

    def get_item(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        history: uuid.UUID | QCHistory,
        session: uuid.UUID | QCSession,
        operation: uuid.UUID | QCOperation,
    ):
        operation = self.get(principal=principal, history=history, session=session, operation=operation, action="view")

        return {
            "data": QualityControlOperationResponse.model_validate(operation),
            "included": {},
        }

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        history: uuid.UUID | QCHistory,
        session: uuid.UUID | QCSession,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        order_by: Optional[list[str]] = None,
    ):
        session = qc_session_service.get(principal=principal, history=history, session=session, action="view")
        queryset = QCOperation.objects.filter(session=session)

        if order_by:
            queryset = self.apply_ordering(
                queryset, order_by, list(get_args(QualityControlOperationOrderByFields))
            )
        else:
            queryset = queryset.order_by("order")

        queryset, meta = self.apply_pagination(queryset, offset, limit)
        operations = list(queryset.all())

        return {
            "data": [QualityControlOperationResponse.model_validate(o) for o in operations],
            "meta": meta,
            "included": {},
        }

    @transaction.atomic
    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        history: uuid.UUID | QCHistory,
        session: uuid.UUID | QCSession,
        operations: list[OperationInput],
    ):
        session = qc_session_service.get(principal=principal, history=history, session=session, action="edit")
        created = []

        for operation in operations:
            new_operation = QCOperation(
                pk=uuid.uuid7(),
                session=session,
                created_by=principal if isinstance(principal, User) else None,
                order=operation.order,
                operation_type=operation.operation_type.value,
                comment=operation.comment,
                arguments=operation.arguments if operation.arguments is not None else {},
            )
            new_operation.full_clean()
            new_operation.save()
            created.append(new_operation)

        return [{"id": operation.pk} for operation in created]

    @transaction.atomic
    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        history: uuid.UUID | QCHistory,
        session: uuid.UUID | QCSession,
        operation: uuid.UUID | QCOperation,
        order: int | Unset = Unset,
        comment: str | None | Unset = Unset,
        arguments: dict[str, Any] | list[Any] | None | Unset = Unset,
    ):
        operation = self.get(principal=principal, history=history, session=session, operation=operation, action="edit")
        editable_fields = {"order": order, "comment": comment, "arguments": arguments}

        for field, value in editable_fields.items():
            if value is not Unset:
                setattr(operation, field, value)

        operation.full_clean()
        operation.save()

    @transaction.atomic
    def delete(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        history: uuid.UUID | QCHistory,
        session: uuid.UUID | QCSession,
        operation: uuid.UUID | QCOperation,
    ) -> None:
        operation = self.get(principal=principal, history=history, session=session, operation=operation, action="edit")

        if operation.session.status != SessionStatus.IN_PROGRESS:
            raise BadRequestError("Operations can only be deleted from an in-progress session.")

        operation.delete()
