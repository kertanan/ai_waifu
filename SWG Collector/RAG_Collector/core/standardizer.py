import hashlib
import json
from typing import Any, Callable, Dict, List, Optional, Union

from datasets import Dataset, DatasetDict

from .schema import UnifiedDocument, DatasetSource


SOURCE_MAPPINGS = {
    DatasetSource.SWEBENCH: {
        "id": "instance_id",
        "repository": "repo",
        "problem": "problem_statement",
        "solution": "patch",
        "metadata.hints": "hints_text",
    },
    DatasetSource.GITHUB_ISSUES: {
        "id": "id",
        "title": "title",
        "problem": "body",
        "metadata.comments": "comments",
        "tags": "labels",
    },
    DatasetSource.STACK_OVERFLOW: {
        "problem": "question",
        "solution": "accepted_answer",
        "tags": "tags",
    },
    DatasetSource.PYTHON_EXCEPTIONS: {
        "problem": "error",
        "solution": "explanation",
        "code": "example",
    },
    DatasetSource.SQLITE_ERRORS: {
        "problem": "error",
        "solution": "solution",
        "code": "query",
    },
    DatasetSource.FASTAPI_DOCS: {
        "title": "title",
        "problem": "description",
        "solution": "content",
        "code": "code_example",
    },
}


def _generate_id(source: str, data: Dict[str, Any], index: int) -> str:
    raw = f"{source}-{json.dumps(data, sort_keys=True, default=str)}-{index}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _extract_nested_value(data: Dict[str, Any], key_path: str) -> Any:
    keys = key_path.split(".")
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current


def _set_nested_value(data: Dict[str, Any], key_path: str, value: Any):
    keys = key_path.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def standardize_swebench(
    row: Dict[str, Any],
    index: int,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> UnifiedDocument:
    metadata = {}
    hints = _extract_nested_value(row, "hints_text")
    if hints:
        metadata["hints"] = hints

    repo = row.get("repo", "")
    if repo:
        parts = repo.split("/")
        if len(parts) >= 2:
            metadata["framework"] = parts[1].lower()

    if extra_metadata:
        metadata.update(extra_metadata)

    return UnifiedDocument(
        id=row.get("instance_id", _generate_id("swebench", row, index)),
        source=DatasetSource.SWEBENCH.value,
        repository=repo,
        title=row.get("instance_id", ""),
        problem=row.get("problem_statement", ""),
        solution=row.get("patch", ""),
        code=row.get("base_commit", ""),
        language="python",
        tags=[repo.split("/")[-1].lower()] if repo else [],
        metadata=metadata,
    )


def standardize_github_issues(
    row: Dict[str, Any],
    index: int,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> UnifiedDocument:
    metadata = {}
    comments = row.get("comments", [])
    if comments:
        metadata["comments"] = comments

    labels = row.get("labels", [])
    if isinstance(labels, list):
        tags = [label.get("name", str(label)) if isinstance(label, dict) else str(label) for label in labels]
    else:
        tags = [str(labels)] if labels else []

    if extra_metadata:
        metadata.update(extra_metadata)

    title = row.get("title", "")
    body = row.get("body", "")

    return UnifiedDocument(
        id=str(row.get("id", _generate_id("github", row, index))),
        source=DatasetSource.GITHUB_ISSUES.value,
        repository=row.get("repository", row.get("repo", "")),
        title=title,
        problem=body,
        solution="",
        code="",
        language=row.get("language", ""),
        tags=tags,
        metadata=metadata,
    )


def standardize_stackoverflow(
    row: Dict[str, Any],
    index: int,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> UnifiedDocument:
    tags = row.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]

    metadata = {}
    if extra_metadata:
        metadata.update(extra_metadata)

    return UnifiedDocument(
        id=str(row.get("id", _generate_id("stackoverflow", row, index))),
        source=DatasetSource.STACK_OVERFLOW.value,
        repository="",
        title=row.get("title", ""),
        problem=row.get("question", row.get("title", "")),
        solution=row.get("accepted_answer", ""),
        code=row.get("code", ""),
        language=row.get("language", ""),
        tags=tags,
        metadata=metadata,
    )


def standardize_python_exceptions(
    row: Dict[str, Any],
    index: int,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> UnifiedDocument:
    error = row.get("error", "")
    tags = []
    if error:
        exception_type = error.split(":")[0].strip() if ":" in error else error
        tags.append(exception_type)

    metadata = {}
    if extra_metadata:
        metadata.update(extra_metadata)

    return UnifiedDocument(
        id=str(row.get("id", _generate_id("python_exceptions", row, index))),
        source=DatasetSource.PYTHON_EXCEPTIONS.value,
        repository="",
        title=error[:100] if error else "",
        problem=error,
        solution=row.get("explanation", ""),
        code=row.get("example", ""),
        language="python",
        tags=tags,
        metadata=metadata,
    )


def standardize_sqlite_errors(
    row: Dict[str, Any],
    index: int,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> UnifiedDocument:
    error = row.get("error", "")
    tags = ["sqlite"]
    if "constraint" in error.lower():
        tags.append("constraint")
    if "syntax" in error.lower():
        tags.append("syntax")

    metadata = {}
    if extra_metadata:
        metadata.update(extra_metadata)

    return UnifiedDocument(
        id=str(row.get("id", _generate_id("sqlite_errors", row, index))),
        source=DatasetSource.SQLITE_ERRORS.value,
        repository="",
        title=error[:100] if error else "",
        problem=error,
        solution=row.get("solution", ""),
        code=row.get("query", ""),
        language="sql",
        tags=tags,
        metadata=metadata,
    )


def standardize_fastapi_docs(
    row: Dict[str, Any],
    index: int,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> UnifiedDocument:
    tags = row.get("tags", ["fastapi"])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]

    metadata = {}
    if extra_metadata:
        metadata.update(extra_metadata)

    return UnifiedDocument(
        id=str(row.get("id", _generate_id("fastapi_docs", row, index))),
        source=DatasetSource.FASTAPI_DOCS.value,
        repository="tiangolo/fastapi",
        title=row.get("title", ""),
        problem=row.get("description", ""),
        solution=row.get("content", ""),
        code=row.get("code_example", ""),
        language="python",
        tags=tags,
        metadata=metadata,
    )


def standardize_lmstudio_logs(
    row: Dict[str, Any],
    index: int,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> UnifiedDocument:
    metadata = {"raw": row}
    if extra_metadata:
        metadata.update(extra_metadata)

    return UnifiedDocument(
        id=str(row.get("id", _generate_id("lm_studio_logs", row, index))),
        source=DatasetSource.LM_STUDIO_LOGS.value,
        repository="",
        title=row.get("title", ""),
        problem=row.get("problem", row.get("input", "")),
        solution=row.get("solution", row.get("output", "")),
        code=row.get("code", ""),
        language=row.get("language", ""),
        tags=row.get("tags", []),
        metadata=metadata,
    )


def standardize_voicevox_logs(
    row: Dict[str, Any],
    index: int,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> UnifiedDocument:
    metadata = {"raw": row}
    if extra_metadata:
        metadata.update(extra_metadata)

    return UnifiedDocument(
        id=str(row.get("id", _generate_id("voicevox_logs", row, index))),
        source=DatasetSource.VOICEVOX_LOGS.value,
        repository="",
        title=row.get("title", ""),
        problem=row.get("problem", row.get("input", "")),
        solution=row.get("solution", row.get("output", "")),
        code=row.get("code", ""),
        language=row.get("language", ""),
        tags=row.get("tags", []),
        metadata=metadata,
    )


STANDARDIZERS: Dict[str, Callable] = {
    DatasetSource.SWEBENCH.value: standardize_swebench,
    DatasetSource.GITHUB_ISSUES.value: standardize_github_issues,
    DatasetSource.STACK_OVERFLOW.value: standardize_stackoverflow,
    DatasetSource.PYTHON_EXCEPTIONS.value: standardize_python_exceptions,
    DatasetSource.SQLITE_ERRORS.value: standardize_sqlite_errors,
    DatasetSource.FASTAPI_DOCS.value: standardize_fastapi_docs,
    DatasetSource.LM_STUDIO_LOGS.value: standardize_lmstudio_logs,
    DatasetSource.VOICEVOX_LOGS.value: standardize_voicevox_logs,
}


def standardize_custom(
    row: Dict[str, Any],
    source: str,
    index: int,
    field_mapping: Optional[Dict[str, str]] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> UnifiedDocument:
    metadata = {}
    if extra_metadata:
        metadata.update(extra_metadata)

    title = ""
    problem = ""
    solution = ""
    code = ""
    language = ""
    tags = []
    repository = ""

    if field_mapping:
        title = str(_extract_nested_value(row, field_mapping.get("title", "")) or "")
        problem = str(_extract_nested_value(row, field_mapping.get("problem", "")) or "")
        solution = str(_extract_nested_value(row, field_mapping.get("solution", "")) or "")
        code = str(_extract_nested_value(row, field_mapping.get("code", "")) or "")
        language = str(_extract_nested_value(row, field_mapping.get("language", "")) or "")
        repository = str(_extract_nested_value(row, field_mapping.get("repository", "")) or "")
        raw_tags = _extract_nested_value(row, field_mapping.get("tags", ""))
        if isinstance(raw_tags, list):
            tags = [str(t) for t in raw_tags]
        elif isinstance(raw_tags, str):
            tags = [t.strip() for t in raw_tags.split(",")]
    else:
        title = str(row.get("title", row.get("name", "")))
        problem = str(row.get("problem", row.get("description", row.get("body", row.get("text", "")))))
        solution = str(row.get("solution", row.get("answer", row.get("patch", ""))))
        code = str(row.get("code", ""))
        language = str(row.get("language", ""))
        repository = str(row.get("repository", row.get("repo", "")))
        raw_tags = row.get("tags", row.get("labels", []))
        if isinstance(raw_tags, list):
            tags = [str(t) for t in raw_tags]
        elif isinstance(raw_tags, str):
            tags = [t.strip() for t in raw_tags.split(",")]

    return UnifiedDocument(
        id=str(row.get("id", _generate_id(source, row, index))),
        source=source,
        repository=repository,
        title=title,
        problem=problem,
        solution=solution,
        code=code,
        language=language,
        tags=tags,
        metadata=metadata,
    )


def standardize_dataset(
    dataset: Union[Dataset, DatasetDict],
    source: str,
    field_mapping: Optional[Dict[str, str]] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    standardizer = STANDARDIZERS.get(source)

    def process_row(example, index):
        row = {k: v for k, v in example.items()}
        if standardizer:
            doc = standardizer(row, index, extra_metadata)
        else:
            doc = standardize_custom(row, source, index, field_mapping, extra_metadata)
        return doc.to_dict()

    if isinstance(dataset, Dataset):
        results = []
        for i, example in enumerate(dataset):
            results.append(process_row(example, i))
        return results

    elif isinstance(dataset, DatasetDict):
        results = []
        global_index = 0
        for split_name, split_dataset in dataset.items():
            for i, example in enumerate(split_dataset):
                row = {k: v for k, v in example.items()}
                row["_split"] = split_name
                if standardizer:
                    doc = standardizer(row, global_index, extra_metadata)
                else:
                    doc = standardize_custom(row, source, global_index, field_mapping, extra_metadata)
                results.append(doc.to_dict())
                global_index += 1
        return results

    return []


def standardize_raw_rows(
    rows: List[Dict[str, Any]],
    source: str,
    field_mapping: Optional[Dict[str, str]] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    standardizer = STANDARDIZERS.get(source)
    results = []

    for i, row in enumerate(rows):
        if standardizer:
            doc = standardizer(row, i, extra_metadata)
        else:
            doc = standardize_custom(row, source, i, field_mapping, extra_metadata)
        results.append(doc.to_dict())

    return results
