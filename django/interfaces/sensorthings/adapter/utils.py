from django.core.exceptions import FieldError
from django.db.models import F, Window
from django.db.models.functions import RowNumber
from ninja.errors import HttpError
from odata_query.django.django_q import AstToDjangoQVisitor
from sensorthings.types import Absent, OrderByDirection
from core.sta import models as sta_models


class SensorThingsUtils:

    @staticmethod
    def select_field(select, field, value, cast=None):
        if select is not None and field not in select:
            return Absent
        return cast(value) if cast else value

    @staticmethod
    def iso_time_interval(begin, end):
        if begin is None or end is None or end <= begin:
            return None
        return f"{begin.isoformat()}/{end.isoformat()}"

    def transform_model_field(self, component, prop):
        if component.__name__ == "Thing":
            return {
                "properties__samplingFeatureType": "sampling_feature_type",
                "properties__samplingFeatureCode": "sampling_feature_code",
                "properties__siteType": "site_type",
                "properties__dataDisclaimer": "data_disclaimer",
                "properties__isPrivate": "is_private",
                "properties__workspace__id": "workspace_id",
                "properties__workspace__name": "workspace__name",
                "properties__workspace__isPrivate": "workspace__is_private",
                "Location__id": "locations__id",
            }.get(prop, prop)

        elif component.__name__ == "Location":
            return {
                "properties__workspace__id": "thing__workspace_id",
                "properties__workspace__name": "thing__workspace__name",
                "properties__workspace__isPrivate": "thing__workspace__is_private",
                "Thing__id": "thing_id",
            }.get(prop, f"location__{prop}")

        elif component.__name__ == "HistoricalLocation":
            return prop

        elif component.__name__ == "Sensor":
            return {
                "encodingType": "encoding_type",
                "properties__workspace__id": "workspace_id",
                "properties__workspace__name": "workspace__name",
                "properties__workspace__isPrivate": "workspace__is_private",
                "metadata__methodCode": "method_code",
                "metadata__methodType": "method_type",
                "metadata__methodLink": "method_link",
                "metadata__sensorModel__sensorModelName": "model",
                "metadata__sensorModel__sensorModelUrl": "model_link",
                "metadata__sensorModel__sensorManufacturer": "manufacturer",
            }.get(prop, prop)

        elif component.__name__ == "ObservedProperty":
            return {
                "properties__variableCode": "code",
                "properties__variableType": "type",
                "properties__workspace__id": "workspace_id",
                "properties__workspace__name": "workspace__name",
                "properties__workspace__isPrivate": "workspace__is_private",
            }.get(prop, prop)

        elif component.__name__ == "Datastream":
            related = {
                "Thing": "thing",
                "Sensor": "sensor",
                "ObservedProperty": "observed_property",
            }
            parent = prop.split("__")[0]
            if parent in related:
                return (
                    related[parent]
                    + "__"
                    + self.transform_model_field(
                        component=getattr(sta_models, parent),
                        prop="__".join(prop.split("__")[1:]),
                    )
                )
            return {
                "unitOfMeasurement__name": "unit__name",
                "unitOfMeasurement__symbol": "unit__symbol",
                "unitOfMeasurement__definition": "unit__definition",
                "observationType": "observation_type",
                "observedArea": "observed_area",
                "properties__workspace__id": "thing__workspace_id",
                "properties__workspace__name": "thing__workspace__name",
                "properties__workspace__isPrivate": "thing__workspace__is_private",
                "properties__resultType": "result_type",
                "properties__status": "status",
                "properties__sampledMedium": "sampled_medium",
                "properties__valueCount": "value_count",
                "properties__noDataValue": "no_data_value",
                "properties__processingLevelCode": "processing_level__code",
                "properties__intendedTimeSpacing": "intended_time_spacing",
                "properties__intendedTimeSpacingUnitOfMeasurement": "intended_time_spacing_unit",
                "properties__aggregationStatistic": "aggregation_statistic",
                "properties__timeAggregationInterval": "time_aggregation_interval",
                "properties__timeAggregationIntervalUnitOfMeasurement": "time_aggregation_interval_unit",
            }.get(prop, prop)

        elif component.__name__ == "FeatureOfInterest":
            return prop

        elif component.__name__ == "Observation":
            related = {
                "Datastream": "datastream",
                "FeatureOfInterest": "feature_of_interest",
            }
            parent = prop.split("__")[0]
            if parent in related:
                return (
                    related[parent]
                    + "__"
                    + self.transform_model_field(
                        component=getattr(sta_models, parent),
                        prop="__".join(prop.split("__")[1:]),
                    )
                )
            return {
                "phenomenonTime": "phenomenon_time",
                "resultTime": "result_time",
            }.get(prop, prop)

    def apply_filters(self, queryset, component, filters):
        visitor = AstToDjangoQVisitor(component)
        query_filter = visitor.visit(filters)

        for prop in list(query_filter.flatten()):
            if isinstance(prop, F):
                model_field = self.transform_model_field(component, prop.name)
                prop.__dict__ = {
                    "_constructor_args": ((model_field,), {}),
                    "name": model_field,
                }
        try:
            return queryset.filter(query_filter)
        except FieldError:
            raise HttpError(422, "Failed to parse filter parameter.")

    def apply_order(self, queryset, component, orderby):
        if not orderby:
            return queryset

        order_exprs = []
        for field in orderby:
            prop = "__".join(field.path)
            model_field = self.transform_model_field(component, prop)
            prefix = "-" if field.direction == OrderByDirection.DESC else ""
            order_exprs.append(f"{prefix}{model_field}")

        return queryset.order_by(*order_exprs)

    @staticmethod
    def apply_pagination(queryset, top=100, skip=0):
        top = max(0, int(top))
        skip = max(0, int(skip))
        return queryset[skip:skip + top]

    @staticmethod
    def apply_window(queryset, partition_field, top=100, skip=0):
        top = max(0, int(top))
        skip = max(0, int(skip))
        return queryset.annotate(
            rn=Window(
                expression=RowNumber(),
                partition_by=[F(partition_field)],
                order_by=queryset.query.order_by or ["id"],
            )
        ).filter(rn__gt=skip, rn__lte=skip + top)
