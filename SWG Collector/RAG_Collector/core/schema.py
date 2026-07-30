from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class DatasetSource(str, Enum):
    SWEBENCH = "swebench"
    GITHUB_ISSUES = "github_issues"
    STACK_OVERFLOW = "stack_overflow"
    FASTAPI_DOCS = "fastapi_docs"
    PYTHON_EXCEPTIONS = "python_exceptions"
    SQLITE_ERRORS = "sqlite_errors"
    LM_STUDIO_LOGS = "lm_studio_logs"
    VOICEVOX_LOGS = "voicevox_logs"
    CUSTOM_JSON = "custom_json"
    CSV = "csv"
    PARQUET = "parquet"


@dataclass
class UnifiedDocument:
    id: str
    source: str
    repository: str = ""
    title: str = ""
    problem: str = ""
    solution: str = ""
    code: str = ""
    language: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "repository": self.repository,
            "title": self.title,
            "problem": self.problem,
            "solution": self.solution,
            "code": self.code,
            "language": self.language,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UnifiedDocument":
        return cls(
            id=data.get("id", ""),
            source=data.get("source", ""),
            repository=data.get("repository", ""),
            title=data.get("title", ""),
            problem=data.get("problem", ""),
            solution=data.get("solution", ""),
            code=data.get("code", ""),
            language=data.get("language", ""),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


REQUIRED_FIELDS = ["id", "source", "problem", "solution", "code", "language", "tags", "metadata"]
