from __future__ import annotations

import argparse
import json
from pathlib import Path

from doc_intel_poc.orchestrator import DocumentIntelligenceWorkflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Planner-driven document intelligence PoC (PDF + Excel)."
    )
    parser.add_argument(
        "--input",
        nargs="+",
        required=True,
        help="Input files (.pdf, .xlsx, .xls, .csv)",
    )
    parser.add_argument(
        "--no-questions",
        action="store_true",
        help="Disable question extraction stage.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print structured JSON output.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_paths = [Path(p) for p in args.input]

    workflow = DocumentIntelligenceWorkflow()
    state = workflow.run(
        input_paths=input_paths,
        extract_questions=not args.no_questions,
    )

    if args.json:
        print(json.dumps(state.to_dict(), indent=2))
        return

    print("=== SUMMARY ===")
    print(state.summary or "No summary generated.")
    print()

    print("=== QUESTIONS ===")
    if state.questions:
        for i, q in enumerate(state.questions, start=1):
            print(f"{i}. {q}")
    else:
        print("No questions found.")

    if state.errors:
        print()
        print("=== ERRORS ===")
        for err in state.errors:
            print(f"- {err}")


if __name__ == "__main__":
    main()
