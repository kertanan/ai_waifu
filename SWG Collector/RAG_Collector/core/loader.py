import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from datasets import Dataset, DatasetDict, load_dataset, load_from_disk
import pandas as pd

SUPPORTED_LOCAL_FORMATS = ["json", "jsonl", "csv", "parquet", "arrow"]


def _is_local_path(source: str) -> bool:
    return os.path.exists(source)


def _find_files_in_directory(path: Path) -> List[str]:
    for ext in SUPPORTED_LOCAL_FORMATS:
        files = sorted(path.glob(f"*.{ext}"))
        if files:
            return [str(f) for f in files]
    return []


def _load_local_dataset(
    path: Union[str, Path],
    split: Optional[str] = None,
    **kwargs,
) -> Union[Dataset, DatasetDict]:
    path = Path(path)

    if (path / "dataset_info.json").exists() or any(path.glob("*.arrow")):
        dataset = load_from_disk(str(path), **kwargs)
    elif path.is_dir():
        files = _find_files_in_directory(path)
        if not files:
            raise FileNotFoundError(f"No supported dataset files found in {path}")
        ext = Path(files[0]).suffix.lstrip(".")
        dataset = load_dataset(ext, data_files=files, **kwargs)
    elif path.is_file():
        ext = path.suffix.lstrip(".")
        if ext not in SUPPORTED_LOCAL_FORMATS:
            raise ValueError(f"Unsupported file format: {ext}")
        dataset = load_dataset(ext, data_files=[str(path)], **kwargs)
    else:
        raise FileNotFoundError(f"Path not found: {path}")

    if isinstance(dataset, DatasetDict) and split is not None:
        return dataset[split]
    return dataset


def load_from_huggingface(
    source: str,
    split: Optional[str] = None,
    **kwargs,
) -> Union[Dataset, DatasetDict]:
    dataset = load_dataset(source, split=split, **kwargs)
    if isinstance(dataset, DatasetDict) and split is not None:
        return dataset[split]
    return dataset


def load_from_json(
    path: Union[str, Path],
    split: Optional[str] = None,
    **kwargs,
) -> Dataset:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        if split and split in data:
            data = data[split]
        elif "data" in data:
            data = data["data"]
    return Dataset.from_list(data, **kwargs)


def load_from_csv(
    path: Union[str, Path],
    split: Optional[str] = None,
    **kwargs,
) -> Dataset:
    df = pd.read_csv(path, **kwargs)
    return Dataset.from_pandas(df)


def load_from_parquet(
    path: Union[str, Path],
    split: Optional[str] = None,
    **kwargs,
) -> Dataset:
    df = pd.read_parquet(path, **kwargs)
    return Dataset.from_pandas(df)


def load_dataset_by_source(
    source: str,
    split: Optional[str] = None,
    local: bool = False,
    **kwargs,
) -> Union[Dataset, DatasetDict]:
    if local or _is_local_path(source):
        return _load_local_dataset(source, split=split, **kwargs)
    return load_from_huggingface(source, split=split, **kwargs)


def get_dataset_columns(dataset: Union[Dataset, DatasetDict]) -> List[str]:
    if isinstance(dataset, Dataset):
        return dataset.column_names
    elif isinstance(dataset, DatasetDict):
        first_split = next(iter(dataset))
        return dataset[first_split].column_names
    return []


def get_dataset_size(dataset: Union[Dataset, DatasetDict]) -> int:
    if isinstance(dataset, Dataset):
        return len(dataset)
    elif isinstance(dataset, DatasetDict):
        return sum(len(ds) for ds in dataset.values())
    return 0
