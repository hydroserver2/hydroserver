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
from interfaces.api.schemas.iam.api_key import (
    APIKeySummaryResponse,
    APIKeyDetailResponse,
    APIKeyQueryParameters,
    APIKeyPostBody,
    APIKeyPatchBody,
    APIKeySummaryPostResponse,
    APIKeyDetailPostResponse,
)
from interfaces.api.schemas.iam.role import (RoleDetailResponse, RoleSummaryResponse, RoleQueryParameters,
                                             RoleOrderByFields)

from interfaces.api.schemas.sta.thing import (
    ThingMarkerResponse,
    ThingMarkerQueryParameters,
    ThingSiteSummaryResponse,
    ThingSiteSummaryQueryParameters,
    ThingSummaryResponse,
    ThingDetailResponse,
    ThingPostBody,
    ThingPatchBody,
    ThingQueryParameters,
    LocationPostBody,
    LocationPatchBody,
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
from interfaces.api.schemas.sta.sensor import (
    SensorSummaryResponse,
    SensorDetailResponse,
    SensorQueryParameters,
    SensorPostBody,
    SensorPatchBody,
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

APIKeyDetailResponse.model_rebuild()
APIKeyDetailPostResponse.model_rebuild()

CollaboratorDetailResponse.model_rebuild()

ThingDetailResponse.model_rebuild()
ObservedPropertyDetailResponse.model_rebuild()
ProcessingLevelDetailResponse.model_rebuild()
ResultQualifierDetailResponse.model_rebuild()
SensorDetailResponse.model_rebuild()
UnitDetailResponse.model_rebuild()
DatastreamDetailResponse.model_rebuild()
ObservationDetailResponse.model_rebuild()
