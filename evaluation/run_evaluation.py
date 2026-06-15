import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests
from tabulate import tabulate


API_BASE_URL = "http://127.0.0.1:8000"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_CASES_PATH = PROJECT_ROOT / "test_cases" / "evaluation_cases.json"
RESULTS_PATH = PROJECT_ROOT / "evaluation" / "evaluation_results.json"
REPORT_PATH = PROJECT_ROOT / "evaluation" / "evaluation_report.md"


DECISION_RANK = {
    "ALLOW": 0,
    "WARN": 1,
    "REQUIRE_APPROVAL": 2,
    "BLOCK": 3
}


def load_test_cases() -> List[Dict[str, Any]]:
    with open(TEST_CASES_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def call_scan_endpoint(endpoint: str, content: str) -> Dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}{endpoint}",
        json={"content": content},
        timeout=60
    )
    response.raise_for_status()
    return response.json()


def is_decision_match(actual: str, expected: str) -> bool:
    return actual == expected


def is_category_match(actual_categories: List[str], expected_categories: List[str]) -> bool:
    for category in expected_categories:
        if category not in actual_categories:
            return False

    return True


def classify_result(test_case: Dict[str, Any], actual_result: Dict[str, Any]) -> Dict[str, Any]:
    expected_decision = test_case["expected_decision"]
    expected_categories = test_case.get("expected_categories", [])

    actual_decision = actual_result.get("decision", "UNKNOWN")
    actual_categories = actual_result.get("categories", [])

    decision_match = is_decision_match(actual_decision, expected_decision)
    category_match = is_category_match(actual_categories, expected_categories)

    passed = decision_match and category_match

    expected_rank = DECISION_RANK.get(expected_decision, 0)
    actual_rank = DECISION_RANK.get(actual_decision, 0)

    if passed:
        error_type = "PASS"
    elif actual_rank < expected_rank:
        error_type = "FALSE_NEGATIVE_OR_UNDERCLASSIFIED"
    elif actual_rank > expected_rank:
        error_type = "FALSE_POSITIVE_OR_OVERCLASSIFIED"
    else:
        error_type = "CATEGORY_MISMATCH"

    return {
        "test_id": test_case["id"],
        "endpoint": test_case["endpoint"],
        "input_type": test_case["input_type"],
        "content": test_case["content"],
        "expected_decision": expected_decision,
        "actual_decision": actual_decision,
        "expected_categories": expected_categories,
        "actual_categories": actual_categories,
        "risk_score": actual_result.get("risk_score", 0),
        "passed": passed,
        "error_type": error_type,
        "reasons": actual_result.get("reasons", [])
    }


def run_evaluation() -> Dict[str, Any]:
    test_cases = load_test_cases()
    results = []

    for test_case in test_cases:
        try:
            actual_result = call_scan_endpoint(
                endpoint=test_case["endpoint"],
                content=test_case["content"]
            )

            classified = classify_result(test_case, actual_result)

        except Exception as error:
            classified = {
                "test_id": test_case["id"],
                "endpoint": test_case["endpoint"],
                "input_type": test_case["input_type"],
                "content": test_case["content"],
                "expected_decision": test_case["expected_decision"],
                "actual_decision": "ERROR",
                "expected_categories": test_case.get("expected_categories", []),
                "actual_categories": [],
                "risk_score": 0,
                "passed": False,
                "error_type": "REQUEST_ERROR",
                "reasons": [str(error)]
            }

        results.append(classified)

    total = len(results)
    passed = sum(1 for item in results if item["passed"])
    failed = total - passed

    pass_rate = round((passed / total) * 100, 2) if total else 0

    error_counts: Dict[str, int] = {}
    decision_counts: Dict[str, int] = {}
    category_counts: Dict[str, int] = {}

    for result in results:
        error_type = result["error_type"]
        error_counts[error_type] = error_counts.get(error_type, 0) + 1

        actual_decision = result["actual_decision"]
        decision_counts[actual_decision] = decision_counts.get(actual_decision, 0) + 1

        for category in result["actual_categories"]:
            category_counts[category] = category_counts.get(category, 0) + 1

    evaluation = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "api_base_url": API_BASE_URL,
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "pass_rate_percent": pass_rate,
        "error_counts": error_counts,
        "decision_counts": decision_counts,
        "category_counts": category_counts,
        "results": results
    }

    RESULTS_PATH.parent.mkdir(exist_ok=True)

    with open(RESULTS_PATH, "w", encoding="utf-8") as file:
        json.dump(evaluation, file, indent=2)

    return evaluation


def generate_markdown_report(evaluation: Dict[str, Any]) -> str:
    summary_table = [
        ["Generated At", evaluation["generated_at"]],
        ["API Base URL", evaluation["api_base_url"]],
        ["Total Tests", evaluation["total_tests"]],
        ["Passed", evaluation["passed"]],
        ["Failed", evaluation["failed"]],
        ["Pass Rate", f'{evaluation["pass_rate_percent"]}%']
    ]

    result_rows = []

    for result in evaluation["results"]:
        result_rows.append(
            [
                result["test_id"],
                result["input_type"],
                result["expected_decision"],
                result["actual_decision"],
                ", ".join(result["expected_categories"]),
                ", ".join(result["actual_categories"]),
                result["risk_score"],
                "PASS" if result["passed"] else "FAIL",
                result["error_type"]
            ]
        )

    failed_rows = [
        row for row in result_rows
        if row[7] == "FAIL"
    ]

    report = "# SentinelAI Evaluation Report\n\n"

    report += "## Summary\n\n"
    report += tabulate(
        summary_table,
        tablefmt="github"
    )
    report += "\n\n"

    report += "## Error Breakdown\n\n"

    if evaluation["error_counts"]:
        error_rows = [
            [key, value]
            for key, value in evaluation["error_counts"].items()
        ]
        report += tabulate(
            error_rows,
            headers=["Error Type", "Count"],
            tablefmt="github"
        )
        report += "\n\n"
    else:
        report += "No errors recorded.\n\n"

    report += "## Decision Breakdown\n\n"

    decision_rows = [
        [key, value]
        for key, value in evaluation["decision_counts"].items()
    ]

    report += tabulate(
        decision_rows,
        headers=["Decision", "Count"],
        tablefmt="github"
    )
    report += "\n\n"

    report += "## Category Coverage\n\n"

    category_rows = [
        [key, value]
        for key, value in sorted(evaluation["category_counts"].items())
    ]

    if category_rows:
        report += tabulate(
            category_rows,
            headers=["Category", "Count"],
            tablefmt="github"
        )
        report += "\n\n"
    else:
        report += "No categories detected.\n\n"

    report += "## Failed Tests\n\n"

    if failed_rows:
        report += tabulate(
            failed_rows,
            headers=[
                "Test ID",
                "Input Type",
                "Expected Decision",
                "Actual Decision",
                "Expected Categories",
                "Actual Categories",
                "Risk Score",
                "Result",
                "Error Type"
            ],
            tablefmt="github"
        )
        report += "\n\n"
    else:
        report += "All tests passed.\n\n"

    report += "## Full Test Results\n\n"

    report += tabulate(
        result_rows,
        headers=[
            "Test ID",
            "Input Type",
            "Expected Decision",
            "Actual Decision",
            "Expected Categories",
            "Actual Categories",
            "Risk Score",
            "Result",
            "Error Type"
        ],
        tablefmt="github"
    )
    report += "\n"

    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        file.write(report)

    return report


def print_summary(evaluation: Dict[str, Any]) -> None:
    print("\nSentinelAI Evaluation Complete")
    print("=" * 40)
    print(f"Total Tests: {evaluation['total_tests']}")
    print(f"Passed: {evaluation['passed']}")
    print(f"Failed: {evaluation['failed']}")
    print(f"Pass Rate: {evaluation['pass_rate_percent']}%")
    print(f"Results saved to: {RESULTS_PATH}")
    print(f"Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    evaluation_data = run_evaluation()
    generate_markdown_report(evaluation_data)
    print_summary(evaluation_data)