import string
from typing import Any
from pydantic import BaseModel


class ETLComponent(BaseModel):
    """
    Base model for ETL components (Extractors, Transformers, and Loaders)
    """

    def render_runtime_data(self, **kwargs) -> dict[str, Any]:
        """
        Render all template fields in the model instance using the provided runtime variables.

        Fields marked with `json_schema_extra["template"] = True` will be treated as Python format
        strings. Fields marked with `json_schema_extra["overwrite"] = True` will be replaced by
        values from `kwargs` if provided. All other fields are included unchanged in the returned
        dictionary.
        """

        data = self.model_dump()
        runtime_data: dict[str, Any] = {}

        for name, field in self.model_fields.items():
            value = data.get(name)

            if field.json_schema_extra:
                can_overwrite = field.json_schema_extra.get("overwrite") is True
                is_template = field.json_schema_extra.get("template") is True
            else:
                can_overwrite = False
                is_template = False

            if can_overwrite and name in kwargs.keys():
                runtime_data[name] = kwargs[name]
                continue

            if not is_template or not isinstance(value, str):
                runtime_data[name] = value
                continue

            missing_variables = self.get_required_template_variables(value) - kwargs.keys()

            if missing_variables:
                raise ValueError(
                    f"Missing required runtime variables needed to render field "
                    f"'{name}' with template '{value}': "
                    f"{', '.join(sorted(missing_variables))}"
                )

            try:
                runtime_data[name] = value.format(**kwargs)
            except Exception as e:
                raise ValueError(
                    f"Failed to render template field '{name}' from template '{value}'. "
                    f"Ensure the template field is correctly formatted."
                ) from e

        return runtime_data

    @property
    def required_runtime_variables(self) -> set[str]:
        """
        The set of runtime variables required to render all template fields.
        """

        required_variables: set[str] = set()

        for name, field in self.model_fields.items():
            is_template = (
                field.json_schema_extra.get("template") is True
                if field.json_schema_extra
                else False
            )
            value = getattr(self, name)

            if is_template and isinstance(value, str):
                required_variables |= self.get_required_template_variables(value)

        return required_variables

    @staticmethod
    def get_required_template_variables(template: str) -> set[str]:
        """
        Determine the set of variable names required to render a template string.
        """

        formatter = string.Formatter()

        return {
            field_name.split(".", 1)[0].split("[", 1)[0]
            for _, field_name, _, _ in formatter.parse(template)
            if field_name is not None
        }
