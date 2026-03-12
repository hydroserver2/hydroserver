from abc import ABC, abstractmethod
from io import BytesIO
from typing import Union, TextIO
from ..models import ETLComponent


class Extractor(ETLComponent, ABC):
    @abstractmethod
    def extract(
        self,
        **kwargs
    ) -> Union[str, TextIO, BytesIO]:
        ...
