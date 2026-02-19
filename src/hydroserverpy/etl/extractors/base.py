from abc import abstractmethod
import logging
import pandas as pd
from datetime import datetime
from ..etl_configuration import ExtractorConfig, Task
from ..timestamp_parser import TimestampParser
from ..logging_utils import summarize_list


logger = logging.getLogger(__name__)


class Extractor:
    def __init__(self, extractor_config: ExtractorConfig):
        self.cfg = extractor_config
        self.runtime_source_uri = None

    def resolve_placeholder_variables(self, task: Task, loader):
        placeholders = list(self.cfg.placeholder_variables or [])
        filled = {}
        runtime_names: set[str] = set()
        task_names: set[str] = set()
        for placeholder in placeholders:
            name = placeholder.name

            if placeholder.type == "runTime":
                logger.debug("Resolving runtime var: %s", name)
                runtime_names.add(name)
                if placeholder.run_time_value == "latestObservationTimestamp":
                    value = loader.earliest_begin_date(task)
                elif placeholder.run_time_value == "jobExecutionTime":
                    value = pd.Timestamp.now(tz="UTC")
            elif placeholder.type == "perTask":
                logger.debug("Resolving task var: %s", name)
                task_names.add(name)
                if name not in task.extractor_variables:
                    logger.error(
                        "Missing per-task extractor variable '%s'. Provided extractorVariables keys=%s",
                        name,
                        summarize_list(sorted((task.extractor_variables or {}).keys())),
                    )
                    raise ValueError(
                        f"Missing required per-task extractor variable '{name}'."
                    )
                value = task.extractor_variables[name]
            else:
                continue

            if isinstance(value, (datetime, pd.Timestamp)):
                parser = TimestampParser(placeholder.timestamp)
                value = parser.utc_to_string(value)

            filled[name] = value

        if runtime_names:
            names = ", ".join(sorted(runtime_names))
            logger.debug(
                "Runtime variables resolved (%s): %s", len(runtime_names), names
            )
        if task_names:
            names = ", ".join(sorted(task_names))
            logger.debug("Task variables resolved (%s): %s", len(task_names), names)

        if not filled:
            uri = self.cfg.source_uri
        else:
            uri = self.format_uri(filled)

        self.runtime_source_uri = uri
        # Keep a stable log prefix for downstream parsing.
        logger.info("Resolved runtime source URI: %s", uri)
        return uri

    def format_uri(self, placeholder_variables):
        try:
            uri = self.cfg.source_uri.format(**placeholder_variables)
        except KeyError as e:
            missing_key = e.args[0]
            logger.error(
                "Failed to format sourceUri: missing placeholder '%s'. Provided placeholders=%s",
                missing_key,
                summarize_list(sorted(placeholder_variables.keys())),
            )
            raise ValueError(
                f"Extractor source URI contains a placeholder '{missing_key}', but it was not provided."
            )
        return uri

    @abstractmethod
    def extract(self):
        pass
