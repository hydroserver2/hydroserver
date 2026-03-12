from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from typing import Optional, Any
from ..extractors import Extractor
from ..transformers import Transformer, ETLDataMapping
from ..loaders import Loader, ETLLoaderResult


class ETLStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    INCOMPLETE = "INCOMPLETE"


class ETLStage(Enum):
    SETUP = "SETUP"
    EXTRACT = "EXTRACT"
    TRANSFORM = "TRANSFORM"
    LOAD = "LOAD"


class ETLContext(BaseModel):
    status: ETLStatus = ETLStatus.PENDING
    stage: ETLStage = ETLStage.SETUP
    runtime_variables: dict[str, Any] = Field(default_factory=dict)
    results: Optional[ETLLoaderResult] = None
    exception: Optional[Exception] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def mark_failed(self, exc: Exception) -> None:
        """
        Mark the ETL run as failed due to the given exception.
        """

        self.status = ETLStatus.FAILED
        self.exception = exc


class ETLPipeline(BaseModel):
    extractor: Extractor
    transformer: Transformer
    loader: Loader

    def run(
        self,
        data_mappings: list[ETLDataMapping],
        raise_on_error: bool = True,
        **kwargs
    ) -> ETLContext:
        """
        Execute the ETL pipeline across extract, transform, and load stages.

        If raise_on_error is True, the first exception raised by any stage
        will be propagated to the caller. If raise_on_error is False, the
        ETLContext will be marked as failed and returned.
        """

        context = ETLContext()

        context.status = ETLStatus.RUNNING

        try:
            context.runtime_variables["extractor"] = self.extractor.render_runtime_data(
                **kwargs
            )
            context.runtime_variables["transformer"] = self.transformer.render_runtime_data(
                **kwargs
            )
            context.runtime_variables["loader"] = self.loader.render_runtime_data(
                **kwargs
            )
        except Exception as e:
            if raise_on_error:
                raise
            context.mark_failed(e)
            return context

        context.stage = ETLStage.EXTRACT

        try:
            extracted_payload = self.extractor.extract(**kwargs)
        except Exception as e:
            if raise_on_error:
                raise
            context.mark_failed(e)
            return context

        context.stage = ETLStage.TRANSFORM

        try:
            transformed_payload = self.transformer.transform(
                payload=extracted_payload,
                data_mappings=data_mappings,
                **kwargs
            )
        except Exception as e:
            if raise_on_error:
                raise
            context.mark_failed(e)
            return context

        context.stage = ETLStage.LOAD

        try:
            context.results = self.loader.load(
                payload=transformed_payload,
                **kwargs
            )
        except Exception as e:
            if raise_on_error:
                raise
            context.mark_failed(e)
            return context

        if context.results.failure_count == 0:
            context.status = ETLStatus.SUCCESS
        else:
            context.status = ETLStatus.INCOMPLETE

        return context
