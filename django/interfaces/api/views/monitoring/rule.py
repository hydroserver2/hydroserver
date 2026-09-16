import uuid

from ninja import Router, Path, Query

from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth
from interfaces.api.services.monitoring.rule import MonitoringRuleAPIService
from interfaces.api.schemas import PaginatedResponse, ItemResponse, CreatedResponse
from interfaces.api.schemas.monitoring.rule import (
    MonitoringRuleResponse,
    MonitoringRulePostBody,
    MonitoringRulePatchBody,
    MonitoringRuleQueryParameters,
    MonitoringRuleItemQueryParameters,
)

monitoring_rule_router = Router(tags=["Monitoring Rules"])
monitoring_rule_service = MonitoringRuleAPIService()


@monitoring_rule_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: PaginatedResponse[MonitoringRuleResponse],
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_monitoring_rules(
    request: HydroServerHttpRequest,
    query: Query[MonitoringRuleQueryParameters],
):
    """
    Get monitoring rules.
    """

    return 200, monitoring_rule_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
    )


@monitoring_rule_router.post(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        201: CreatedResponse,
        400: str,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def create_monitoring_rule(
    request: HydroServerHttpRequest,
    data: MonitoringRulePostBody,
):
    """
    Create a monitoring rule on a datastream belonging to the given task.
    """

    return 201, monitoring_rule_service.create(
        principal=request.principal,
        data=data,
    )


@monitoring_rule_router.get(
    "/{rule_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: ItemResponse[MonitoringRuleResponse],
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_monitoring_rule(
    request: HydroServerHttpRequest,
    rule_id: Path[uuid.UUID],
    query: Query[MonitoringRuleItemQueryParameters],
):
    """
    Get a monitoring rule.
    """

    return 200, monitoring_rule_service.get(
        principal=request.principal,
        uid=rule_id,
        include=query.include,
    )


@monitoring_rule_router.patch(
    "/{rule_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        400: str,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def update_monitoring_rule(
    request: HydroServerHttpRequest,
    rule_id: Path[uuid.UUID],
    data: MonitoringRulePatchBody,
):
    """
    Update a monitoring rule's parameters.
    """

    monitoring_rule_service.update(
        principal=request.principal,
        uid=rule_id,
        data=data,
    )

    return 204, None


@monitoring_rule_router.delete(
    "/{rule_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
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
    rule_id: Path[uuid.UUID],
):
    """
    Delete a monitoring rule.
    """

    monitoring_rule_service.delete(
        principal=request.principal,
        uid=rule_id,
    )

    return 204, None
