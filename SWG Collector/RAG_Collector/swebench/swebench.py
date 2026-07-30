import json
from dataset_standardizer import load_and_standardize

standardized = load_and_standardize(
    "./path/to/local/SWE-bench",
    split="test",
    local=True,
    rename_columns={"sentence": "text"},
    keep_columns=["text", "label"],
)

with open("swebench_verified.json", "w", encoding="utf-8") as f:
    json.dump(list(standardized), f, ensure_ascii=False, indent=4)
