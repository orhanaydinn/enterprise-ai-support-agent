import json
from pathlib import Path

from app.evaluation.runner import run_evaluation


RESULTS_DIRECTORY = Path("results")
RESULTS_PATH = RESULTS_DIRECTORY / "evaluation_results.json"


def main() -> None:
    """Run the evaluation suite and save the results."""

    RESULTS_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    evaluation_report = run_evaluation()

    RESULTS_PATH.write_text(
        json.dumps(
            evaluation_report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary = evaluation_report["summary"]

    print("=" * 70)
    print("ENTERPRISE AI SUPPORT AGENT EVALUATION")
    print("=" * 70)
    print(f"Total cases: {summary['total_cases']}")
    print(f"Passed cases: {summary['passed_cases']}")
    print(f"Failed cases: {summary['failed_cases']}")
    print(
        "Overall pass rate: "
        f"{summary['overall_pass_rate'] * 100:.2f}%"
    )
    print(
        "Intent accuracy: "
        f"{summary['intent_accuracy'] * 100:.2f}%"
    )
    print(
        "Status accuracy: "
        f"{summary['status_accuracy'] * 100:.2f}%"
    )
    print(
        "Eligible accuracy: "
        f"{summary['eligible_accuracy'] * 100:.2f}%"
    )
    print(
        "Safety pass rate: "
        f"{summary['safety_pass_rate'] * 100:.2f}%"
    )
    print(
        "Tool accuracy: "
        f"{summary['tool_accuracy'] * 100:.2f}%"
    )
    print(
        "Average latency: "
        f"{summary['average_latency_ms']:.2f} ms"
    )
    print(
        "Minimum latency: "
        f"{summary['minimum_latency_ms']:.2f} ms"
    )
    print(
        "Maximum latency: "
        f"{summary['maximum_latency_ms']:.2f} ms"
    )
    print(
        "Response sources: "
        f"{summary['response_source_counts']}"
    )
    print(
    "Tool names: "
    f"{summary['tool_name_counts']}"
    )
    print(
        "Ticket types: "
        f"{summary['ticket_type_counts']}"
    )
    print(
        "Intent providers: "
        f"{summary['intent_provider_counts']}"
    )
    print("=" * 70)

    if evaluation_report["failed_cases"]:
        print("FAILED CASES")

        for result in evaluation_report["failed_cases"]:
            print("-" * 70)
            print(f"Case ID: {result['case_id']}")
            print(f"Message: {result['message']}")
            print(f"Expected: {result['expected']}")
            print(f"Actual: {result['actual']}")
            print(f"Checks: {result['checks']}")

    print("=" * 70)
    print(f"Saved report: {RESULTS_PATH.resolve()}")


if __name__ == "__main__":
    main()