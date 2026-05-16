from __future__ import annotations

import streamlit as st

from backend.database.db import SessionLocal
from backend.models.user import User
from backend.security.passwords import hash_password, verify_password


def render_auth_gate() -> None:
    """
    Renders login/register when user is not authenticated.
    Stops execution (st.stop) if user is not logged in.
    """
    if st.session_state.user_id is not None:
        return

    st.title("🔒 Login to AI Learning Tutor")
    st.write("Please log in or register to track your learning progress.")

    auth_mode = st.radio("Mode", ["Login", "Register"], horizontal=True)
    with st.form("auth_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Submit")

        if submitted:
            if not (username and password):
                st.error("Please enter both username and password")
                st.stop()

            db = SessionLocal()
            try:
                user = db.query(User).filter(User.username == username).first()
                if auth_mode == "Register":
                    if user:
                        st.error("Username already exists")
                    else:
                        new_user = User(username=username, password_hash=hash_password(password))
                        db.add(new_user)
                        db.commit()
                        db.refresh(new_user)
                        st.session_state.user_id = new_user.id
                        st.success("Registered successfully!")
                        st.rerun()
                else:
                    if not user:
                        st.error("Invalid username or password")
                    else:
                        result = verify_password(password, user.password_hash)
                        if result.ok:
                            if result.needs_rehash and result.upgraded_hash:
                                user.password_hash = result.upgraded_hash
                                db.add(user)
                                db.commit()
                            st.session_state.user_id = user.id
                            st.success("Logged in successfully!")
                            st.rerun()
                        else:
                            st.error("Invalid username or password")
            finally:
                db.close()

    st.stop()

