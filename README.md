# Document Intelligence Agent PoC (Python)

Simple, modular proof-of-concept for document intelligence similar to PDF.ai.

## What it does

- Accepts input files: PDF and Excel/CSV
- Reads content with:
  - `pdfplumber` for PDF
  - `pandas` for Excel/CSV
- Produces:
  1. Summary
  2. Extracted questions (if present)

## Architecture — Dynamic Agent System

The project uses a **planner-driven execution loop** instead of a hardcoded
pipeline:

1. **Planner** (`doc_intel_poc/planner.py`) — inspects the shared state
   (input paths, options, completed actions) and generates a list of action
   names at runtime. After every step the planner can *revise* the remaining
   plan (insert, remove, or reorder actions).
2. **Tool Registry** (`doc_intel_poc/registry.py`) — a dictionary that maps
   action names to plain Python functions. New tools can be registered at any
   time.
3. **Executor** (`doc_intel_poc/executor.py`) — iterates over the
   planner-generated plan, looks up each action in the registry, executes it,
   and asks the planner to revise the remainder of the plan.
4. **Tools** (`doc_intel_poc/tools.py`) — each tool is a standalone function
   with signature `(state: dict) -> None`. Tools read from and write to a
   shared state dictionary.
5. **Orchestrator** (`doc_intel_poc/orchestrator.py`) — thin wrapper that
   wires the planner, registry, and executor together and exposes a
   `run()` method.

Key properties:

- **No hardcoded sequence** — the planner decides which actions run and in
  what order based on the current state.
- **Shared state dictionary** — every tool reads/writes the same `dict`,
  making data flow explicit.
- **Mid-execution plan revision** — after each step the planner can adapt
  the remaining plan (e.g., skip question extraction when the analysis finds
  no candidates). Tools can also request insertions via
  `state["_insert_actions"]`.
- **Logging** — run with `--verbose` to see a full execution trace of every
  action.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python main.py --input path/to/doc.pdf path/to/sheet.xlsx
```

Verbose logging (execution trace):

```bash
python main.py --input path/to/doc.pdf --verbose
```

JSON output:

```bash
python main.py --input path/to/doc.pdf path/to/sheet.xlsx --json
```

Disable question extraction:

```bash
python main.py --input path/to/doc.pdf path/to/sheet.xlsx --no-questions
```

## Sample Run (example)

Command:

```bash
python main.py --input samples/meeting_notes.pdf samples/qna.xlsx
```

Example output:

```text
=== SUMMARY ===
Processed 2 document(s) with ~1890 words.
Source breakdown: pdf (1210 words), excel (680 words).
Top recurring terms: budget, timeline, vendor, milestone, risk, contract, target, approval.
Highlights: Q3 rollout plan requires legal sign-off before vendor onboarding. | Budget variance exceeded 7 percent in March due to delayed procurement. | Who is responsible for final UAT approval? | Can we accelerate deployment by splitting phase 2 by region?
Detected 5 question(s) in total.

=== QUESTIONS ===
1. Who is responsible for final UAT approval?
2. Can we accelerate deployment by splitting phase 2 by region?
3. What is the revised target date for procurement completion?
4. Should we renegotiate the vendor SLA for support response time?
5. Is the contingency budget enough for Q4 risk mitigation?
```

## Notes

- This PoC is deterministic and heuristic-based (no LLM dependency).
- It is meant for demonstration and extension.
- To improve quality, replace tool logic with an LLM-backed component while keeping the same function signatures.
