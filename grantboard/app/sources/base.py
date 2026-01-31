from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ..models import SourceResult


class SourceAdapter(ABC):
    name: str

    @abstractmethod
    def fetch(self) -> List[SourceResult]:
        raise NotImplementedError
