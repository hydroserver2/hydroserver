import uuid

from ninja import Router, Path, Query
from django.http import HttpResponse

from core.types import Unset
from interfaces.api.http.errors import raise_http_errors
from interfaces.api.http.response import apply_response_pagination_headers
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import bearer_auth, session_auth, apikey_auth
from processing.monitoring.services.rule import MonitoringRuleService
from interfaces.api.schemas.monitoring.rule import (
    MonitoringRuleResponse,
    MonitoringRulePostBody,
    MonitoringRulePatchBody,
    MonitoringRuleQueryParameters,
)

monitoring_rule_router = Router(tags=["Monitoring Rules"])
monitoring_rule_service = MonitoringRuleService()


@monitoring_rule_router.get(
    "",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: list[MonitoringRuleResponse],
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_monitoring_rules(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    task_id: Path[uuid.UUID],
    query: Query[MonitoringRuleQueryParameters],
):
    """
    Get rules for a monitoring task.
    """

    with raise_http_errors():
        count, rules = monitoring_rule_service.get_collection(
            task=task_id,
            principal=request.principal,
            order_by=[f.orm_field for f in query.order_by],
            **query.model_dump(exclude_unset=True, exclude={"order_by", "datastream"}),
            **({"datastream": query.datastream} if "datastream" in query.model_fields_set else {}),
        )

    apply_response_pagination_headers(
        response=response,
        count=count,
        page=query.page,
        page_size=query.page_size,
    )

    return 200, rules


@monitoring_rule_router.post(
    "",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        201: MonitoringRuleResponse,
        400: str,
        401: str,
        403: str,
        404: str,
        422: str,
    },
    by_alias=True,
)
def create_monitoring_rule(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    data: MonitoringRulePostBody,
):
    """
    Create a monitoring rule on a datastream belonging to the given task.
    """

    with raise_http_errors():
        rule = monitoring_rule_service.create(
            task=task_id,
            principal=request.principal,
            **data.model_dump(exclude_unset=True, exclude={"uid"}),
            **({"uid": data.uid} if data.uid is not Unset else {}),
        )

    return 201, rule


@monitoring_rule_router.get(
    "/{rule_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: MonitoringRuleResponse,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_monitoring_rule(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    rule_id: Path[uuid.UUID],
):
    """
    Get a monitoring rule.
    """

    with raise_http_errors():
        rule = monitoring_rule_service.get(
            rule=rule_id,
            task=task_id,
            principal=request.principal,
        )

    return 200, rule


@monitoring_rule_router.patch(
    "/{rule_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: MonitoringRuleResponse,
        400: str,
        401: str,
        403: str,
        404: str,
        422: str,
    },
    by_alias=True,
)
def update_monitoring_rule(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    rule_id: Path[uuid.UUID],
    data: MonitoringRulePatchBody,
):
    """
    Update a monitoring rule's parameters.
    """

    with raise_http_errors():
        rule = monitoring_rule_service.update(
            rule=rule_id,
            task=task_id,
            principal=request.principal,
            **data.model_dump(exclude_unset=True),
        )

    return 200, rule


@monitoring_rule_router.delete(
    "/{rule_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        204: None,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def delete_monitoring_rule(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    rule_id: Path[uuid.UUID],
):
    """
    Delete a monitoring rule.
    """

    with raise_http_errors():
        monitoring_rule_service.delete(
            rule=rule_id,
            task=task_id,
            principal=request.principal,
        )

    return 204, None
