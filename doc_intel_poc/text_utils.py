"""Text cleaning utilities for document intelligence preprocessing."""

from __future__ import annotations

import re
import unicodedata


def clean_text(raw: str) -> str:
    """Clean raw extracted text by fixing fragmentation and normalizing whitespace.

    Steps:
        1. Remove non-printable characters (keep newlines and spaces).
        2. Rejoin words broken across lines (e.g. ``"Clie\\nnt"`` → ``"Client"``).
        3. Collapse excessive blank lines into a single blank line.
        4. Normalize whitespace within lines.
    """
    if not raw:
        return ""

    # 1. Strip non-printable / control characters except newline and tab
    text = "".join(
        ch for ch in raw
        if ch in ("\n", "\t") or unicodedata.category(ch)[0] not in ("C",)
    )

    # 2. Rejoin hyphenated line breaks  (e.g. "exam-\nple" → "example")
    text = re.sub(r"-\s*\n\s*", "", text)

    # 3. Replace single newlines with a space (preserve paragraph breaks)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    # 4. Collapse multiple blank lines into one
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 5. Normalize whitespace within lines (tabs, multiple spaces → single space)
    text = re.sub(r"[ \t]+", " ", text)

    # 6. Strip leading/trailing whitespace on each line
    text = "\n".join(line.strip() for line in text.split("\n"))

    # 7. Final trim
    return text.strip()


def count_words(text: str) -> int:
    """Count real words using regex-based tokenization."""
    return len(re.findall(r"\b[a-zA-Z0-9]+(?:['-][a-zA-Z0-9]+)*\b", text))


def count_sentences(text: str) -> int:
    """Count sentences by splitting on sentence-ending punctuation."""
    sentences = re.split(r"[.!?]+", text)
    return sum(1 for s in sentences if s.strip())
