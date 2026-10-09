from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class Tool(ABC, Generic[T]):
    """Application-level tool contract used by agents and workflow executors."""

    name: str

    @abstractmethod
    async def execute(self, **kwargs) -> T:
        raise NotImplementedError
