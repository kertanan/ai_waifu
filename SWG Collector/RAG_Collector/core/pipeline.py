import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from datasets import Dataset, DatasetDict

from .loader import load_dataset_by_source
from .validator import validate_dataset, validate_standardized_documents
from .standardizer import standardize_dataset, standardize_raw_rows
from .cleaner import clean_documents


class StandardizationPipeline:
    def __init__(
        self,
        source: str,
        field_mapping: Optional[Dict[str, str]] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
        deduplicate: bool = True,
        remove_empty: bool = True,
        clean_text_fields: Optional[List[str]] = None,
    ):
        self.source = source
        self.field_mapping = field_mapping
        self.extra_metadata = extra_metadata or {}
        self.deduplicate = deduplicate
        self.remove_empty = remove_empty
        self.clean_text_fields = clean_text_fields

    def run(
        self,
        input_source: str,
        split: Optional[str] = None,
        local: bool = False,
        output_path: Optional[str] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        print(f"[Pipeline] Loading dataset from: {input_source}")
        dataset = load_dataset_by_source(input_source, split=split, local=local, **kwargs)
        print(f"[Pipeline] Loaded {self._get_size(dataset)} records")

        print("[Pipeline] Validating dataset...")
        dataset, validation_result = validate_dataset(
            dataset,
            deduplicate=self.deduplicate,
            remove_empty=self.remove_empty,
        )
        self._print_validation_result(validation_result)

        print(f"[Pipeline] Standardizing to unified schema...")
        documents = standardize_dataset(
            dataset,
            source=self.source,
            field_mapping=self.field_mapping,
            extra_metadata=self.extra_metadata,
        )
        print(f"[Pipeline] Standardized {len(documents)} documents")

        print("[Pipeline] Validating standardized documents...")
        std_validation = validate_standardized_documents(documents)
        self._print_validation_result(std_validation)

        print("[Pipeline] Cleaning documents...")
        documents = clean_documents(documents, text_fields=self.clean_text_fields)
        print(f"[Pipeline] Cleaning complete")

        if output_path:
            self._save_output(documents, output_path)

        print("[Pipeline] Done!")
        return documents

    def run_from_rows(
        self,
        rows: List[Dict[str, Any]],
        output_path: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        print(f"[Pipeline] Processing {len(rows)} raw rows")

        documents = standardize_raw_rows(
            rows,
            source=self.source,
            field_mapping=self.field_mapping,
            extra_metadata=self.extra_metadata,
        )
        print(f"[Pipeline] Standardized {len(documents)} documents")

        print("[Pipeline] Cleaning documents...")
        documents = clean_documents(documents, text_fields=self.clean_text_fields)
        print(f"[Pipeline] Cleaning complete")

        if output_path:
            self._save_output(documents, output_path)

        print("[Pipeline] Done!")
        return documents

    def _get_size(self, dataset: Union[Dataset, DatasetDict]) -> int:
        if isinstance(dataset, Dataset):
            return len(dataset)
        elif isinstance(dataset, DatasetDict):
            return sum(len(ds) for ds in dataset.values())
        return 0

    def _print_validation_result(self, result):
        if result.errors:
            for error in result.errors:
                print(f"  [ERROR] {error}")
        if result.warnings:
            for warning in result.warnings:
                print(f"  [WARN] {warning}")
        if result.is_valid:
            print(f"  [OK] Validation passed")

    def _save_output(self, documents: List[Dict[str, Any]], output_path: str):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.suffix == ".json":
            with open(path, "w", encoding="utf-8") as f:
                json.dump(documents, f, ensure_ascii=False, indent=2)
            print(f"[Pipeline] Saved {len(documents)} documents to {output_path}")
        elif path.suffix == ".jsonl":
            with open(path, "w", encoding="utf-8") as f:
                for doc in documents:
                    f.write(json.dumps(doc, ensure_ascii=False) + "\n")
            print(f"[Pipeline] Saved {len(documents)} documents to {output_path}")
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(documents, f, ensure_ascii=False, indent=2)
            print(f"[Pipeline] Saved {len(documents)} documents to {output_path}")


def run_pipeline(
    source: str,
    input_source: str,
    split: Optional[str] = None,
    local: bool = False,
    output_path: Optional[str] = None,
    field_mapping: Optional[Dict[str, str]] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
    deduplicate: bool = True,
    remove_empty: bool = True,
    clean_text_fields: Optional[List[str]] = None,
    **kwargs,
) -> List[Dict[str, Any]]:
    pipeline = StandardizationPipeline(
        source=source,
        field_mapping=field_mapping,
        extra_metadata=extra_metadata,
        deduplicate=deduplicate,
        remove_empty=remove_empty,
        clean_text_fields=clean_text_fields,
    )
    return pipeline.run(
        input_source,
        split=split,
        local=local,
        output_path=output_path,
        **kwargs,
    )
