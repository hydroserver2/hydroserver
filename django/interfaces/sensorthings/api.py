from django.db import transaction
from sensorthings import SensorThingsExtension
from sensorthings.factories import SensorThingsEndpointHookFactory
from interfaces.http.auth import session_auth, bearer_auth, apikey_auth, anonymous_auth
from .schemas import (DatastreamListResponse, DatastreamGetResponse, ThingListResponse, ThingGetResponse,
                      LocationListResponse, LocationGetResponse, ObservationListResponse, ObservationGetResponse,
                      ObservationPostBody, ObservationDataArrayPostBody, ObservedPropertyListResponse,
                      ObservedPropertyGetResponse, SensorListResponse, SensorGetResponse)


hydroserver_extension = SensorThingsExtension(
    endpoint_hooks=[
        SensorThingsEndpointHookFactory(
            endpoint_name="list_datastreams",
            view_authentication=[
                session_auth,
                bearer_auth,
                apikey_auth,
                anonymous_auth,
            ],
            view_response_schema=DatastreamListResponse,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="get_datastream",
            view_authentication=[
                session_auth,
                bearer_auth,
                apikey_auth,
                anonymous_auth,
            ],
            view_response_schema=DatastreamGetResponse,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="create_datastream",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="update_datastream",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="delete_datastream",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="list_features_of_interest",
            view_authentication=[
                session_auth,
                bearer_auth,
                apikey_auth,
                anonymous_auth,
            ],
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="get_feature_of_interest",
            view_authentication=[
                session_auth,
                bearer_auth,
                apikey_auth,
                anonymous_auth,
            ],
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="create_feature_of_interest",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="update_feature_of_interest",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="delete_feature_of_interest",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="list_historical_locations",
            view_authentication=[
                session_auth,
                bearer_auth,
                apikey_auth,
                anonymous_auth,
            ],
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="get_historical_location",
            view_authentication=[
                session_auth,
                bearer_auth,
                apikey_auth,
                anonymous_auth,
            ],
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="create_historical_location",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="update_historical_location",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="delete_historical_location",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="list_locations",
            view_authentication=[
                session_auth,
                bearer_auth,
                apikey_auth,
                anonymous_auth,
            ],
            view_response_schema=LocationListResponse,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="get_location",
            view_authentication=[
                session_auth,
                bearer_auth,
                apikey_auth,
                anonymous_auth,
            ],
            view_response_schema=LocationGetResponse,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="create_location",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="update_location",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="delete_location",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="list_observations",
            view_authentication=[
                session_auth,
                bearer_auth,
                apikey_auth,
                anonymous_auth,
            ],
            view_response_schema=ObservationListResponse,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="get_observation",
            view_authentication=[
                session_auth,
                bearer_auth,
                apikey_auth,
                anonymous_auth,
            ],
            view_response_schema=ObservationGetResponse,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="create_observation",
            view_wrapper=transaction.atomic,
            view_authentication=[
                session_auth,
                bearer_auth,
                apikey_auth,
                anonymous_auth,
            ],
            view_body_schema=ObservationPostBody,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="create_observations",
            view_wrapper=transaction.atomic,
            view_authentication=[
                session_auth,
                bearer_auth,
                apikey_auth,
                anonymous_auth,
            ],
            view_body_schema=ObservationDataArrayPostBody,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="update_observation",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="delete_observation",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="list_observed_properties",
            view_authentication=[
                session_auth,
                bearer_auth,
                apikey_auth,
                anonymous_auth,
            ],
            view_response_schema=ObservedPropertyListResponse,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="get_observed_property",
            view_authentication=[
                session_auth,
                bearer_auth,
                apikey_auth,
                anonymous_auth,
            ],
            view_response_schema=ObservedPropertyGetResponse,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="create_observed_property",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="update_observed_property",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="delete_observed_property",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="list_sensors",
            view_authentication=[
                session_auth,
                bearer_auth,
                apikey_auth,
                anonymous_auth,
            ],
            view_response_schema=SensorListResponse,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="get_sensor",
            view_authentication=[
                session_auth,
                bearer_auth,
                apikey_auth,
                anonymous_auth,
            ],
            view_response_schema=SensorGetResponse,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="create_sensor",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="update_sensor",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="delete_sensor",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="list_things",
            view_authentication=[
                session_auth,
                bearer_auth,
                apikey_auth,
                anonymous_auth,
            ],
            view_response_schema=ThingListResponse,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="get_thing",
            view_authentication=[
                session_auth,
                bearer_auth,
                apikey_auth,
                anonymous_auth,
            ],
            view_response_schema=ThingGetResponse,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="create_thing",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="update_thing",
            enabled=False,
            view_authentication=lambda request: False,
        ),
        SensorThingsEndpointHookFactory(
            endpoint_name="delete_thing",
            enabled=False,
            view_authentication=lambda request: False,
        ),
    ],
)
