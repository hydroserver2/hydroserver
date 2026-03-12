import uuid
from typing import Optional
from ninja import Router, Path, Query, File, Form
from ninja.files import UploadedFile
from django.http import HttpResponse
from django.db import transaction
from interfaces.http.auth import bearer_auth, session_auth, apikey_auth, anonymous_auth
from interfaces.http.request import HydroServerHttpRequest
from interfaces.api.schemas import VocabularyQueryParameters
from interfaces.api.schemas import (
    DatastreamSummaryResponse,
    DatastreamDetailResponse,
    DatastreamQueryParameters,
    DatastreamPostBody,
    DatastreamPatchBody,
    TagGetResponse,
    TagPostBody,
    TagDeleteBody,
    FileAttachmentGetResponse,
    FileAttachmentDeleteBody,
)
from domains.sta.services import DatastreamService
from interfaces.api.views.observation import observation_router

datastream_router = Router(tags=["Datastreams"])
datastream_service = DatastreamService()


@datastream_router.get(
    "",
    auth=[session_auth, bearer_auth, apikey_auth, anonymous_auth],
    response={
        200: list[DatastreamSummaryResponse] | list[DatastreamDetailResponse],
        401: str,
    },
    by_alias=True,
)
def get_datastreams(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[DatastreamQueryParameters],
):
    """
    Get public Datastreams and Datastreams associated with the authenticated user.
    """

    return 200, datastream_service.list(
        principal=request.principal,
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
        expand_related=query.expand_related,
    )


@datastream_router.post(
    "",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        201: DatastreamSummaryResponse | DatastreamDetailResponse,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
@transaction.atomic
def create_datastream(
    request: HydroServerHttpRequest,
    data: DatastreamPostBody,
    expand_related: Optional[bool] = None,
):
    """
    Create a new Datastream.
    """

    return 201, datastream_service.create(
        principal=request.principal, data=data, expand_related=expand_related
    )


@datastream_router.get(
    "/tags/keys",
    auth=[session_auth, bearer_auth, apikey_auth, anonymous_auth],
    response={
        200: dict[str, list[str]],
        401: str,
    },
)
def get_datastream_tag_keys(
    request: HydroServerHttpRequest,
    workspace_id: Optional[uuid.UUID] = None,
    datastream_id: Optional[uuid.UUID] = None,
):
    """
    Get all existing unique datastream tag keys.
    """

    return 200, datastream_service.get_tag_keys(
        principal=request.principal,
        workspace_id=workspace_id,
        datastream_id=datastream_id,
    )


@datastream_router.get(
    "/aggregation-statistics", response={200: list[str]}, by_alias=True
)
def get_datastream_aggregation_statistics(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[VocabularyQueryParameters],
):
    """
    Get datastream aggregation statistics.
    """

    return 200, datastream_service.list_aggregation_statistics(
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_desc=query.order_desc,
    )


@datastream_router.get("/statuses", response={200: list[str]}, by_alias=True)
def get_datastream_statuses(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[VocabularyQueryParameters],
):
    """
    Get datastream statuses.
    """

    return 200, datastream_service.list_statuses(
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_desc=query.order_desc,
    )


@datastream_router.get("/sampled-mediums", response={200: list[str]}, by_alias=True)
def get_datastream_sampled_mediums(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[VocabularyQueryParameters],
):
    """
    Get datastream sampled mediums.
    """

    return 200, datastream_service.list_sampled_mediums(
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_desc=query.order_desc,
    )


@datastream_router.get(
    "/file-attachment-types", response={200: list[str]}, by_alias=True
)
def get_file_attachment_types(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[VocabularyQueryParameters],
):
    """
    Get file attachment types.
    """

    return 200, datastream_service.list_file_attachment_types(
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_desc=query.order_desc,
    )


@datastream_router.get(
    "/{datastream_id}",
    auth=[session_auth, bearer_auth, apikey_auth, anonymous_auth],
    response={
        200: DatastreamSummaryResponse | DatastreamDetailResponse,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_datastream(
    request: HydroServerHttpRequest,
    datastream_id: Path[uuid.UUID],
    expand_related: Optional[bool] = None,
):
    """
    Get a Datastream.
    """

    return 200, datastream_service.get(
        principal=request.principal, uid=datastream_id, expand_related=expand_related
    )


@datastream_router.patch(
    "/{datastream_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: DatastreamSummaryResponse | DatastreamDetailResponse,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_datastream(
    request: HydroServerHttpRequest,
    datastream_id: Path[uuid.UUID],
    data: DatastreamPatchBody,
    expand_related: Optional[bool] = None,
):
    """
    Update a Datastream.
    """

    return 200, datastream_service.update(
        principal=request.principal,
        uid=datastream_id,
        data=data,
        expand_related=expand_related,
    )


@datastream_router.delete(
    "/{datastream_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def delete_datastream(request: HydroServerHttpRequest, datastream_id: Path[uuid.UUID]):
    """
    Delete a Datastream.
    """

    return 204, datastream_service.delete(
        principal=request.principal, uid=datastream_id
    )


@datastream_router.get(
    "/{datastream_id}/tags",
    auth=[session_auth, bearer_auth, apikey_auth, anonymous_auth],
    response={
        200: list[TagGetResponse],
        401: str,
        403: str,
    },
    by_alias=True,
)
def get_datastream_tags(
    request: HydroServerHttpRequest, datastream_id: Path[uuid.UUID]
):
    """
    Get all tags associated with a Datastream.
    """

    return 200, datastream_service.get_tags(
        principal=request.principal,
        uid=datastream_id,
    )


@datastream_router.post(
    "/{datastream_id}/tags",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        201: TagGetResponse,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
def add_datastream_tag(
    request: HydroServerHttpRequest, datastream_id: Path[uuid.UUID], data: TagPostBody
):
    """
    Add a tag to a Datastream.
    """

    return 201, datastream_service.add_tag(
        principal=request.principal,
        uid=datastream_id,
        data=data,
    )


@datastream_router.put(
    "/{datastream_id}/tags",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: TagGetResponse,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
def edit_datastream_tag(
    request: HydroServerHttpRequest, datastream_id: Path[uuid.UUID], data: TagPostBody
):
    """
    Edit a tag of a Datastream.
    """

    return 200, datastream_service.update_tag(
        principal=request.principal,
        uid=datastream_id,
        data=data,
    )


@datastream_router.delete(
    "/{datastream_id}/tags",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        204: None,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
def remove_datastream_tag(
    request: HydroServerHttpRequest, datastream_id: Path[uuid.UUID], data: TagDeleteBody
):
    """
    Remove a tag from a Datastream.
    """

    return 204, datastream_service.remove_tag(
        principal=request.principal,
        uid=datastream_id,
        data=data,
    )


@datastream_router.get(
    "/{datastream_id}/file-attachments",
    auth=[session_auth, bearer_auth, apikey_auth, anonymous_auth],
    response={
        200: list[FileAttachmentGetResponse],
        401: str,
        403: str,
    },
    by_alias=True,
)
def get_datastream_file_attachments(
    request: HydroServerHttpRequest, datastream_id: Path[uuid.UUID]
):
    """
    Get all file attachments associated with a Datastream.
    """

    return 200, datastream_service.get_file_attachments(
        principal=request.principal,
        uid=datastream_id,
    )


@datastream_router.post(
    "/{datastream_id}/file-attachments",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        201: FileAttachmentGetResponse,
        400: str,
        401: str,
        403: str,
        413: str,
        422: str,
    },
    by_alias=True,
)
def add_datastream_file_attachment(
    request: HydroServerHttpRequest,
    datastream_id: Path[uuid.UUID],
    file_attachment_type: str = Form(...),
    file: UploadedFile = File(...),
):
    """
    Add a file attachment to a datastream.
    """

    return 201, datastream_service.add_file_attachment(
        principal=request.principal,
        uid=datastream_id,
        file=file,
        file_attachment_type=file_attachment_type,
    )


@datastream_router.delete(
    "/{datastream_id}/file-attachments",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        204: None,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
def remove_datastream_file_attachment(
    request: HydroServerHttpRequest,
    datastream_id: Path[uuid.UUID],
    data: FileAttachmentDeleteBody,
):
    """
    Remove a file attachment from a datastream.
    """

    return 204, datastream_service.remove_file_attachment(
        principal=request.principal,
        uid=datastream_id,
        data=data,
    )


@datastream_router.get(
    "/{datastream_id}/csv",
    auth=[session_auth, bearer_auth, apikey_auth, anonymous_auth],
    response={200: None, 403: str, 404: str},
)
def get_datastream_csv(request: HydroServerHttpRequest, datastream_id: Path[uuid.UUID]):
    """
    Get a CSV representation of the Datastream.
    """

    return datastream_service.get_csv(principal=request.principal, uid=datastream_id)


datastream_router.add_router("{datastream_id}/observations", observation_router)
