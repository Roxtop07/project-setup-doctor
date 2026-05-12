from __future__ import annotations

from abc import ABC, abstractmethod

from models.contracts import Issue, ProjectInfo


class BaseAnalyzer(ABC):
    name: str = "base"

    @abstractmethod
    async def analyze(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        ...
