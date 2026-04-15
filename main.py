from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

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
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging to show execution trace.",
    )
    return parser.parse_args()


def _state_to_json(state: dict[str, Any]) -> dict[str, Any]:
    """Produce a JSON-safe version of the shared state dictionary."""
    docs = state.get("documents", [])
    return {
        "inputs": [str(p) for p in state.get("input_paths", [])],
        "options": state.get("options", {}),
        "documents": [d.to_dict() for d in docs],
        "analysis": state.get("analysis", {}),
        "questions": state.get("questions", []),
        "summary": state.get("summary", ""),
        "completed_actions": state.get("completed_actions", []),
        "execution_log": state.get("execution_log", []),
        "errors": state.get("errors", []),
    }


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    input_paths = [Path(p) for p in args.input]

    workflow = DocumentIntelligenceWorkflow()
    state = workflow.run(
        input_paths=input_paths,
        extract_questions=not args.no_questions,
    )

    if args.json:
        print(json.dumps(_state_to_json(state), indent=2))
        return

    print("=== SUMMARY ===")
    print(state.get("summary") or "No summary generated.")
    print()

    print("=== QUESTIONS ===")
    questions = state.get("questions", [])
    if questions:
        for i, q in enumerate(questions, start=1):
            print(f"{i}. {q}")
    else:
        print("No questions found.")

    errors = state.get("errors", [])
    if errors:
        print()
        print("=== ERRORS ===")
        for err in errors:
            print(f"- {err}")


if __name__ == "__main__":
    main()
