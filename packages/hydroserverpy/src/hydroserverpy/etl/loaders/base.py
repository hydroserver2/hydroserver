import pandas as pd
from abc import ABC, abstractmethod
from typing import Union, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from collections import Counter
from ..models import ETLComponent


class ETLTargetResult(BaseModel):
    target_identifier: Union[str, int]
    status: Optional[Literal["success", "failed", "skipped"]] = None
    values_loaded: int = 0
    earliest_timestamp: Optional[datetime] = None
    latest_timestamp: Optional[datetime] = None
    error: Optional[str] = None
    traceback: Optional[str] = None


class ETLLoaderResult(BaseModel):
    success_count: int = 0
    failure_count: int = 0
    skipped_count: int = 0
    values_loaded_total: int = 0
    earliest_timestamp: Optional[datetime] = None
    latest_timestamp: Optional[datetime] = None
    target_results: dict[Union[str, int], ETLTargetResult] = Field(default_factory=dict)

    def aggregate_results(self) -> None:
        """
        Aggregate per-target ETL results into summary fields on the loader result.
        """

        status_counts = Counter()
        values_loaded_total = 0

        for target_result in self.target_results.values():
            status_counts[target_result.status] += 1
            values_loaded_total += target_result.values_loaded or 0

            if target_result.earliest_timestamp is not None:
                if self.earliest_timestamp is None:
                    self.earliest_timestamp = target_result.earliest_timestamp
                else:
                    self.earliest_timestamp = min(
                        self.earliest_timestamp,
                        target_result.earliest_timestamp,
                    )

            if target_result.latest_timestamp is not None:
                if self.latest_timestamp is None:
                    self.latest_timestamp = target_result.latest_timestamp
                else:
                    self.latest_timestamp = max(
                        self.latest_timestamp,
                        target_result.latest_timestamp,
                    )

        self.success_count = status_counts.get("success", 0)
        self.skipped_count = status_counts.get("skipped", 0)
        self.failure_count = status_counts.get("failed", 0)
        self.values_loaded_total = values_loaded_total


class Loader(ETLComponent, ABC):

    @abstractmethod
    def load(
        self,
        payload: pd.DataFrame,
        **kwargs
    ) -> ETLLoaderResult:
        ...

    @abstractmethod
    def target_loaded_through(
        self,
        target_identifier: Union[str, int]
    ) -> Optional[datetime]:
        ...

    def earliest_loaded_through(
        self,
        target_identifiers: list[Union[str, int]],
    ) -> Optional[datetime]:
        """
        Return the earliest 'loaded through' timestamp across all given target
        identifiers, or None if no targets have been loaded yet.

        Calls target_loaded_through for each target identifier and returns the
        minimum non-None result. This represents the furthest back in time the
        pipeline must re-fetch source data to ensure all targets are up-to-date.
        """

        timestamps = [
            timestamp for target_identifier in target_identifiers
            if (timestamp := self.target_loaded_through(target_identifier=target_identifier)) is not None
        ]

        return min(timestamps) if timestamps else None
