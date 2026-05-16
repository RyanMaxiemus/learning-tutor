from __future__ import annotations

from datetime import datetime

import streamlit as st

from backend.database.db import SessionLocal
from backend.models.question import Progress


def render_review_queue() -> None:
    st.title("🗓️ Review Queue")
    st.write("Topics due for review based on spaced repetition scheduling.")

    db = SessionLocal()
    try:
        now = datetime.utcnow()
        due = (
            db.query(Progress)
            .filter(
                Progress.user_id == st.session_state.user_id,
                Progress.next_review_date.isnot(None),
                Progress.next_review_date <= now,
            )
            .order_by(Progress.next_review_date.asc())
            .limit(25)
            .all()
        )

        if not due:
            st.success("Nothing due right now. Nice work.")
            return

        st.subheader("Due topics")
        for p in due:
            st.write(f"- **{p.subject} / {p.topic}** (due: {p.next_review_date})")

        st.markdown("---")
        st.subheader("Quick-start a review session")
        subject = st.selectbox("Subject", sorted({p.subject for p in due}))
        topic = st.selectbox(
            "Topic",
            [p.topic for p in due if p.subject == subject],
        )

        if st.button("Start Review Session", type="primary"):
            st.session_state.current_session_id = None
            st.session_state.current_question = None
            st.session_state.questions_asked = 0
            st.session_state.awaiting_answer = False
            st.session_state.selected_material_id = None
            st.session_state.page = "📖 Study Session"

            # pre-fill subject/topic inputs via session_state keys used by the Study Session page (if present)
            st.session_state["prefill_subject"] = subject
            st.session_state["prefill_topic"] = topic
            st.rerun()
    finally:
        db.close()

