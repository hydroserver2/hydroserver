import uuid
from typing import Optional
from ninja import Router, Path, Query, File, Form
from ninja.files import UploadedFile
from django.db import transaction
from django.http import HttpResponse
from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.schemas import VocabularyQueryParameters
from interfaces.api.schemas import (
    MonitoringSiteMarkerResponse,
    MonitoringSiteMarkerQueryParameters,
    SiteTypeIconResponse,
    MonitoringSiteMapSummaryResponse,
    MonitoringSiteMapSummaryQueryParameters,
    MonitoringSiteSummaryResponse,
    MonitoringSiteTaskSummaryResponse,
    MonitoringSiteTaskSummaryQueryParameters,
    MonitoringSiteDetailResponse,
    MonitoringSitePostBody,
    MonitoringSitePatchBody,
    MonitoringSiteQueryParameters,
    LinkedResourceQueryParameters,
    LinkedResourceGetResponse,
    LinkedResourcePostBody,
)
from core.sta.services import MonitoringSiteService
from core.web.models import SiteTypeIcon

monitoring_site_router = Router(tags=["Monitoring Sites"])
monitoring_site_service = MonitoringSiteService()


@monitoring_site_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: list[MonitoringSiteSummaryResponse] | list[MonitoringSiteDetailResponse],
        401: str,
    },
    by_alias=True,
)
def get_monitoring_sites(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[MonitoringSiteQueryParameters],
):
    """
    Get public MonitoringSites and MonitoringSites associated with the authenticated user.
    """

    return 200, monitoring_site_service.list(
        principal=request.principal,
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
        expand_related=query.expand_related,
    )


@monitoring_site_router.get(
    "/markers",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: list[MonitoringSiteMarkerResponse],
        401: str,
    },
    by_alias=True,
)
def get_monitoring_site_markers(
    request: HydroServerHttpRequest,
    query: Query[MonitoringSiteMarkerQueryParameters],
):
    """
    Get lean marker data for public MonitoringSites plus private MonitoringSites visible to the authenticated user.
    """

    return 200, monitoring_site_service.list_markers(
        principal=request.principal,
        filtering=query.dict(exclude_unset=True),
    )


@monitoring_site_router.get(
    "/site-summaries",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: list[MonitoringSiteMapSummaryResponse],
        401: str,
    },
    by_alias=True,
)
def get_monitoring_site_summaries(
    request: HydroServerHttpRequest,
    query: Query[MonitoringSiteMapSummaryQueryParameters],
):
    """
    Get lean site summary data for public MonitoringSites and MonitoringSites associated with the authenticated user.
    """

    return 200, monitoring_site_service.list_site_summaries(
        principal=request.principal,
        filtering=query.dict(exclude_unset=True),
    )


@monitoring_site_router.get(
    "/task-summaries",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: list[MonitoringSiteTaskSummaryResponse],
        401: str,
    },
    by_alias=True,
)
def get_monitoring_site_task_summaries(
    request: HydroServerHttpRequest,
    query: Query[MonitoringSiteTaskSummaryQueryParameters],
):
    """
    Get task count summaries for MonitoringSites associated with the authenticated user.
    """

    return 200, monitoring_site_service.list_task_summaries(
        principal=request.principal,
        workspace_id=query.workspace_id or None,
        type=query.type or None,
    )


@monitoring_site_router.post(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        201: MonitoringSiteSummaryResponse | MonitoringSiteDetailResponse,
        400: str,
        401: str,
        422: str,
    },
    by_alias=True,
)
@transaction.atomic
def create_monitoring_site(
    request: HydroServerHttpRequest,
    data: MonitoringSitePostBody,
    expand_related: Optional[bool] = None,
):
    """
    Create a new MonitoringSite.
    """

    return 201, monitoring_site_service.create(
        principal=request.principal, data=data, expand_related=expand_related
    )


@monitoring_site_router.get(
    "/tags/keys",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: dict[str, list[str]],
        401: str,
    },
)
def get_monitoring_site_tag_keys(
    request: HydroServerHttpRequest,
    workspace_id: Optional[uuid.UUID] = None,
    monitoring_site_id: Optional[uuid.UUID] = None,
):
    """
    Get all existing unique monitoring_site tag keys.
    """

    return 200, monitoring_site_service.get_tag_keys(
        principal=request.principal,
        workspace_id=workspace_id,
        monitoring_site_id=monitoring_site_id,
    )


@monitoring_site_router.get("/site-types", response={200: list[str]}, by_alias=True)
def get_site_types(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[VocabularyQueryParameters],
):
    """
    Get site types.
    """

    return 200, monitoring_site_service.list_site_types(
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_desc=query.order_desc,
    )


@monitoring_site_router.get(
    "/site-type-icons",
    response={200: list[SiteTypeIconResponse]},
    by_alias=True,
)
def get_site_type_icons(request: HydroServerHttpRequest):
    """
    Get the configured site type icon mappings.
    """

    return 200, SiteTypeIcon.objects.values("icon", "site_types")


@monitoring_site_router.get("/linked-resource-types", response={200: list[str]}, by_alias=True)
def get_monitoring_site_linked_resource_types(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[VocabularyQueryParameters],
):
    """
    Get linked resource types.
    """

    return 200, monitoring_site_service.list_linked_resource_types(
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_desc=query.order_desc,
    )


@monitoring_site_router.get(
    "/{monitoring_site_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: MonitoringSiteSummaryResponse | MonitoringSiteDetailResponse,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_monitoring_site(
    request: HydroServerHttpRequest,
    monitoring_site_id: Path[uuid.UUID],
    expand_related: Optional[bool] = None,
):
    """
    Get a MonitoringSite.
    """

    return 200, monitoring_site_service.get(
        principal=request.principal, uid=monitoring_site_id, expand_related=expand_related
    )


@monitoring_site_router.patch(
    "/{monitoring_site_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: MonitoringSiteSummaryResponse | MonitoringSiteDetailResponse,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_monitoring_site(
    request: HydroServerHttpRequest,
    monitoring_site_id: Path[uuid.UUID],
    data: MonitoringSitePatchBody,
    expand_related: Optional[bool] = None,
):
    """
    Update a MonitoringSite.
    """

    return 200, monitoring_site_service.update(
        principal=request.principal,
        uid=monitoring_site_id,
        data=data,
        expand_related=expand_related,
    )


@monitoring_site_router.delete(
    "/{monitoring_site_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def delete_monitoring_site(request: HydroServerHttpRequest, monitoring_site_id: Path[uuid.UUID]):
    """
    Delete a MonitoringSite.
    """

    return 204, monitoring_site_service.delete(principal=request.principal, uid=monitoring_site_id)


@monitoring_site_router.get(
    "/{monitoring_site_id}/linked-resources",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: list[LinkedResourceGetResponse],
        401: str,
        403: str,
    },
    by_alias=True,
)
def get_monitoring_site_linked_resources(
    request: HydroServerHttpRequest,
    monitoring_site_id: Path[uuid.UUID],
    query: Query[LinkedResourceQueryParameters],
):
    """
    Get all linked resources associated with a MonitoringSite.
    """

    return 200, monitoring_site_service.get_linked_resources(
        principal=request.principal,
        uid=monitoring_site_id,
        filtering=query.dict(exclude_unset=True),
    )


@monitoring_site_router.post(
    "/{monitoring_site_id}/linked-resources",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        201: LinkedResourceGetResponse,
        400: str,
        401: str,
        403: str,
        413: str,
        422: str,
    },
    by_alias=True,
)
def add_monitoring_site_linked_resource(
    request: HydroServerHttpRequest,
    monitoring_site_id: Path[uuid.UUID],
    name: str = Form(..., min_length=1),
    description: Optional[str] = Form(None),
    type: str = Form(..., min_length=1),
    file: Optional[UploadedFile] = File(None),
    link: Optional[str] = Form(None),
):
    """
    Add a linked resource to a monitoring_site.
    """

    return 201, monitoring_site_service.add_linked_resource(
        principal=request.principal,
        uid=monitoring_site_id,
        file=file,
        link=link,
        data=LinkedResourcePostBody(
            name=name,
            description=description,
            type=type,
        )
    )


@monitoring_site_router.patch(
    "/{monitoring_site_id}/linked-resources/{linked_resource_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: LinkedResourceGetResponse,
        400: str,
        401: str,
        403: str,
        404: str,
        413: str,
        422: str,
    },
    by_alias=True,
)
def update_monitoring_site_linked_resource(
    request: HydroServerHttpRequest,
    monitoring_site_id: Path[uuid.UUID],
    linked_resource_id: Path[uuid.UUID],
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    type: Optional[str] = Form(None),
    file: Optional[UploadedFile] = File(None),
    link: Optional[str] = Form(None),
):
    """
    Update a linked resource for a monitoring_site. A linked resource's mode (hosted file vs.
    external URL) cannot be changed in place — delete it and create a new one instead.
    """

    return 200, monitoring_site_service.update_linked_resource(
        principal=request.principal,
        uid=monitoring_site_id,
        linked_resource_id=linked_resource_id,
        name=name,
        description=description,
        type=type,
        file=file,
        link=link,
    )


@monitoring_site_router.delete(
    "/{monitoring_site_id}/linked-resources/{linked_resource_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def remove_monitoring_site_linked_resource(
    request: HydroServerHttpRequest,
    monitoring_site_id: Path[uuid.UUID],
    linked_resource_id: Path[uuid.UUID],
):
    """
    Remove a linked resource from a monitoring_site.
    """

    return 204, monitoring_site_service.remove_linked_resource(
        principal=request.principal,
        uid=monitoring_site_id,
        linked_resource_id=linked_resource_id,
    )
