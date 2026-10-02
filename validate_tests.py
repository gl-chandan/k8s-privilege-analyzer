import csv
import json
from pathlib import Path

from src.graph_builder import build_graph
from src.path_analyzer import find_escalation_paths


TEST_DIR = Path("data/test_cases")
RESULTS_DIR = Path("results")
MAX_DEPTH = 6


def validate_test(file_path):
    # Load expected paths from the JSON file
    with open(file_path, "r") as file:
        test_data = json.load(file)

    expected_paths = {
        tuple(path) for path in test_data["expected_paths"]
    }

    # Build graph and run analyzer
    graph, target = build_graph(str(file_path))
    found_paths = find_escalation_paths(
        graph, target, max_depth=MAX_DEPTH
    )

    found_paths_set = {
        tuple(path) for path in found_paths
    }

    # Compare expected and discovered paths
    missing = expected_paths - found_paths_set
    unexpected = found_paths_set - expected_paths

    passed = not missing and not unexpected

    return {
        "test_case": file_path.name,
        "expected_count": len(expected_paths),
        "found_count": len(found_paths_set),
        "status": "PASS" if passed else "FAIL",
        "missing": missing,
        "unexpected": unexpected,
        "found_paths": found_paths_set
    }


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    test_files = sorted(TEST_DIR.glob("*.json"))

    if not test_files:
        print("No test cases found.")
        return

    results = []

    print("Synthetic Graph Validation")
    print("-" * 40)

    for file_path in test_files:
        result = validate_test(file_path)
        results.append(result)

        print(f"\nTest case: {result['test_case']}")
        print(f"Expected paths: {result['expected_count']}")
        print(f"Found paths: {result['found_count']}")
        print(f"Status: {result['status']}")

        for path in sorted(result["found_paths"]):
            print(" -> ".join(path))

        if result["missing"]:
            print("Missing paths:")
            for path in sorted(result["missing"]):
                print(" -> ".join(path))

        if result["unexpected"]:
            print("Unexpected paths:")
            for path in sorted(result["unexpected"]):
                print(" -> ".join(path))

    # Save validation results
    report_path = RESULTS_DIR / "test_validation.csv"

    with open(report_path, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "Test Case",
            "Expected Paths",
            "Found Paths",
            "Status"
        ])

        for result in results:
            writer.writerow([
                result["test_case"],
                result["expected_count"],
                result["found_count"],
                result["status"]
            ])

    passed_count = sum(
        result["status"] == "PASS" for result in results
    )

    print("\n" + "-" * 40)
    print(f"Total test cases: {len(results)}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {len(results) - passed_count}")
    print(f"Report saved to: {report_path}")

    if passed_count != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()