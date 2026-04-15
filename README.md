# Document Intelligence Agent System

Production-grade, intelligent agent system for document processing with dynamic planning, adaptive execution, and multi-tool orchestration.

## What it does

- Accepts input files: PDF, Excel (.xlsx/.xls), and CSV
- Uses a **hybrid LLM + rule-based planner** to dynamically generate execution plans
- Supports **goal-driven planning** — adapts strategy based on:
  - User query (e.g., "Summarize this and list all questions")
  - Document type (report, form/questionnaire, data sheet)
- Orchestrates multiple tools with **failure-aware execution**
- Produces:
  1. Summary
  2. Extracted questions
  3. Keywords / key-phrases
  4. Table analysis (for Excel/CSV)
  5. Multi-document cross-referencing insights

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│  main.py    │────▶│  Orchestrator    │────▶│ Tool Registry│
│ (CLI / UI)  │     │ (failure-aware)  │     │  (dynamic)   │
└─────────────┘     └───────┬──────────┘     └──────┬───────┘
                            │                       │
                    ┌───────▼──────────┐    ┌───────▼───────┐
                    │  Hybrid Planner  │    │   7 Tools:    │
                    │  (LLM + rules)   │    │  reader       │
                    │                  │    │  analyzer     │
                    │  • goal-driven   │    │  keyword_ext  │
                    │  • plan mutation │    │  table_anal   │
                    │  • adaptive      │    │  question_ext │
                    └──────────────────┘    │  multi_doc    │
                                           │  summarizer   │
                                           └───────────────┘
```

### Key components

- **`doc_intel_poc/models.py`** — `ToolResult`, `PlanStep`, `Plan` (with mutation), `TraceEntry`, structured `WorkflowState`
- **`doc_intel_poc/tool_registry.py`** — Dynamic tool registry for planner intelligence
- **`doc_intel_poc/agents/planner.py`** — Hybrid planner (LLM via OpenAI when `OPENAI_API_KEY` is set, otherwise deterministic rules). Supports `generate_plan()`, `revise_plan()`, and `decide_next()`
- **`doc_intel_poc/agents/`** — 7 modular tools, each returning `ToolResult` with `result`, `confidence`, and `error`
- **`doc_intel_poc/orchestrator.py`** — Failure-aware executor with automatic replanning and execution trace

### Design principles

1. **Hybrid planning** — LLM generates plans when available; deterministic rules ensure the system always works without external dependencies
2. **Failure-aware execution** — Every tool returns a `ToolResult` with confidence scores; failures trigger `planner.revise_plan()` automatically
3. **Dynamic tool selection** — The planner chooses tools from the registry based on document type, goal, and available tools
4. **Plan mutation** — Plans support insertion, removal, and reordering of steps based on intermediate results
5. **Multi-document reasoning** — Cross-references insights when multiple files are provided
6. **Conversational interface** — Natural-language `--goal` flag adapts the execution plan

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### Optional: Enable LLM planning

```bash
export OPENAI_API_KEY="sk-..."
```

When set, the planner uses OpenAI to generate plans dynamically. Without it, the system uses deterministic rules (no external API required).

## Run

### Basic usage

```bash
python main.py --input path/to/doc.pdf path/to/sheet.xlsx
```

### With a conversational goal

```bash
python main.py --input doc.pdf --goal "Summarize this and list all questions"
python main.py --input doc.pdf --goal "Only extract key points"
```

### With execution trace

```bash
python main.py --input doc.pdf --trace
```

### JSON output

```bash
python main.py --input doc.pdf --json
```

### JSON trace (for debugging)

```bash
python main.py --input doc.pdf --json-trace
```

### Disable question extraction

```bash
python main.py --input doc.pdf --no-questions
```

## Example Execution Trace

```text
╔══════════════════════════════════════╗
║       EXECUTION TRACE                ║
╚══════════════════════════════════════╝

  Step 1 [✓] reader
    Reason : Parse input files first.
    Output : Read 2 document(s)
    Confidence: 1.00

  Step 2 [✓] analyzer
    Reason : Compute text statistics for downstream tools.
    Output : Analysed 1890 words across 2 doc(s)
    Confidence: 1.00

  Step 3 [✓] keyword_extractor
    Reason : Extract key topics and phrases.
    Output : Extracted 12 keyword(s)
    Confidence: 0.85

  Step 4 [✓] table_analyzer
    Reason : Analyse tabular structure in Excel/CSV files.
    Output : Analysed 1 sheet(s)
    Confidence: 0.80

  Step 5 [✓] multi_doc_reasoner
    Reason : Cross-reference insights across multiple documents.
    Output : Found 5 common theme(s) across 2 documents
    Confidence: 0.75

  Step 6 [✓] question_extractor
    Reason : Extract questions detected in the text.
    Output : Extracted 5 question(s)
    Confidence: 1.00

  Step 7 [✓] summarizer
    Reason : Produce final human-readable summary.
    Output : Processed 2 document(s) with ~1890 words...
    Confidence: 0.90

  Plan goal : Summarize this and list all questions
  Plan revisions: 0

=== SUMMARY ===
Processed 2 document(s) with ~1890 words.
Source breakdown: pdf (1210 words), excel (680 words).
Key topics: budget, timeline, vendor, milestone, risk, contract, target, approval.
Highlights: Q3 rollout plan requires legal sign-off before vendor onboarding. | ...
Detected 5 question(s) in total.
Common themes across documents: budget, milestone, risk, timeline, vendor.

=== QUESTIONS ===
1. Who is responsible for final UAT approval?
2. Can we accelerate deployment by splitting phase 2 by region?
3. What is the revised target date for procurement completion?
4. Should we renegotiate the vendor SLA for support response time?
5. Is the contingency budget enough for Q4 risk mitigation?

=== KEYWORDS ===
budget timeline, vendor milestone, risk contract, budget, timeline, vendor, milestone, risk, contract, target, approval

=== TABLE INSIGHTS ===
  Sheet 'QnA': 15 rows, columns: ['Question', 'Answer', 'Priority']

=== MULTI-DOCUMENT INSIGHTS ===
  Common themes: budget, milestone, risk, timeline, vendor
```

## Notes

- The system works fully **without an LLM** using deterministic rule-based planning
- When `OPENAI_API_KEY` is set, the planner uses GPT to generate adaptive plans
- Every tool returns structured `ToolResult` with confidence scores
- Failed tools trigger automatic plan revision — the system self-heals
- Modular design: add new tools by implementing `Agent` and registering in the orchestrator
