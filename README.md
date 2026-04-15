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
- Uses modular agents with planner-driven execution:
  - Planner
  - Reader
  - Analyzer
  - Question extractor
  - Summarizer

## Architecture

- `doc_intel_poc/agents/planner.py` decides which agent runs next from shared state.
- `doc_intel_poc/orchestrator.py` loops: ask planner -> dispatch selected agent.
- No fixed hardcoded linear pipeline in `main.py`.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python main.py --input path\\to\\doc.pdf path\\to\\sheet.xlsx
```

Optional JSON output:

```bash
python main.py --input path\\to\\doc.pdf path\\to\\sheet.xlsx --json
```

Disable question extraction:

```bash
python main.py --input path\\to\\doc.pdf path\\to\\sheet.xlsx --no-questions
```

## Sample Run (example)

Command:

```bash
python main.py --input samples\\meeting_notes.pdf samples\\qna.xlsx
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
- To improve quality, replace analyzer/summarizer logic with an LLM-backed component while keeping the same agent interfaces.
