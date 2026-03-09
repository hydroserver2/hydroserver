import re
import ast
import logging
import pandas as pd
from pydantic import model_validator
from typing import Any
from .base import DataOperation
from ..exceptions import ETLError


logger = logging.getLogger(__name__)


ALLOWED_AST = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.UAdd,
    ast.USub,
    ast.Name,
    ast.Load,
    ast.Constant,
)


class ArithmeticExpressionOperation(DataOperation):
    expression: str
    _compiled: Any = None

    @model_validator(mode="after")
    def compile_expression(self) -> "ArithmeticExpressionOperation":
        """
        Validate and compile the expression on initialization.
        Whitespace is canonicalized before compilation.
        """

        canonical = re.sub(r"\s+", "", self.expression)

        try:
            tree = ast.parse(canonical, mode="eval")
        except (ValueError, AssertionError) as e:
            raise ValueError(
                f"Failed to compile arithmetic expression for data target: {self.target_identifier}. "
                f"Failing expression: {self.expression}. "
                f"{str(e)}"
            )
        except Exception:
            raise ValueError(
                f"Failed to compile arithmetic expression for data target: {self.target_identifier}. "
                f"Failing expression: {self.expression}. "
                f"Encountered an unexpected error."
            )

        for node in ast.walk(tree):
            if not isinstance(node, ALLOWED_AST):
                raise ValueError(
                    f"Failed to compile arithmetic expression for data target: {self.target_identifier}. "
                    f"Failing expression: {self.expression}. "
                    "Only +, -, *, / with 'x' and numeric literals are allowed in arithmetic expressions."
                )
            if isinstance(node, ast.Name) and node.id != "x":
                raise ValueError(
                    f"Failed to compile arithmetic expression for data target: {self.target_identifier}. "
                    f"Failing expression: {self.expression}. "
                    "Only the variable 'x' is allowed in arithmetic expressions. "
                    f"Provided variable: {node.id}"
                )
            if isinstance(node, ast.Constant):
                val = node.value
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    raise ValueError(
                        f"Failed to compile arithmetic expression for data target: {self.target_identifier}. "
                        f"Failing expression: {self.expression}. "
                        "Only numeric literals are allowed in arithmetic expressions. "
                        f"Provided value: {val}"
                    )

        self._compiled = compile(tree, "<expr>", "eval")
        return self

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply the compiled arithmetic expression to the value column of a
        (timestamp, value) DataFrame.

        The variable 'x' in the expression represents the value column.
        The timestamp column is passed through unchanged.
        """

        try:
            result = df.copy()
            result["value"] = eval(self._compiled, {"__builtins__": {}}, {"x": df["value"]})
            return result
        except Exception as e:
            raise ETLError(
                f"Failed to evaluate arithmetic expression for data target: {self.target_identifier}. "
                f"Failing expression: {self.expression}"
            ) from e
