from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

import streamlit as st

from doc_intel_poc.orchestrator import DocumentIntelligenceWorkflow

st.set_page_config(page_title="Document Intelligence Agent", page_icon="🧠", layout="wide")

st.title("🧠 Document Intelligence Agent")
st.caption("Upload any documents and let the agent extract insights, questions, and a summary.")

# ── File uploader ────────────────────────────────────────────────────────────
uploaded_files = st.file_uploader(
    "Upload documents",
    type=["pdf", "xlsx", "xls", "csv", "txt", "docx"],
    accept_multiple_files=True,
)

if uploaded_files:
    file_info = [
        {"File name": f.name, "Size (KB)": f"{f.size / 1024:.1f}"}
        for f in uploaded_files
    ]
    st.table(file_info)

# ── Run button ────────────────────────────────────────────────────────────────
run_clicked = st.button("🚀 Run Agent", type="primary")

if run_clicked:
    if not uploaded_files:
        st.warning("Please upload at least one file.")
    else:
        tmp_dir = tempfile.mkdtemp()
        try:
            # Save uploaded files to temp directory with unique names
            temp_paths: list[Path] = []
            for uploaded_file in uploaded_files:
                suffix = Path(uploaded_file.name).suffix
                unique_name = f"{uuid4().hex}{suffix}"
                dest = Path(tmp_dir) / unique_name
                dest.write_bytes(uploaded_file.getbuffer())
                temp_paths.append(dest)

            with st.spinner("Running agent workflow…"):
                try:
                    workflow = DocumentIntelligenceWorkflow()
                    state = workflow.run(input_paths=temp_paths)
                except Exception as exc:
                    st.error(f"Agent workflow failed unexpectedly: {exc}")
                    st.stop()

            # ── Summary ───────────────────────────────────────────────────────
            st.subheader("📝 Summary")
            if state.summary:
                st.markdown(state.summary)
            else:
                st.info("No summary generated.")

            # ── Questions ─────────────────────────────────────────────────────
            st.subheader("❓ Questions")
            if state.questions:
                for i, q in enumerate(state.questions, start=1):
                    st.markdown(f"{i}. {q}")
            else:
                st.info("No questions detected.")

            # ── Analysis details ──────────────────────────────────────────────
            analysis = state.analysis
            if analysis:
                st.subheader("📊 Analysis Details")
                col1, col2, col3 = st.columns(3)
                col1.metric("Documents", analysis.get("document_count", "—"))
                col2.metric("Total words", analysis.get("total_word_count", "—"))
                col3.metric("Question marks", analysis.get("question_mark_count", "—"))

                # Keywords / Top Terms
                top_terms = analysis.get("top_terms") or analysis.get("keywords")
                if top_terms:
                    st.subheader("🔑 Keywords / Top Terms")
                    if isinstance(top_terms, list):
                        st.write(", ".join(str(t) for t in top_terms))
                    else:
                        st.write(top_terms)

                # Per-document insights
                per_doc = analysis.get("per_document", [])
                if per_doc:
                    st.subheader("📄 Per-Document Insights")
                    st.table(per_doc)

                # Multi-document summary
                doc_count = analysis.get("document_count", 0)
                if isinstance(doc_count, int) and doc_count > 1:
                    st.subheader("🗂️ Multi-Document Summary")
                    st.markdown(
                        f"Processed **{doc_count}** documents with a combined "
                        f"**{analysis.get('total_word_count', 0):,}** words. "
                        f"**{analysis.get('question_mark_count', 0)}** question mark(s) detected across all documents."
                    )

            # ── Execution trace ───────────────────────────────────────────────
            with st.expander("🔍 Execution Trace"):
                if state.plan_trace:
                    st.markdown("**Planner steps:**")
                    for step in state.plan_trace:
                        st.markdown(
                            f"- **{step.get('next_agent', '?')}** — {step.get('reason', '')}"
                        )

                if state.completed_agents:
                    st.markdown("**Completed agents:**")
                    for agent in state.completed_agents:
                        st.markdown(f"✅ {agent}")

                if state.errors:
                    st.markdown("**Errors:**")
                    for err in state.errors:
                        st.markdown(f"❌ {err}")

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
