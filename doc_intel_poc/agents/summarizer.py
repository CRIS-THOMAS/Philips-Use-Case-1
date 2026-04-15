from __future__ import annotations

import re
from collections import Counter

from doc_intel_poc.agents.base import Agent
from doc_intel_poc.models import WorkflowState


class SummarizerAgent(Agent):
    name = "summarizer"

    STOPWORDS = {
        "the", "and", "for", "that", "with", "this", "from", "have",
        "are", "was", "were", "has", "had", "will", "would", "could",
        "should", "about", "into", "their", "there", "them", "then",
        "than", "also", "your", "you", "our", "but", "not", "all",
        "been", "its", "may", "can", "each", "which", "does", "did",
        "source", "pdf", "page", "sheet", "csv", "based", "used",
        "using", "such", "when", "where", "what", "how", "who",
        "more", "other", "some", "only", "over", "any", "most",
        "after", "before", "between", "through", "during", "without",
        "like", "just", "very", "even", "still", "well", "much",
        "make", "made", "get", "got", "take", "took", "come", "came",
        "know", "see", "think", "say", "said", "one", "two", "three",
    }

    _MARKER_RE = re.compile(r"^(\[?SOURCE:|---\s*(PDF Page|Sheet:))")

    _NUMBER_RE = re.compile(
        r"(?:\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"
        r"|\b(?:19|20)\d{2}\b"
        r"|\b\d[\d,]*\.?\d*\s*%"
        r"|\$\s*\d[\d,]*\.?\d*"
        r"|\b\d[\d,]*\.?\d*\s*(?:million|billion|thousand|units|items|days|hours|months|years|people|users)\b"
        r")",
        re.IGNORECASE,
    )

    def run(self, state: WorkflowState) -> None:
        if not state.documents:
            state.summary = "No readable content found in the provided files."
            return

        text = state.combined_text or ""
        paragraphs: list[str] = []

        # --- 1. Purpose paragraph ---
        purpose = self._infer_purpose(text)
        paragraphs.append(purpose)

        # --- 2. Key concepts & components ---
        concepts_para = self._build_concepts_paragraph(text)
        if concepts_para:
            paragraphs.append(concepts_para)

        # --- 3. Important details, numbers, and findings ---
        details_para = self._build_details_paragraph(text)
        if details_para:
            paragraphs.append(details_para)

        # --- 4. Results and observations ---
        results_para = self._build_results_paragraph(text)
        if results_para:
            paragraphs.append(results_para)

        # --- 5. Open questions as substantive content ---
        if state.questions:
            questions_para = self._build_questions_paragraph(state.questions)
            paragraphs.append(questions_para)

        # --- 6. Conclusion ---
        top_terms = self._top_terms(text, top_n=5)
        conclusion = self._build_conclusion(text, top_terms)
        paragraphs.append(conclusion)

        state.summary = "\n\n".join(paragraphs)

    # ------------------------------------------------------------------
    # Paragraph builders
    # ------------------------------------------------------------------

    def _infer_purpose(self, text: str) -> str:
        lower = text.lower()
        purpose_signals = [
            (["meeting", "minutes", "agenda", "attendees", "discussion"],
             "The document records the proceedings of a meeting, capturing the "
             "agenda items discussed, key decisions reached by participants, "
             "and action items assigned for follow-up. It serves as an official "
             "record of the conversation, including points of agreement and "
             "areas where further deliberation is needed."),
            (["invoice", "payment", "billing", "amount due", "purchase"],
             "The document deals with a financial transaction, detailing the "
             "items or services billed, associated costs, payment terms, and "
             "relevant parties involved. It functions as a formal record of "
             "the financial obligations and settlement expectations between "
             "the transacting entities."),
            (["report", "analysis", "findings", "results", "evaluation"],
             "The document presents a structured analysis of a particular "
             "subject, walking through the methodology, data examined, and "
             "the conclusions drawn from the evidence. It is intended to "
             "inform stakeholders about observed patterns, performance "
             "indicators, and recommended next steps."),
            (["contract", "agreement", "terms", "clause", "obligations"],
             "The document lays out the contractual terms and conditions "
             "governing an agreement between parties. It covers mutual "
             "obligations, deliverables, timelines, liability provisions, "
             "and the conditions under which the agreement may be modified "
             "or terminated."),
            (["specification", "requirement", "design", "architecture", "system"],
             "The document describes the technical specifications or design "
             "blueprint for a system or component. It covers the functional "
             "requirements, architectural decisions, interface definitions, "
             "and constraints that guide the implementation and integration "
             "of the solution."),
            (["policy", "procedure", "compliance", "guideline", "regulation"],
             "The document outlines organizational policies and procedural "
             "guidelines intended to ensure compliance with internal standards "
             "or external regulations. It defines the expected behaviors, "
             "approval workflows, and accountability structures that govern "
             "day-to-day operations."),
            (["proposal", "budget", "plan", "timeline", "milestone", "project"],
             "The document presents a project proposal or strategic plan, "
             "describing the objectives, scope, anticipated timeline, key "
             "milestones, and the budget allocation required for execution. "
             "It aims to align stakeholders around the planned approach and "
             "resource commitments needed to achieve the stated goals."),
            (["data", "table", "record", "entry", "column", "row"],
             "The document contains structured data organized into records "
             "and fields, representing a dataset meant for tracking, "
             "reporting, or further analytical processing. The entries cover "
             "specific attributes and measurements relevant to the subject "
             "matter at hand."),
        ]
        best_match = ""
        best_score = 0
        for keywords, description in purpose_signals:
            score = sum(1 for kw in keywords if kw in lower)
            if score > best_score:
                best_score = score
                best_match = description
        if best_score >= 2:
            return best_match
        # Fallback: build purpose from top themes
        top = self._top_terms(text, top_n=3)
        if top:
            themes = ", ".join(top)
            return (
                f"The document addresses topics related to {themes}. "
                f"It presents information in a structured manner, covering "
                f"relevant details, context, and observations pertaining to "
                f"these subjects."
            )
        return (
            "The document presents structured content covering its core "
            "subject matter with relevant details and contextual information."
        )

    def _build_concepts_paragraph(self, text: str) -> str:
        top_terms = self._top_terms(text, top_n=12)
        if not top_terms:
            return ""

        # Group into primary concepts and supporting topics
        primary = top_terms[:4]
        supporting = top_terms[4:8]
        peripheral = top_terms[8:]

        parts: list[str] = []
        parts.append(
            f"The central concepts discussed revolve around "
            f"{self._natural_join(primary)}."
        )
        if supporting:
            parts.append(
                f"Supporting these core ideas, the document also addresses "
                f"{self._natural_join(supporting)}, providing additional "
                f"context and depth to the primary discussion."
            )
        if peripheral:
            parts.append(
                f"References to {self._natural_join(peripheral)} appear "
                f"throughout, tying together the broader narrative."
            )
        return " ".join(parts)

    def _build_details_paragraph(self, text: str) -> str:
        detail_sentences = self._extract_detail_sentences(text, max_count=6)
        if not detail_sentences:
            return ""

        # Separate numeric-detail sentences from qualitative ones
        numeric: list[str] = []
        qualitative: list[str] = []
        for sent in detail_sentences:
            if self._NUMBER_RE.search(sent):
                numeric.append(sent)
            else:
                qualitative.append(sent)

        parts: list[str] = []
        if numeric:
            parts.append(
                "Several important details stand out. "
                + " ".join(numeric)
            )
        if qualitative:
            parts.append(" ".join(qualitative))

        return " ".join(parts)

    def _build_results_paragraph(self, text: str) -> str:
        findings = self._extract_findings(text, max_sentences=5)
        if not findings:
            return ""
        return " ".join(findings)

    def _build_questions_paragraph(self, questions: list[str]) -> str:
        if len(questions) == 1:
            return (
                f"One notable question raised within the content is: "
                f'"{questions[0]}" This suggests an area where further '
                f"investigation or clarification may be warranted."
            )
        previews = questions[:4]
        formatted = "; ".join(f'"{q}"' for q in previews)
        remainder = ""
        if len(questions) > 4:
            remainder = (
                f", along with {len(questions) - 4} additional question(s)"
            )
        return (
            f"Several questions emerge from the content, including "
            f"{formatted}{remainder}. These questions point to areas "
            f"where decisions are pending or additional information is "
            f"needed to move forward."
        )

    def _build_conclusion(self, text: str, top_terms: list[str]) -> str:
        if top_terms:
            focus = self._natural_join(top_terms[:3])
            return (
                f"Overall, the document provides a substantive treatment of "
                f"{focus}. The information presented forms a coherent "
                f"narrative that connects the key themes, supporting details, "
                f"and any open items into a complete picture of the subject "
                f"matter. Readers should pay particular attention to the "
                f"specific figures, decisions, and questions highlighted "
                f"above, as these represent the most actionable elements "
                f"of the content."
            )
        return (
            "Overall, the document covers its subject matter with sufficient "
            "detail to inform further review or decision-making. The key "
            "points and observations described above capture the substance "
            "of what was communicated."
        )

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    def _top_terms(self, text: str, top_n: int) -> list[str]:
        tokens = re.findall(r"\b[a-zA-Z][a-zA-Z-]{2,}\b", text.lower())
        filtered = (tok for tok in tokens if tok not in self.STOPWORDS)
        counts = Counter(filtered)
        return [term for term, _ in counts.most_common(top_n)]

    def _extract_detail_sentences(
        self, text: str, max_count: int,
    ) -> list[str]:
        sentences = self._split_sentences(text)
        scored: list[tuple[float, str]] = []

        detail_words = {
            "percent", "total", "budget", "cost", "date", "deadline",
            "march", "april", "january", "february", "may", "june",
            "july", "august", "september", "october", "november", "december",
            "q1", "q2", "q3", "q4", "revenue", "amount", "count",
            "version", "release", "phase", "stage", "level", "rate",
            "score", "average", "maximum", "minimum", "threshold",
        }

        for sent in sentences:
            clean = " ".join(sent.split()).strip()
            if len(clean) < 35 or len(clean) > 220:
                continue
            if self._MARKER_RE.search(clean):
                continue

            lower = clean.lower()
            words = set(re.findall(r"\b[a-z]+\b", lower))
            score = len(words & detail_words)
            if self._NUMBER_RE.search(clean):
                score += 2
            if 50 < len(clean) < 180:
                score += 0.5

            if score >= 1.5:
                scored.append((score, clean))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:max_count]]

    def _extract_findings(self, text: str, max_sentences: int = 5) -> list[str]:
        sentences = self._split_sentences(text)
        scored: list[tuple[float, str]] = []

        signal_words = {
            "result", "concluded", "determined", "found", "observed",
            "significant", "approved", "confirmed", "completed",
            "achieved", "exceeded", "declined", "increased", "decreased",
            "recommended", "required", "resolved", "identified",
            "implemented", "established", "delivered", "performance",
            "impact", "outcome", "decision", "priority", "critical",
            "essential", "improvement", "risk", "target", "goal",
            "successful", "failure", "progress", "challenge", "solution",
            "conclusion", "noted", "addressed", "proposed", "agreed",
        }

        for sent in sentences:
            clean = " ".join(sent.split()).strip()
            if len(clean) < 40 or len(clean) > 250:
                continue
            if self._MARKER_RE.search(clean):
                continue

            lower = clean.lower()
            words = set(re.findall(r"\b[a-z]+\b", lower))
            score = len(words & signal_words)
            if self._NUMBER_RE.search(clean):
                score += 1
            if 60 < len(clean) < 180:
                score += 0.5

            if score >= 1.5:
                scored.append((score, clean))

        scored.sort(key=lambda x: x[0], reverse=True)
        selected = [s for _, s in scored[:max_sentences]]
        if not selected:
            return []
        return selected

    def _split_sentences(self, text: str) -> list[str]:
        return re.split(r"(?<=[.!?])\s+", text)

    @staticmethod
    def _natural_join(items: list[str]) -> str:
        if not items:
            return ""
        if len(items) == 1:
            return items[0]
        if len(items) == 2:
            return f"{items[0]} and {items[1]}"
        return ", ".join(items[:-1]) + f", and {items[-1]}"
