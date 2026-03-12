import pytest
from pydantic import Field
from hydroserverpy.etl.models.base import ETLComponent


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

def _make_component(**field_definitions):
    """
    Dynamically create a concrete ETLComponent subclass with the given fields.
    field_definitions maps field_name -> (default, Field(...)) or just a default value.
    """

    annotations = {}
    defaults = {}

    for name, spec in field_definitions.items():
        if isinstance(spec, tuple):
            annotation, field = spec
            annotations[name] = annotation
            defaults[name] = field
        else:
            annotations[name] = type(spec)
            defaults[name] = spec

    cls = type("ConcreteComponent", (ETLComponent,), {"__annotations__": annotations, **defaults})
    return cls


# ---------------------------------------------------------------------------
# render_runtime_data – plain fields
# ---------------------------------------------------------------------------

class TestRenderRuntimeDataPlainFields:

    def test_plain_field_is_included_unchanged(self):
        cls = _make_component(name=("str", Field(default="value")))
        result = cls(name="hello").render_runtime_data()
        assert result["name"] == "hello"

    def test_all_plain_fields_are_included(self):
        cls = _make_component(
            a=("str", Field(default="x")),
            b=("int", Field(default=0)),
        )
        result = cls(a="foo", b=42).render_runtime_data()
        assert result["a"] == "foo"
        assert result["b"] == 42

    def test_extra_kwargs_are_ignored_for_plain_fields(self):
        cls = _make_component(name=("str", Field(default="value")))
        result = cls(name="hello").render_runtime_data(unused="ignored")
        assert result["name"] == "hello"


# ---------------------------------------------------------------------------
# render_runtime_data – template fields
# ---------------------------------------------------------------------------

class TestRenderRuntimeDataTemplateFields:

    def test_template_field_is_rendered_with_kwargs(self):
        cls = _make_component(
            uri=("str", Field(default="https://example.com/{path}",
                              json_schema_extra={"template": True}))
        )
        result = cls(uri="https://example.com/{path}").render_runtime_data(path="data/file.csv")
        assert result["uri"] == "https://example.com/data/file.csv"

    def test_template_with_multiple_variables(self):
        cls = _make_component(
            uri=("str", Field(default="https://{host}/{path}",
                              json_schema_extra={"template": True}))
        )
        result = cls(uri="https://{host}/{path}").render_runtime_data(host="example.com", path="data")
        assert result["uri"] == "https://example.com/data"

    def test_missing_template_variable_raises_value_error(self):
        cls = _make_component(
            uri=("str", Field(default="https://example.com/{path}",
                              json_schema_extra={"template": True}))
        )
        with pytest.raises(ValueError, match="Missing required runtime variables"):
            cls(uri="https://example.com/{path}").render_runtime_data()

    def test_missing_template_variable_error_includes_variable_name(self):
        cls = _make_component(
            uri=("str", Field(default="https://example.com/{path}",
                              json_schema_extra={"template": True}))
        )
        with pytest.raises(ValueError, match="path"):
            cls(uri="https://example.com/{path}").render_runtime_data()

    def test_missing_template_variable_error_includes_field_name(self):
        cls = _make_component(
            uri=("str", Field(default="https://example.com/{path}",
                              json_schema_extra={"template": True}))
        )
        with pytest.raises(ValueError, match="uri"):
            cls(uri="https://example.com/{path}").render_runtime_data()

    def test_extra_kwargs_do_not_affect_template_rendering(self):
        cls = _make_component(
            uri=("str", Field(default="https://example.com/{path}",
                              json_schema_extra={"template": True}))
        )
        result = cls(uri="https://example.com/{path}").render_runtime_data(path="data", extra="ignored")
        assert result["uri"] == "https://example.com/data"

    def test_non_string_template_field_is_included_unchanged(self):
        """A template-marked field with a non-string value is passed through as-is."""
        cls = _make_component(
            count=("int", Field(default=0, json_schema_extra={"template": True}))
        )
        result = cls(count=5).render_runtime_data()
        assert result["count"] == 5


# ---------------------------------------------------------------------------
# render_runtime_data – overwrite fields
# ---------------------------------------------------------------------------

class TestRenderRuntimeDataOverwriteFields:

    def test_overwrite_field_is_replaced_by_kwarg(self):
        cls = _make_component(
            name=("str", Field(default="original", json_schema_extra={"overwrite": True}))
        )
        result = cls(name="original").render_runtime_data(name="replaced")
        assert result["name"] == "replaced"

    def test_overwrite_field_uses_stored_value_when_kwarg_absent(self):
        cls = _make_component(
            name=("str", Field(default="original", json_schema_extra={"overwrite": True}))
        )
        result = cls(name="original").render_runtime_data()
        assert result["name"] == "original"

    def test_overwrite_takes_precedence_over_template(self):
        """A field marked both overwrite and template should be overwritten, not rendered."""
        cls = _make_component(
            uri=("str", Field(default="https://example.com/{path}",
                              json_schema_extra={"overwrite": True, "template": True}))
        )
        result = cls(uri="https://example.com/{path}").render_runtime_data(
            uri="https://other.com/file.csv"
        )
        assert result["uri"] == "https://other.com/file.csv"


# ---------------------------------------------------------------------------
# required_runtime_variables
# ---------------------------------------------------------------------------

class TestRequiredRuntimeVariables:

    def test_returns_empty_set_for_no_template_fields(self):
        cls = _make_component(name=("str", Field(default="value")))
        assert cls(name="hello").required_runtime_variables == set()

    def test_returns_variable_names_from_template_field(self):
        cls = _make_component(
            uri=("str", Field(default="https://example.com/{path}",
                              json_schema_extra={"template": True}))
        )
        assert cls(uri="https://example.com/{path}").required_runtime_variables == {"path"}

    def test_returns_all_variables_from_multiple_template_fields(self):
        cls = _make_component(
            uri=("str", Field(default="https://{host}/{path}",
                              json_schema_extra={"template": True})),
            label=("str", Field(default="{name}",
                                json_schema_extra={"template": True})),
        )
        result = cls(uri="https://{host}/{path}", label="{name}").required_runtime_variables
        assert result == {"host", "path", "name"}

    def test_deduplicates_variables_used_in_multiple_fields(self):
        cls = _make_component(
            a=("str", Field(default="{var}", json_schema_extra={"template": True})),
            b=("str", Field(default="{var}", json_schema_extra={"template": True})),
        )
        result = cls(a="{var}", b="{var}").required_runtime_variables
        assert result == {"var"}

    def test_does_not_raise_for_fields_without_json_schema_extra(self):
        cls = _make_component(name=("str", Field(default="value")))
        result = cls(name="hello").required_runtime_variables
        assert result == set()


# ---------------------------------------------------------------------------
# get_required_template_variables
# ---------------------------------------------------------------------------

class TestGetRequiredTemplateVariables:

    def test_returns_single_variable(self):
        result = ETLComponent.get_required_template_variables("hello {name}")
        assert result == {"name"}

    def test_returns_multiple_variables(self):
        result = ETLComponent.get_required_template_variables("{host}/{path}")
        assert result == {"host", "path"}

    def test_returns_empty_set_for_no_variables(self):
        result = ETLComponent.get_required_template_variables("no variables here")
        assert result == set()

    def test_deduplicates_repeated_variables(self):
        result = ETLComponent.get_required_template_variables("{x} and {x}")
        assert result == {"x"}

    def test_strips_attribute_access(self):
        result = ETLComponent.get_required_template_variables("{obj.attr}")
        assert result == {"obj"}

    def test_strips_index_access(self):
        result = ETLComponent.get_required_template_variables("{obj[0]}")
        assert result == {"obj"}

    def test_returns_empty_set_for_empty_string(self):
        result = ETLComponent.get_required_template_variables("")
        assert result == set()
