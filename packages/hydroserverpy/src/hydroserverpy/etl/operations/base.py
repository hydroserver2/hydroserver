import pandas as pd
from abc import ABC, abstractmethod
from pydantic import BaseModel


class DataOperation(BaseModel, ABC):
    target_identifier: str

    @abstractmethod
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply the operation to a DataFrame with the columns (timestamp, value).
        """
        ...
