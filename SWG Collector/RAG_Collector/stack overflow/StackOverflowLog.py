from pathlib import Path
from datasets import load_dataset
import json


class StackOverflowCollector:

    def __init__(
        self,
        dataset_name: str,
        split: str = "train",
        output_dir: str = "./raw"
    ):
        self.dataset_name = dataset_name
        self.split = split
        self.output_dir = Path(output_dir)

    def download(self):

        print(f"Downloading {self.dataset_name}...")

        dataset = load_dataset(
            self.dataset_name,
            split=self.split
        )

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        filename = self.dataset_name.replace("/", "_") + ".json"

        output_path = self.output_dir / filename

        with open(
            output_path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                list(dataset),
                f,
                ensure_ascii=False,
                indent=4
            )

        print(f"Saved : {output_path}")
        print(f"Total rows : {len(dataset)}")

        return output_path


if __name__ == "__main__":

    collector = StackOverflowCollector(

        dataset_name="pacovaldez/stackoverflow-questions",

        split="train",

        output_dir="./raw"

    )

    collector.download()