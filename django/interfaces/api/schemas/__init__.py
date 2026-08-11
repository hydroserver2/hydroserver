from .base import (BaseGetResponse, BasePostBody, BasePatchBody, BaseQueryParameters, CollectionQueryParameters,
                   VocabularyQueryParameters, OrderByField)
from interfaces.api.schemas.iam.workspace import (
    WorkspaceSummaryResponse,
    WorkspaceDetailResponse,
    WorkspaceQueryParameters,
    WorkspacePostBody,
    WorkspacePatchBody,
    WorkspaceTransferBody,
    AccountContactDetailResponse
)
from interfaces.api.schemas.iam.collaborator import (
    CollaboratorDetailResponse,
    CollaboratorQueryParameters,
    CollaboratorPostBody,
    CollaboratorDeleteBody,
)
from interfaces.api.schemas.iam.service_account import (
    ServiceAccountSummaryResponse,
    ServiceAccountDetailResponse,
    ServiceAccountQueryParameters,
    ServiceAccountPostBody,
    ServiceAccountPatchBody,
    ServiceAccountSummaryPostResponse,
    ServiceAccountDetailPostResponse,
    ServiceAccountContactResponse,
)
from interfaces.api.schemas.iam.role import (RoleDetailResponse, RoleSummaryResponse, RoleQueryParameters,
                                             RoleOrderByFields)

from interfaces.api.schemas.sta.monitoring_site import (
    MonitoringSiteMarkerResponse,
    MonitoringSiteMarkerQueryParameters,
    SiteTypeIconResponse,
    MonitoringSiteMapSummaryResponse,
    MonitoringSiteMapSummaryQueryParameters,
    MonitoringSiteSummaryResponse,
    MonitoringSiteTaskSummaryResponse,
    MonitoringSiteTaskSummaryQueryParameters,
    MonitoringSiteSummaryResponse,
    MonitoringSiteDetailResponse,
    MonitoringSitePostBody,
    MonitoringSitePatchBody,
    MonitoringSiteQueryParameters,
    TagGetResponse,
    FileAttachmentGetResponse,
)
from interfaces.api.schemas.sta.observed_property import (
    ObservedPropertySummaryResponse,
    ObservedPropertyDetailResponse,
    ObservedPropertyQueryParameters,
    ObservedPropertyPostBody,
    ObservedPropertyPatchBody,
)
from interfaces.api.schemas.sta.processing_level import (
    ProcessingLevelSummaryResponse,
    ProcessingLevelDetailResponse,
    ProcessingLevelQueryParameters,
    ProcessingLevelPostBody,
    ProcessingLevelPatchBody,
)
from interfaces.api.schemas.sta.result_qualifier import (
    ResultQualifierSummaryResponse,
    ResultQualifierDetailResponse,
    ResultQualifierQueryParameters,
    ResultQualifierPostBody,
    ResultQualifierPatchBody,
)
from interfaces.api.schemas.sta.method import (
    MethodSummaryResponse,
    MethodDetailResponse,
    MethodQueryParameters,
    MethodPostBody,
    MethodPatchBody,
)
from interfaces.api.schemas.sta.unit import (
    UnitSummaryResponse,
    UnitDetailResponse,
    UnitQueryParameters,
    UnitPostBody,
    UnitPatchBody,
)
from interfaces.api.schemas.sta.datastream import (
    DatastreamVisualizationBootstrapQueryParameters,
    DatastreamVisualizationBootstrapResponse,
    DatastreamSummaryResponse,
    DatastreamDetailResponse,
    DatastreamQueryParameters,
    DatastreamPostBody,
    DatastreamPatchBody,
)
from interfaces.api.schemas.sta.observation import (
    ObservationSummaryResponse,
    ObservationDetailResponse,
    ObservationQueryParameters,
    ObservationRowResponse,
    ObservationColumnarResponse,
    ObservationPostBody,
    ObservationBulkPostQueryParameters,
    ObservationBulkPostBody,
    ObservationBulkColumnarPostBody,
    ObservationBulkDeleteBody,
)
from interfaces.api.schemas.sta.attachment import (
    FileAttachmentQueryParameters,
    TagGetResponse,
    TagPostBody,
    TagDeleteBody,
    FileAttachmentGetResponse,
    FileAttachmentPostBody,
    FileAttachmentDeleteBody,
)
from interfaces.api.schemas.etl.data_connection import (
    DataConnectionResponse,
    DataConnectionQueryParameters,
    DataConnectionPostBody,
    DataConnectionPatchBody,
)

WorkspaceDetailResponse.model_rebuild()
RoleDetailResponse.model_rebuild()

ServiceAccountDetailResponse.model_rebuild()
ServiceAccountDetailPostResponse.model_rebuild()

CollaboratorDetailResponse.model_rebuild()

MonitoringSiteDetailResponse.model_rebuild()
ObservedPropertyDetailResponse.model_rebuild()
ProcessingLevelDetailResponse.model_rebuild()
ResultQualifierDetailResponse.model_rebuild()
MethodDetailResponse.model_rebuild()
UnitDetailResponse.model_rebuild()
DatastreamDetailResponse.model_rebuild()
ObservationDetailResponse.model_rebuild()
