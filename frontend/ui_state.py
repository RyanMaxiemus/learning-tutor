from __future__ import annotations

import streamlit as st


def init_session_state():
    st.session_state.setdefault("db_initialized", False)
    st.session_state.setdefault("user_id", None)
    st.session_state.setdefault("current_session_id", None)
    st.session_state.setdefault("current_question", None)
    st.session_state.setdefault("question_start_time", None)
    st.session_state.setdefault("questions_asked", 0)
    st.session_state.setdefault("selected_material_id", None)
    st.session_state.setdefault("awaiting_answer", False)
    st.session_state.setdefault("last_answer_result", None)
    st.session_state.setdefault("page", "🏠 Home")
    st.session_state.setdefault("show_restart_dialog", False)

