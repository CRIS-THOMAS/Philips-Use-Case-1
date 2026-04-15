from __future__ import annotations

import argparse
import json
from pathlib import Path

from doc_intel_poc.orchestrator import DocumentIntelligenceWorkflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Intelligent document-processing agent system (PDF + Excel)."
    )
    parser.add_argument(
        "--input",
        nargs="+",
        required=True,
        help="Input files (.pdf, .xlsx, .xls, .csv)",
    )
    parser.add_argument(
        "--goal",
        type=str,
        default="",
        help=(
            "Natural-language goal for the agent, e.g. "
            '"Summarize this and list all questions"'
        ),
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
        "--trace",
        action="store_true",
        help="Print step-by-step execution trace.",
    )
    parser.add_argument(
        "--json-trace",
        action="store_true",
        help="Print execution trace as JSON (for debugging).",
    )
    return parser.parse_args()


def _goal_from_query(goal: str) -> tuple[str, bool]:
    """Parse a conversational goal and derive extract_questions flag."""
    lower = goal.lower()
    extract_q = True

    if "only extract key points" in lower or "only key points" in lower:
        extract_q = False
    elif "no question" in lower:
        extract_q = False

    return goal, extract_q


def main() -> None:
    args = parse_args()
    input_paths = [Path(p) for p in args.input]

    # Conversational interface: derive settings from goal
    goal = args.goal
    extract_questions = not args.no_questions
    if goal:
        goal, q_flag = _goal_from_query(goal)
        extract_questions = extract_questions and q_flag

    workflow = DocumentIntelligenceWorkflow()
    state = workflow.run(
        input_paths=input_paths,
        extract_questions=extract_questions,
        goal=goal,
    )

    # -- Output ----------------------------------------------------------

    if args.json:
        print(json.dumps(state.to_dict(), indent=2))
        return

    if args.trace:
        workflow.print_trace(state)

    if args.json_trace:
        print(json.dumps([t.to_dict() for t in state.execution_trace], indent=2))

    print("=== SUMMARY ===")
    print(state.summary or "No summary generated.")
    print()

    print("=== QUESTIONS ===")
    if state.questions:
        for i, q in enumerate(state.questions, start=1):
            print(f"{i}. {q}")
    else:
        print("No questions found.")

    if state.keywords:
        print()
        print("=== KEYWORDS ===")
        print(", ".join(state.keywords))

    if state.table_insights:
        print()
        print("=== TABLE INSIGHTS ===")
        for sheet in state.table_insights.get("sheets", []):
            print(f"  Sheet '{sheet['sheet']}': {sheet['row_count']} rows, columns: {sheet['columns']}")

    if state.multi_doc_insights:
        print()
        print("=== MULTI-DOCUMENT INSIGHTS ===")
        common = state.multi_doc_insights.get("common_themes", [])
        if common:
            print(f"  Common themes: {', '.join(common)}")

    if state.errors:
        print()
        print("=== ERRORS ===")
        for err in state.errors:
            print(f"- {err}")


if __name__ == "__main__":
    main()
