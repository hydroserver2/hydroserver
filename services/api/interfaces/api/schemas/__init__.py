from .base import (BaseGetResponse, BasePostBody, BasePatchBody, BaseQueryParameters, CollectionQueryParameters,
                   VocabularyQueryParameters)
from .workspace import (
    WorkspaceSummaryResponse,
    WorkspaceDetailResponse,
    WorkspaceQueryParameters,
    WorkspacePostBody,
    WorkspacePatchBody,
    WorkspaceTransferBody,
    AccountContactDetailResponse
)
from .collaborator import (
    CollaboratorDetailResponse,
    CollaboratorQueryParameters,
    CollaboratorPostBody,
    CollaboratorDeleteBody,
)
from .api_key import (
    APIKeySummaryResponse,
    APIKeyDetailResponse,
    APIKeyQueryParameters,
    APIKeyPostBody,
    APIKeyPatchBody,
    APIKeySummaryPostResponse,
    APIKeyDetailPostResponse,
)
from .role import RoleDetailResponse, RoleSummaryResponse, RoleQueryParameters

from .thing import (
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
from .observed_property import (
    ObservedPropertySummaryResponse,
    ObservedPropertyDetailResponse,
    ObservedPropertyQueryParameters,
    ObservedPropertyPostBody,
    ObservedPropertyPatchBody,
)
from .processing_level import (
    ProcessingLevelSummaryResponse,
    ProcessingLevelDetailResponse,
    ProcessingLevelQueryParameters,
    ProcessingLevelPostBody,
    ProcessingLevelPatchBody,
)
from .result_qualifier import (
    ResultQualifierSummaryResponse,
    ResultQualifierDetailResponse,
    ResultQualifierQueryParameters,
    ResultQualifierPostBody,
    ResultQualifierPatchBody,
)
from .sensor import (
    SensorSummaryResponse,
    SensorDetailResponse,
    SensorQueryParameters,
    SensorPostBody,
    SensorPatchBody,
)
from .unit import (
    UnitSummaryResponse,
    UnitDetailResponse,
    UnitQueryParameters,
    UnitPostBody,
    UnitPatchBody,
)
from .datastream import (
    DatastreamSummaryResponse,
    DatastreamDetailResponse,
    DatastreamQueryParameters,
    DatastreamPostBody,
    DatastreamPatchBody,
)
from .observation import (
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
from .attachment import (
    FileAttachmentQueryParameters,
    TagGetResponse,
    TagPostBody,
    TagDeleteBody,
    FileAttachmentDeleteBody,
    FileAttachmentPatchBody,
    FileAttachmentGetResponse,
)

from .data_connection import (DataConnectionSummaryResponse, DataConnectionDetailResponse, DataConnectionPostBody,
                              DataConnectionPatchBody, DataConnectionFields, DataConnectionOrderByFields,
                              DataConnectionQueryParameters)
from .orchestration_system import (OrchestrationSystemSummaryResponse, OrchestrationSystemDetailResponse,
                                   OrchestrationSystemPostBody, OrchestrationSystemPatchBody,
                                   OrchestrationSystemFields, OrchestrationSystemOrderByFields,
                                   OrchestrationSystemQueryParameters)
from .task import (TaskSummaryResponse, TaskDetailResponse, TaskPostBody, TaskPatchBody, TaskRunResponse, TaskFields,
                   TaskQueryParameters, TaskOrderByFields, TaskScheduleFields, TaskSchedulePostBody,
                   TaskMappingPostBody, TaskMappingPathPostBody)
from .run import (TaskRunFields, TaskRunResponse, TaskRunPostBody, TaskRunPatchBody, TaskRunQueryParameters,
                  TaskRunOrderByFields)


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
