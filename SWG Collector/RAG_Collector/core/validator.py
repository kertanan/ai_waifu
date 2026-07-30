from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from datasets import Dataset, DatasetDict

from .schema import REQUIRED_FIELDS


@dataclass
class ValidationResult:
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duplicates_removed: int = 0
    empty_rows_removed: int = 0

    def add_error(self, message: str):
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str):
        self.warnings.append(message)


def validate_columns(
    dataset: Dataset,
    required_columns: Optional[List[str]] = None,
    source_columns: Optional[List[str]] = None,
) -> ValidationResult:
    result = ValidationResult()
    columns = set(dataset.column_names)

    if required_columns:
        missing = set(required_columns) - columns
        if missing:
            result.add_error(f"Missing required columns: {missing}")

    if source_columns:
        available = columns.intersection(set(source_columns))
        if not available:
            result.add_warning(f"No source columns found. Available: {columns}")

    return result


def validate_empty_rows(
    dataset: Dataset,
    text_columns: Optional[List[str]] = None,
) -> tuple[Dataset, ValidationResult]:
    result = ValidationResult()

    if not text_columns:
        text_columns = [col for col in dataset.column_names if col != "id"]

    def is_empty(example):
        for col in text_columns:
            if col in example:
                val = example[col]
                if val is None or (isinstance(val, str) and val.strip() == ""):
                    return False
        return True

    original_size = len(dataset)
    filtered = dataset.filter(is_empty, num_proc=1)
    result.empty_rows_removed = original_size - len(filtered)

    if result.empty_rows_removed > 0:
        result.add_warning(f"Removed {result.empty_rows_removed} empty rows")

    return filtered, result


def detect_duplicates(
    dataset: Dataset,
    id_column: str = "id",
) -> tuple[Dataset, ValidationResult]:
    result = ValidationResult()

    if id_column not in dataset.column_names:
        result.add_warning(f"ID column '{id_column}' not found, skipping deduplication")
        return dataset, result

    seen: Set[str] = set()
    unique_indices = []

    for i, example in enumerate(dataset):
        row_id = str(example.get(id_column, ""))
        if row_id not in seen:
            seen.add(row_id)
            unique_indices.append(i)

    result.duplicates_removed = len(dataset) - len(unique_indices)

    if result.duplicates_removed > 0:
        filtered = dataset.select(unique_indices)
        result.add_warning(f"Removed {result.duplicates_removed} duplicate rows")
        return filtered, result

    return dataset, result


def validate_dataset(
    dataset: Union[Dataset, DatasetDict],
    required_columns: Optional[List[str]] = None,
    source_columns: Optional[List[str]] = None,
    text_columns: Optional[List[str]] = None,
    deduplicate: bool = True,
    remove_empty: bool = True,
) -> tuple[Union[Dataset, DatasetDict], ValidationResult]:
    result = ValidationResult()

    if isinstance(dataset, DatasetDict):
        validated_splits = {}
        for split_name, split_dataset in dataset.items():
            validated, split_result = validate_dataset(
                split_dataset,
                required_columns=required_columns,
                source_columns=source_columns,
                text_columns=text_columns,
                deduplicate=deduplicate,
                remove_empty=remove_empty,
            )
            validated_splits[split_name] = validated
            result.errors.extend(split_result.errors)
            result.warnings.extend(split_result.warnings)
            result.duplicates_removed += split_result.duplicates_removed
            result.empty_rows_removed += split_result.empty_rows_removed
            if not split_result.is_valid:
                result.is_valid = False

        return DatasetDict(validated_splits), result

    col_result = validate_columns(dataset, required_columns, source_columns)
    result.errors.extend(col_result.errors)
    result.warnings.extend(col_result.warnings)
    if not col_result.is_valid:
        result.is_valid = False

    if remove_empty:
        dataset, empty_result = validate_empty_rows(dataset, text_columns)
        result.warnings.extend(empty_result.warnings)
        result.empty_rows_removed = empty_result.empty_rows_removed

    if deduplicate:
        dataset, dup_result = detect_duplicates(dataset)
        result.warnings.extend(dup_result.warnings)
        result.duplicates_removed = dup_result.duplicates_removed

    return dataset, result


def validate_standardized_documents(
    documents: List[Dict[str, Any]],
) -> ValidationResult:
    result = ValidationResult()

    seen_ids: Set[str] = set()
    duplicates = 0
    missing_fields = 0

    for i, doc in enumerate(documents):
        doc_id = doc.get("id", "")
        if not doc_id:
            result.add_warning(f"Document at index {i} has empty id")

        if doc_id in seen_ids:
            duplicates += 1
        seen_ids.add(doc_id)

        for field in REQUIRED_FIELDS:
            if field not in doc:
                result.add_warning(f"Document {doc_id} missing field: {field}")
                missing_fields += 1

    if duplicates > 0:
        result.add_warning(f"Found {duplicates} duplicate IDs")

    if missing_fields > 0:
        result.add_warning(f"Total missing fields across documents: {missing_fields}")

    return result
