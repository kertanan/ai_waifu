import json
from core import run_pipeline, clean_text, validate_standardized_documents
from core.standardizer import standardize_raw_rows
from core.cleaner import clean_documents


def example_swebench():
    dataset = run_pipeline(
        source="swebench",
        input_source="./swebench",
        split="test",
        local=True,
        output_path="./datasets/swebench/standardized.json",
        extra_metadata={"difficulty": "medium"},
    )
    print(f"Processed {len(dataset)} SWE-bench documents")
    return dataset


def example_github_issues():
    dataset = run_pipeline(
        source="github_issues",
        input_source="./github_issue",
        local=True,
        output_path="./datasets/github_issue/standardized.json",
    )
    print(f"Processed {len(dataset)} GitHub Issue documents")
    return dataset


def example_stackoverflow():
    dataset = run_pipeline(
        source="stack_overflow",
        input_source="./stack_overflow",
        local=True,
        output_path="./datasets/stack_overflow/standardized.json",
    )
    print(f"Processed {len(dataset)} Stack Overflow documents")
    return dataset


def example_python_exceptions():
    dataset = run_pipeline(
        source="python_exceptions",
        input_source="./Python Exceptions",
        local=True,
        output_path="./datasets/python_exceptions/standardized.json",
    )
    print(f"Processed {len(dataset)} Python Exception documents")
    return dataset


def example_sqlite_errors():
    dataset = run_pipeline(
        source="sqlite_errors",
        input_source="./SQLite Errors",
        local=True,
        output_path="./datasets/sqlite_errors/standardized.json",
    )
    print(f"Processed {len(dataset)} SQLite Error documents")
    return dataset


def example_fastapi_docs():
    dataset = run_pipeline(
        source="fastapi_docs",
        input_source="./FastAPI Docs",
        local=True,
        output_path="./datasets/fastapi_docs/standardized.json",
    )
    print(f"Processed {len(dataset)} FastAPI Doc documents")
    return dataset


def example_custom_json():
    raw_data = [
        {
            "title": "Django Migration Error",
            "problem": "Running makemigrations fails with ImportError.",
            "solution": "Add missing app to INSTALLED_APPS.",
            "code": "python manage.py makemigrations",
            "language": "python",
            "tags": ["django", "migration"],
        },
        {
            "title": "Flask CORS Issue",
            "problem": "CORS headers not added to response.",
            "solution": "Install flask-cors and initialize CORS(app).",
            "code": "from flask_cors import CORS",
            "language": "python",
            "tags": ["flask", "cors"],
        },
    ]

    documents = standardize_raw_rows(
        raw_data,
        source="custom_json",
        extra_metadata={"framework": "python"},
    )
    cleaned = clean_documents(documents)
    validation = validate_standardized_documents(cleaned)

    print(f"Processed {len(cleaned)} custom documents")
    print(f"Validation: {'PASS' if validation.is_valid else 'FAIL'}")

    return cleaned


def example_text_cleaning():
    dirty_text = """
    <h1>Django Error</h1>
    <p>When saving a model, the following occurs:</p>
    <pre><code>model.save()</code></pre>
    <br/>
    <p><strong>IntegrityError</strong>: duplicate key value</p>
    """

    clean = clean_text(dirty_text)
    print("Dirty text:")
    print(dirty_text[:200])
    print("\nClean text:")
    print(clean)
    return clean


if __name__ == "__main__":
    print("=" * 60)
    print("RAG Collector - Standardization Pipeline Examples")
    print("=" * 60)

    print("\n--- Example: Text Cleaning ---")
    example_text_cleaning()

    print("\n--- Example: Custom JSON ---")
    example_custom_json()

    print("\n" + "=" * 60)
    print("To run source-specific pipelines, uncomment the desired function")
    print("and ensure the dataset paths are correct.")
    print("=" * 60)
