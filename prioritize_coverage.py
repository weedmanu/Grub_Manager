import json
import subprocess
import sys
from pathlib import Path


def main():
    print("Running tests and generating coverage report...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pytest", "--cov=.", "--cov-report=json"],
            check=False,  # Don't stop on test failures
            capture_output=True,
        )
    except Exception as e:
        print(f"Error running tests: {e}")
        return

    json_path = Path("coverage.json")
    if not json_path.exists():
        print("coverage.json not found.")
        return

    with open(json_path) as f:
        data = json.load(f)

    files = []
    for filename, file_data in data["files"].items():
        # Filter out temporary scripts and tests
        if (
            filename.startswith("tests/")
            or filename.startswith("fix_")
            or filename.startswith("rename_")
            or filename == "profile_performance.py"
        ):
            continue

        summary = file_data["summary"]
        percent = summary["percent_covered"]
        missing_lines = summary["missing_lines"]

        # We target 100%
        if percent < 100:
            files.append({"name": filename, "percent": percent, "missing": missing_lines})

    # Sort by missing lines (ascending) - smallest gaps first
    files.sort(key=lambda x: x["missing"])

    print(f"\n{'File':<60} | {'Coverage':<10} | {'Missing Lines':<10}")
    print("-" * 85)
    print("Sorted by missing lines (ascending) - easiest to complete first")
    print()

    for f in files:
        print(f"{f['name']:<60} | {f['percent']:>9.2f}% | {f['missing']:>10}")


if __name__ == "__main__":
    main()
