import uuid
import uuid6
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict, validate_call
from django.db import transaction
from django.db.models.query import QuerySet
from django.contrib.auth import get_user_model

from core.types import Unset
from core.iam.models import APIKey
from core.service import ServiceUtils
from processing.quality.models import QCHistory, QCSession, QCOperation, OperationType, SessionStatus
from processing.quality.services.session import QCSessionService


User = get_user_model()

qc_session_service = QCSessionService()


class OperationInput(BaseModel):
    order: int
    operation_type: OperationType
    comment: Optional[str] = None
    arguments: dict[str, Any] | list[Any] | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class QCOperationService(ServiceUtils):

    order_by_fields = {"id", "order", "operation_type", "created_at"}

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get(
        self,
        history: uuid.UUID | QCHistory,
        session: uuid.UUID | QCSession,
        operation: uuid.UUID | QCOperation,
        principal: User | APIKey | None | Unset = Unset,
        action: Literal["view", "edit"] = "view",
    ) -> QCOperation:
        """Get an operation belonging to a QC session."""

        session = qc_session_service.get(history=history, session=session, principal=principal, action=action)

        if isinstance(operation, uuid.UUID):
            try:
                operation = QCOperation.objects.select_related("session").get(pk=operation, session=session)
            except QCOperation.DoesNotExist:
                raise LookupError(f"QC operation with ID {str(operation)} does not exist.")
        elif operation.session_id != session.pk:
            raise LookupError(f"QC operation with ID {str(operation.id)} does not exist.")

        return operation

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get_collection(
        self,
        history: uuid.UUID | QCHistory,
        session: uuid.UUID | QCSession,
        principal: User | APIKey | None,
        page: int = Field(gt=0, default=1),
        page_size: int = Field(gt=0, default=100),
        order_by: list[str] = Field(default_factory=list),
    ) -> tuple[int, QuerySet[QCOperation]]:
        """Return all operations for a QC session in execution order."""

        session = qc_session_service.get(history=history, session=session, principal=principal, action="view")

        if not all(term.lstrip("-") in self.order_by_fields for term in order_by):
            raise ValueError(f"Invalid order_by field(s): {order_by}")

        queryset = QCOperation.objects.filter(session=session).order_by(*order_by, "order")

        count = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset:offset + page_size]

        return count, queryset

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def create(
        self,
        principal: User | APIKey | None,
        history: uuid.UUID | QCHistory,
        session: uuid.UUID | QCSession,
        operations: list[OperationInput],
    ) -> list[QCOperation]:
        """Append one or more operations to an in-progress session."""

        session = qc_session_service.get(history=history, session=session, principal=principal, action="edit")

        if session.status != SessionStatus.IN_PROGRESS:
            raise ValueError("Operations can only be added to an in-progress session.")

        return [
            QCOperation.objects.create(
                pk=uuid6.uuid7(),
                session=session,
                order=operation.order,
                operation_type=operation.operation_type.value,
                comment=operation.comment,
                arguments=operation.arguments if operation.arguments is not None else {},
            )
            for operation in operations
        ]

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def update(
        self,
        principal: User | APIKey | None,
        history: uuid.UUID | QCHistory,
        session: uuid.UUID | QCSession,
        operation: uuid.UUID | QCOperation,
        order: int | Unset = Unset,
        comment: str | None | Unset = Unset,
        arguments: dict[str, Any] | list[Any] | None | Unset = Unset,
    ) -> QCOperation:
        """Update an operation in an in-progress session."""

        operation = self.get(history=history, session=session, operation=operation, principal=principal, action="edit")

        if operation.session.status != SessionStatus.IN_PROGRESS:
            raise ValueError("Operations can only be updated in an in-progress session.")

        editable_fields = {"order": order, "comment": comment, "arguments": arguments}
        for field, value in editable_fields.items():
            if value is not Unset:
                setattr(operation, field, value)

        operation.save()

        return operation

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def delete(
        self,
        principal: User | APIKey | None,
        history: uuid.UUID | QCHistory,
        session: uuid.UUID | QCSession,
        operation: uuid.UUID | QCOperation,
    ) -> None:
        """Delete an operation from an in-progress session."""

        operation = self.get(history=history, session=session, operation=operation, principal=principal, action="edit")

        if operation.session.status != SessionStatus.IN_PROGRESS:
            raise ValueError("Operations can only be deleted from an in-progress session.")

        operation.delete()
