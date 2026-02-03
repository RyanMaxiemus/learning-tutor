import streamlit as st
import sys
from pathlib import Path
import json
from datetime import datetime, timedelta
from typing import Dict
import time

# Add backend to Python path so we can import it
sys.path.append(str(Path(__file__).parent.parent))

# Import all our backend services
from backend.database.db import SessionLocal, init_db
from backend.models.user import User
from backend.models.session import Session as SessionModel
from backend.models.question import Interaction, Progress
from backend.models.material import StudyMaterial
from backend.services.llm_service import llm_service
from backend.services.progress_tracker import ProgressTracker
from backend.services.material_processor import material_processor
from config.settings import settings
from config.security import (
    SecurityConfig, validate_file_content, sanitize_input,
    generate_secure_filename, secure_file_deletion, validate_file_size,
    log_security_event, SecurityEvents
)
from loguru import logger
import os
import uuid
import re

# Initialize database on first run (only once per session)
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

# Configure Streamlit page
st.set_page_config(
    page_title="AI Learning Tutor",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translateY(10px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
    .fade-in-element {
      animation: fadeIn 0.5s ease-in-out;
    }
    .stButton>button {
        width: 100%;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
    }
    .warning-box {
        padding: 1rem;
        background-color: #fff3cd;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
    }
    .error-box {
        padding: 1rem;
        background-color: #f8d7da;
        border-radius: 0.5rem;
        border-left: 4px solid #dc3545;
    }
</style>
""", unsafe_allow_html=True)

# ===== SESSION STATE INITIALIZATION =====

# Get or create user
if 'user_id' not in st.session_state:
    db = SessionLocal()
    user = db.query(User).first()
    if not user:
        user = User(username="default_user")
        db.add(user)
        db.commit()
        db.refresh(user)
    st.session_state.user_id = user.id
    db.close()

# Initialize session state variables
if 'current_session_id' not in st.session_state:
    st.session_state.current_session_id = None

if 'current_question' not in st.session_state:
    st.session_state.current_question = None

if 'question_start_time' not in st.session_state:
    st.session_state.question_start_time = None

if 'questions_asked' not in st.session_state:
    st.session_state.questions_asked = 0

if 'selected_material_id' not in st.session_state:
    st.session_state.selected_material_id = None

if 'awaiting_answer' not in st.session_state:
    st.session_state.awaiting_answer = False

if 'last_answer_result' not in st.session_state:
    st.session_state.last_answer_result = None

# ===== SIDEBAR NAVIGATION =====

st.sidebar.title("📚 AI Learning Tutor")
st.sidebar.markdown("---")

# Unified page navigation state
if 'page' not in st.session_state:
    st.session_state.page = "🏠 Home"

page_options = ["🏠 Home", "📖 Study Session", "📚 Study Materials", "📊 Progress Dashboard", "⚙️ Settings"]

# The radio button's state is directly tied to `st.session_state.page`.
# This is the single source of truth for the current page.
st.sidebar.radio(
    "Navigate to:",
    page_options,
    key='page',
)

# Use the unified page state
page = st.session_state.page

st.sidebar.markdown("---")

# Show current session info in sidebar if active
db = SessionLocal()
if st.session_state.current_session_id:
    session = db.query(SessionModel).filter(SessionModel.id == st.session_state.current_session_id).first()
    if session:
        st.sidebar.info(f"""
        **Active Session**

        📖 Subject: {session.subject}
        🎯 Topic: {session.topic}
        📊 Difficulty: {session.difficulty_level.title()}

        Questions: {session.questions_answered}/{settings.QUESTIONS_PER_SESSION}
        Correct: {session.questions_correct}
        Accuracy: {session.accuracy:.0f}%
        """)

        # Restart session button
        if st.sidebar.button("🔄 Restart Session", key="sidebar_restart"):
            st.session_state.show_restart_dialog = True
            st.rerun()
db.close()

# ===== HELPER FUNCTIONS =====

def set_page(page_name: str):
    """Callback function to set the page in session state."""
    st.session_state.page = page_name

def resume_session_callback(session_id: int):
    """Callback to set state for resuming a session."""
    st.session_state.current_session_id = session_id

    db = SessionLocal()
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    db.close()

    if session:
        st.session_state.questions_asked = session.questions_answered
    else:
        st.session_state.questions_asked = 0  # Fallback

    st.session_state.current_question = None
    st.session_state.awaiting_answer = False
    st.session_state.selected_material_id = None  # Reset selected material
    st.session_state.page = "📖 Study Session"


def start_another_session_callback():
    """Callback to reset state for a new session."""
    st.session_state.current_session_id = None
    st.session_state.current_question = None
    st.session_state.questions_asked = 0
    st.session_state.awaiting_answer = False


def create_session(subject: str, topic: str, difficulty: str, material_id: int = None) -> int:
    """Create a new study session"""
    db = SessionLocal()
    try:
        session = SessionModel(
            user_id=st.session_state.user_id,
            subject=subject,
            topic=topic,
            difficulty_level=difficulty,
            status="active"
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session.id
    finally:
        db.close()

def end_session(session_id: int):
    """End a study session"""
    db = SessionLocal()
    try:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if session:
            session.end_time = datetime.utcnow()
            session.status = "completed"
            db.commit()
    finally:
        db.close()

def restart_session(session_id: int, new_difficulty: str = None):
    """Restart a session with optional difficulty change"""
    db = SessionLocal()
    try:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if session:
            # Record restart
            session.restart_count += 1

            # Track difficulty change
            if new_difficulty and new_difficulty != session.difficulty_level:
                changes = json.loads(session.difficulty_changes) if session.difficulty_changes else []
                changes.append({
                    "from": session.difficulty_level,
                    "to": new_difficulty,
                    "at_question": session.questions_answered,
                    "timestamp": datetime.utcnow().isoformat()
                })
                session.difficulty_changes = json.dumps(changes)
                session.difficulty_level = new_difficulty

            # Reset counters
            session.questions_answered = 0
            session.questions_correct = 0
            session.status = "active"

            db.commit()
    finally:
        db.close()

def generate_next_question(session_id: int, material_id: int = None, previous_questions: list = None):
    """Generate the next question for a session"""
    db = SessionLocal()
    try:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()

        # Get context from material if using uploaded docs
        context = None
        if material_id:
            # Search material for relevant content
            results = material_processor.search_material(material_id, session.topic, top_k=1)
            if results:
                context = results[0]['text']

        # Generate question using LLM
        question_data = llm_service.generate_question(
            subject=session.subject,
            topic=session.topic,
            difficulty=session.difficulty_level,
            context=context,
            previous_questions=previous_questions
        )

        return question_data
    finally:
        db.close()

def record_answer(session_id: int, question: Dict, user_answer: str, is_correct: bool, response_time: int):
    """Record a question interaction"""
    db = SessionLocal()
    try:
        # Create interaction record
        interaction = Interaction(
            session_id=session_id,
            question=question['question'],
            user_answer=user_answer,
            correct_answer=question['correct'],
            options=json.dumps(question['options']),
            is_correct=is_correct,
            response_time_seconds=response_time,
            material_id=st.session_state.selected_material_id
        )
        db.add(interaction)

        # Update session stats
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        session.questions_answered += 1
        if is_correct:
            session.questions_correct += 1

        # Update progress
        tracker = ProgressTracker(db)
        tracker.update_progress(
            user_id=st.session_state.user_id,
            subject=session.subject,
            topic=session.topic,
            is_correct=is_correct
        )

        db.commit()
    finally:
        db.close()

# ===== PAGE: HOME =====

if page == "🏠 Home":
    st.title("Welcome to Your AI Learning Tutor! 🎓")

    st.markdown("""
    Your personal AI tutor that adapts to your learning pace and style.

    ### 🌟 Features:
    - **Adaptive Learning**: Difficulty adjusts based on your performance
    - **Multi-Subject Support**: Study anything from programming to languages
    - **Document Import**: Upload PDFs and study your own materials
    - **Progress Tracking**: See your improvement over time
    - **100% Private**: Everything runs locally on your computer
    """)

    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("📖 Start Learning")
        st.write("Begin a new study session")
        st.button(
            "Start Session",
            type="primary",
            use_container_width=True,
            on_click=set_page,
            args=("📖 Study Session",)
        )

    with col2:
        st.subheader("📚 Import Materials")
        st.write("Upload your study materials")
        st.button(
            "Upload Documents",
            use_container_width=True,
            on_click=set_page,
            args=("📚 Study Materials",)
        )

    with col3:
        st.subheader("📊 View Progress")
        st.write("Track your learning journey")
        st.button(
            "See Progress",
            use_container_width=True,
            on_click=set_page,
            args=("📊 Progress Dashboard",)
        )

    st.markdown("---")

    # Recent activity
    st.subheader("📅 Recent Activity")

    db = SessionLocal()
    recent_sessions = db.query(SessionModel).filter(
        SessionModel.user_id == st.session_state.user_id
    ).order_by(SessionModel.start_time.desc()).limit(5).all()

    if recent_sessions:
        for session in recent_sessions:
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
            with col1:
                st.write(f"**{session.subject}** - {session.topic}")
            with col2:
                st.write(f"📊 {session.difficulty_level.title()}")
            with col3:
                accuracy = session.accuracy
                color = "🟢" if accuracy >= 80 else "🟡" if accuracy >= 60 else "🔴"
                st.write(f"{color} {accuracy:.0f}% correct")
            with col4:
                st.write(f"🗓️ {session.start_time.strftime('%b %d')}")
            with col5:
                # Show resume button for incomplete sessions
                if session.status == "active" or session.questions_answered < settings.QUESTIONS_PER_SESSION:
                    st.button(
                        "▶️",
                        key=f"home_resume_{session.id}",
                        help="Resume session",
                        on_click=resume_session_callback,
                        args=(session.id,)
                    )
            st.markdown("---")
    else:
        st.info("👋 No recent activity. Start your first session above!")

    db.close()

# ===== PAGE: STUDY SESSION =====

elif page == "📖 Study Session":
    st.title("📖 Study Session")

    # Show restart dialog if requested
    if st.session_state.get('show_restart_dialog', False):
        st.warning("⚠️ Restart Session")
        st.write("Are you sure you want to restart? Your current progress will be saved but reset.")

        col1, col2, col3 = st.columns(3)

        db = SessionLocal()
        session = db.query(SessionModel).filter(SessionModel.id == st.session_state.current_session_id).first()
        current_difficulty = session.difficulty_level if session else "beginner"
        db.close()

        with col1:
            if st.button(f"Keep {current_difficulty.title()}", use_container_width=True):
                restart_session(st.session_state.current_session_id)
                st.session_state.questions_asked = 0
                st.session_state.current_question = None
                st.session_state.awaiting_answer = False
                st.session_state.show_restart_dialog = False
                st.success("✓ Session restarted!")
                time.sleep(1)
                st.rerun()

        with col2:
            new_diff = st.selectbox("Switch to:", ["beginner", "intermediate", "advanced"], key="new_diff")
            if st.button("Switch Difficulty", use_container_width=True):
                restart_session(st.session_state.current_session_id, new_diff)
                st.session_state.questions_asked = 0
                st.session_state.current_question = None
                st.session_state.awaiting_answer = False
                st.session_state.show_restart_dialog = False
                st.success(f"✓ Switched to {new_diff}!")
                time.sleep(1)
                st.rerun()

        with col3:
            if st.button("Cancel", use_container_width=True):
                st.session_state.show_restart_dialog = False
                st.rerun()

        st.stop()

    # If no active session, show setup
    if st.session_state.current_session_id is None:
        st.subheader("🎯 Start a New Session")

        col1, col2 = st.columns(2)

        with col1:
            subject = st.text_input(
                "Subject",
                placeholder="e.g., Python Programming, Spanish, AWS Certification",
                help="What do you want to learn?"
            )

            topic = st.text_input(
                "Topic",
                placeholder="e.g., Control Flow, Past Tense, S3 Security",
                help="Specific topic within the subject"
            )

            difficulty = st.select_slider(
                "Difficulty Level",
                options=["beginner", "intermediate", "advanced"],
                value="beginner",
                help="Don't worry, you can restart and change this anytime!"
            )

        with col2:
            st.write("**Optional: Study from your materials**")

            db = SessionLocal()
            materials = db.query(StudyMaterial).filter(
                StudyMaterial.user_id == st.session_state.user_id,
                StudyMaterial.processing_status == "ready"
            ).all()
            db.close()

            if materials:
                material_options = ["General Knowledge (No specific material)"] + [
                    f"{m.original_filename} ({m.subject})" for m in materials
                ]
                selected_material = st.selectbox(
                    "Study Material",
                    material_options,
                    help="Questions will be based on this document"
                )

                if selected_material != "General Knowledge (No specific material)":
                    idx = material_options.index(selected_material) - 1
                    st.session_state.selected_material_id = materials[idx].id
                else:
                    st.session_state.selected_material_id = None
            else:
                st.info("No materials uploaded yet. Questions will be generated from general knowledge.")
                st.session_state.selected_material_id = None

        st.markdown("---")

        # Start button
        if st.button("🚀 Start Session", type="primary", use_container_width=True):
            if not subject or not topic:
                st.error("⚠️ Please fill in both Subject and Topic")
            else:
                # Sanitize inputs
                subject = sanitize_input(subject, SecurityConfig.MAX_SUBJECT_LENGTH)
                topic = sanitize_input(topic, SecurityConfig.MAX_TOPIC_LENGTH)

                if not subject or not topic:
                    st.error("⚠️ Invalid characters in Subject or Topic. Please use only letters, numbers, and spaces.")
                else:
                    # Create session
                    session_id = create_session(subject, topic, difficulty, st.session_state.selected_material_id)
                    st.session_state.current_session_id = session_id
                    st.session_state.questions_asked = 0
                    st.session_state.current_question = None
                    st.session_state.awaiting_answer = False
                    st.success("✓ Session started! Loading first question...")
                    time.sleep(1)
                    st.rerun()

    # Active session - show questions
    else:
        container = st.container()
        container.markdown('<div class="fade-in-element">', unsafe_allow_html=True)

        db = SessionLocal()
        session = db.query(SessionModel).filter(SessionModel.id == st.session_state.current_session_id).first()

        if not session:
            container.error("Session not found")
            st.session_state.current_session_id = None
            db.close()
            st.rerun()

        # Show session header
        col1, col2, col3 = container.columns([2, 1, 1])
        with col1:
            st.subheader(f"📖 {session.subject}: {session.topic}")
        with col2:
            st.metric("Accuracy", f"{session.accuracy:.0f}%")
        with col3:
            st.metric("Progress", f"{session.questions_answered}/{settings.QUESTIONS_PER_SESSION}")

        container.markdown("---")

        # Check if session is complete
        if session.questions_answered >= settings.QUESTIONS_PER_SESSION:
            end_session(st.session_state.current_session_id)

            container.success("🎉 Session Complete!")
            container.balloons()

            # Show results
            col1, col2, col3 = container.columns(3)
            with col1:
                st.metric("Questions Answered", session.questions_answered)
            with col2:
                st.metric("Correct Answers", session.questions_correct)
            with col3:
                st.metric("Final Accuracy", f"{session.accuracy:.0f}%")

            container.markdown("---")

            # Feedback based on performance
            if session.accuracy >= 90:
                container.success("🌟 **Outstanding!** You've mastered this topic!")
            elif session.accuracy >= 75:
                container.success("✨ **Great job!** You have a solid understanding!")
            elif session.accuracy >= 60:
                container.info("👍 **Good work!** Keep practicing to improve!")
            else:
                container.warning("💪 **Keep going!** Consider reviewing this topic again.")

            # Get progress update
            tracker = ProgressTracker(db)
            progress = tracker.get_subject_progress(st.session_state.user_id, session.subject)

            if progress['topics']:
                topic_progress = next((t for t in progress['topics'] if t['topic'] == session.topic), None)
                if topic_progress:
                    container.info(f"📊 Current mastery of {session.topic}: **{topic_progress['mastery_percentage']:.0f}%**")

            # Suggest next topic
            next_topic = tracker.suggest_next_topic(st.session_state.user_id, session.subject)
            if next_topic:
                container.info(f"💡 **Suggested next topic:** {next_topic}")

            # Action buttons
            col1, col2 = container.columns(2)
            with col1:
                st.button(
                    "Start Another Session",
                    type="primary",
                    use_container_width=True,
                    on_click=start_another_session_callback
                )

            with col2:
                st.button(
                    "View Progress Dashboard",
                    use_container_width=True,
                    on_click=set_page,
                    args=("📊 Progress Dashboard",)
                )

            db.close()
            st.stop()

        # Generate new question if needed
        if st.session_state.current_question is None:
            with st.spinner("🤔 Generating question..."):
                # Fetch previous questions to ensure variety
                previous_interactions = db.query(Interaction).filter(
                    Interaction.session_id == st.session_state.current_session_id
                ).order_by(Interaction.timestamp.desc()).limit(5).all()
                previous_questions = [inter.question for inter in previous_interactions]

                question = generate_next_question(
                    st.session_state.current_session_id,
                    st.session_state.selected_material_id,
                    previous_questions=previous_questions
                )

                # If generation failed, show error and retry option (do not store as current_question)
                if question.get("_generation_failed"):
                    container.error("⚠️ **Question could not be generated**")
                    container.markdown(question.get("message", "Something went wrong. Please try again."))
                    if container.button("🔄 Try again", type="primary", use_container_width=True):
                        st.rerun()
                    container.markdown("---")
                    db.close()
                    st.stop()

                st.session_state.current_question = question
                st.session_state.question_start_time = time.time()
                st.session_state.awaiting_answer = True
                st.session_state.last_answer_result = None

        # Display question
        question = st.session_state.current_question

        # Guard: if we ever have a failed-question in state, show retry (shouldn't happen after above fix)
        if question.get("_generation_failed"):
            container.error("⚠️ **Question could not be generated**")
            container.markdown(question.get("message", "Something went wrong. Please try again."))
            if container.button("🔄 Try again", type="primary", use_container_width=True):
                st.session_state.current_question = None
                st.rerun()
            db.close()
            st.stop()

        container.write(f"**Question {session.questions_answered + 1} of {settings.QUESTIONS_PER_SESSION}:**")
        container.write(f"### {question['question']}")

        if 'code_snippet' in question and question['code_snippet'] and question['code_snippet'] != 'null':
            # Clean up code snippet from markdown and quotes
            code_snippet = question['code_snippet']
            if code_snippet.startswith("```python"):
                code_snippet = code_snippet[9:]
            if code_snippet.startswith("```"):
                code_snippet = code_snippet[3:]
            if code_snippet.endswith("```"):
                code_snippet = code_snippet[:-3]

            # Also remove wrapping quotes if they exist from the JSON string
            if code_snippet.startswith('"') and code_snippet.endswith('"'):
                code_snippet = code_snippet[1:-1]

            # Unescape newlines
            code_snippet = code_snippet.replace('\\n', '\n').replace('\\"', '"')

            container.code(code_snippet.strip(), language='python')

        # Show last answer result if exists
        if st.session_state.last_answer_result:
            result = st.session_state.last_answer_result
            if result['is_correct']:
                container.success(f"✅ {result['feedback']}")
            else:
                container.error(f"❌ {result['feedback']}")
            container.info(f"💡 {question['explanation']}")

            # Next question button
            if container.button("➡️ Next Question", type="primary", use_container_width=True):
                st.session_state.current_question = None
                st.session_state.awaiting_answer = False
                st.session_state.last_answer_result = None
                st.rerun()

        # Show answer options if waiting for answer
        elif st.session_state.awaiting_answer:
            with container.form(key="answer_form"):
                # Ensure options are sorted alphabetically by key (A, B, C, D) for consistent order
                try:
                    sorted_options = sorted(question['options'].items())
                except (TypeError, AttributeError):
                    sorted_options = list(question['options'].items() if isinstance(question.get('options'), dict) else [])

                if not sorted_options:
                    st.error("Question options are invalid or missing. Please try the next question.")
                else:
                    option_list = [f"{key}: {text}" for key, text in sorted_options]

                    selected_option_str = st.radio(
                        "**Select your answer:**",
                        options=option_list,
                        index=None,  # No default selection
                        key="answer_selection"
                    )

                    submitted = st.form_submit_button("Submit Answer", use_container_width=True, type="primary")

                    if submitted:
                        if selected_option_str:
                            with st.spinner("Checking your answer..."):
                                # Extract key and text from selection
                                option_key = selected_option_str.split(':', 1)[0]
                                option_text = selected_option_str.split(':', 1)[1].strip()

                                # Calculate response time
                                response_time = int(time.time() - st.session_state.question_start_time)

                                # Check if correct (instant for multiple choice)
                                is_correct = (option_key == question['correct'])

                                # Use instant feedback for correct answers; LLM only for wrong (personalized feedback)
                                if is_correct:
                                    evaluation = {
                                        "is_correct": True,
                                        "feedback": "Correct! Well done.",
                                        "score": 1.0
                                    }
                                else:
                                    evaluation = llm_service.evaluate_answer(
                                        question=question['question'],
                                        user_answer=option_text,
                                        correct_answer=question['options'][question['correct']],
                                        explanation=question['explanation']
                                    )

                                # Record answer
                                record_answer(
                                    st.session_state.current_session_id,
                                    question,
                                    option_key,
                                    is_correct,
                                    response_time
                                )

                                # Store result
                                st.session_state.last_answer_result = evaluation
                                st.session_state.awaiting_answer = False
                            st.rerun()
                        else:
                            st.warning("Please select an answer before submitting.", icon="⚠️")

            container.markdown("---")

            # Help options
            col1, col2 = container.columns(2)
            with col1:
                if st.button("💡 Get a Hint", use_container_width=True):
                    hint = llm_service.provide_hint(
                        question['question'],
                        question['options'],
                        question['correct']
                    )
                    st.info(f"**Hint:** {hint}")

            with col2:
                if st.button("❓ Explain Topic", use_container_width=True):
                    explanation = llm_service.explain_concept(
                        session.subject,
                        session.topic,
                        session.difficulty_level
                    )
                    st.info(explanation)

        container.markdown('</div>', unsafe_allow_html=True)
        db.close()
# ===== PAGE: STUDY MATERIALS =====

elif page == "📚 Study Materials":
    st.title("📚 Study Materials")

    st.write("Upload your study materials (PDFs, Word documents, or text files) to create personalized learning sessions.")

    # Upload section
    st.subheader("📤 Upload New Material")

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['pdf', 'docx', 'doc', 'txt'],
            help="Supported formats: PDF, Word, Text"
        )

    with col2:
        subject_for_material = st.text_input(
            "Assign to Subject",
            placeholder="e.g., AWS Certification",
            help="Which subject does this material belong to?"
        )

    if uploaded_file and subject_for_material:
        # Sanitize subject input
        subject_for_material = sanitize_input(subject_for_material, SecurityConfig.MAX_SUBJECT_LENGTH)
        if not subject_for_material:
            st.error("❌ Invalid characters in subject name. Please use only letters, numbers, and spaces.")
        elif st.button("📥 Process and Upload", type="primary"):
            with st.spinner("Processing document... This may take a moment."):
                # Sanitize filename to prevent path traversal
                import os
                safe_filename = os.path.basename(uploaded_file.name)
                # Generate random filename to prevent conflicts and improve security
                import uuid
                file_extension = Path(safe_filename).suffix.lower()
                random_filename = f"{uuid.uuid4()}{file_extension}"
                file_path = settings.UPLOADS_DIR / random_filename

                # Validate file size (max 100MB)
                if len(uploaded_file.getbuffer()) > 100 * 1024 * 1024:
                    st.error("❌ File too large. Maximum size is 100MB.")
                    st.stop()

                # Validate file type by content, not just extension
                file_content = uploaded_file.getbuffer()
                if not validate_file_content(file_content, file_extension):
                    st.error("❌ Invalid file type or corrupted file.")
                    st.stop()

                # Save uploaded file
                with open(file_path, 'wb') as f:
                    f.write(file_content)

                # Calculate hash
                file_hash = material_processor.calculate_file_hash(file_path)

                # Check for duplicates
                db = SessionLocal()
                existing = db.query(StudyMaterial).filter(
                    StudyMaterial.user_id == st.session_state.user_id,
                    StudyMaterial.file_hash == file_hash
                ).first()

                if existing:
                    st.warning(f"⚠️ This file appears to be a duplicate of '{existing.original_filename}'")
                    file_path.unlink()  # Delete duplicate
                else:
                    # Create database record
                    material = StudyMaterial(
                        user_id=st.session_state.user_id,
                        subject=subject_for_material,
                        filename=file_path.name,
                        original_filename=uploaded_file.name,
                        file_path=str(file_path),
                        file_type=uploaded_file.name.split('.')[-1].lower(),
                        processing_status="processing",
                        file_hash=file_hash
                    )
                    db.add(material)
                    db.commit()
                    db.refresh(material)

                    # Process the material
                    result = material_processor.process_material(
                        file_path,
                        material.id,
                        subject_for_material
                    )

                    if result.get('success'):
                        material.page_count = result['page_count']
                        material.total_chunks = result['total_chunks']
                        material.processing_status = "ready"
                        db.commit()

                        st.success(f"✅ Successfully processed '{uploaded_file.name}'!")
                        st.info(f"📄 Pages: {result['page_count']} | 📊 Chunks: {result['total_chunks']}")
                    else:
                        material.processing_status = "failed"
                        db.commit()
                        st.error(f"❌ Error processing file: {result.get('error', 'Unknown error')}")

                db.close()
                time.sleep(1)
                st.rerun()

    st.markdown("---")

    # List existing materials
    st.subheader("📚 Your Study Materials")

    db = SessionLocal()
    materials = db.query(StudyMaterial).filter(
        StudyMaterial.user_id == st.session_state.user_id
    ).order_by(StudyMaterial.upload_date.desc()).all()

    if materials:
        for material in materials:
            with st.expander(f"📄 {material.original_filename} ({material.subject})", expanded=False):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.write(f"**Subject:** {material.subject}")
                    st.write(f"**File Type:** {material.file_type.upper()}")
                    st.write(f"**Uploaded:** {material.upload_date.strftime('%B %d, %Y at %I:%M %p')}")

                    if material.processing_status == "ready":
                        st.write(f"**Pages:** {material.page_count}")
                        st.write(f"**Searchable Chunks:** {material.total_chunks}")
                        st.success("✅ Ready to use")
                    elif material.processing_status == "processing":
                        st.info("⏳ Processing...")
                    elif material.processing_status == "failed":
                        st.error("❌ Processing failed")
                    else:
                        st.warning("⏸️ Pending processing")

                with col2:
                    if st.button("🗑️ Delete", key=f"delete_{material.id}"):
                        # Delete from database
                        material_processor.delete_material(material.id)
                        db.delete(material)
                        db.commit()

                        # Delete file securely
                        file_path = Path(material.file_path)
                        if not secure_file_deletion(file_path):
                            st.warning("File deleted from database but may remain on disk.")

                        st.success("Deleted!")
                        time.sleep(1)
                        st.rerun()
    else:
        st.info("📭 No materials uploaded yet. Upload your first document above!")

    db.close()

# ===== PAGE: PROGRESS DASHBOARD =====

elif page == "📊 Progress Dashboard":
    st.title("📊 Progress Dashboard")

    db = SessionLocal()
    tracker = ProgressTracker(db)

    # Get all subjects
    all_progress = db.query(Progress).filter(
        Progress.user_id == st.session_state.user_id
    ).all()

    subjects = list(set([p.subject for p in all_progress]))

    if not subjects:
        st.info("📭 No progress yet. Start a study session to begin tracking your progress!")
        db.close()
    else:
        # Subject selector
        selected_subject = st.selectbox("Select Subject", subjects)

        # Get progress for selected subject
        progress_data = tracker.get_subject_progress(st.session_state.user_id, selected_subject)

        # Overall stats
        st.subheader(f"📖 {selected_subject}")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Overall Mastery", f"{progress_data['overall_mastery'] * 100:.0f}%")

        with col2:
            st.metric("Topics Started", progress_data['topics_started'])

        with col3:
            st.metric("Topics Mastered", progress_data['topics_mastered'])

        with col4:
            mastery_rate = (progress_data['topics_mastered'] / progress_data['topics_started'] * 100) if progress_data['topics_started'] > 0 else 0
            st.metric("Mastery Rate", f"{mastery_rate:.0f}%")

        st.markdown("---")

        # Topics breakdown
        st.subheader("📋 Topics Breakdown")

        topics = progress_data['topics']

        for topic_data in topics:
            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                st.write(f"**{topic_data['topic']}**")

            with col2:
                mastery_pct = topic_data['mastery_percentage']
                if mastery_pct >= 80:
                    status = "🟢 Mastered"
                elif mastery_pct >= 60:
                    status = "🟡 Proficient"
                else:
                    status = "🔴 Needs Practice"
                st.write(status)

            with col3:
                st.write(f"{mastery_pct:.0f}%")

            # Progress bar
            st.progress(topic_data['mastery'])

            # Details
            st.caption(f"Practiced {topic_data['times_practiced']} times | Last: {topic_data['last_practiced']}")
            st.markdown("---")

        # Weak areas
        weak_areas = tracker.get_weak_areas(st.session_state.user_id, selected_subject)

        if weak_areas:
            st.subheader("⚠️ Areas Needing Practice")
            for area in weak_areas[:3]:  # Top 3 weak areas
                st.warning(f"**{area['topic']}** - {area['mastery'] * 100:.0f}% mastery ({area['times_practiced']} sessions)")

        # Recent sessions
        st.subheader("📅 Recent Sessions")

        recent_sessions = db.query(SessionModel).filter(
            SessionModel.user_id == st.session_state.user_id,
            SessionModel.subject == selected_subject
        ).order_by(SessionModel.start_time.desc()).limit(10).all()

        for session in recent_sessions:
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])

            with col1:
                st.write(f"**{session.topic}**")

            with col2:
                st.write(f"📊 {session.difficulty_level.title()}")

            with col3:
                accuracy = session.accuracy
                color = "🟢" if accuracy >= 80 else "🟡" if accuracy >= 60 else "🔴"
                st.write(f"{color} {accuracy:.0f}%")

            with col4:
                st.write(f"🗓️ {session.start_time.strftime('%b %d, %I:%M %p')}")

            with col5:
                # Show resume button for incomplete sessions
                if session.status == "active" or session.questions_answered < settings.QUESTIONS_PER_SESSION:
                    st.button(
                        "▶️ Resume",
                        key=f"resume_{session.id}",
                        on_click=resume_session_callback,
                        args=(session.id,)
                    )
                else:
                    st.write("✅ Complete")

    db.close()

# ===== PAGE: SETTINGS =====

elif page == "⚙️ Settings":
    st.title("⚙️ Settings")

    st.subheader("📤 Export / Import Progress")

    # Export
    st.write("**Export Your Data**")
    st.write("Download all your learning progress as a JSON file for backup or transfer.")

    if st.button("📥 Export Progress Data"):
        db = SessionLocal()

        # Gather all user data
        user = db.query(User).filter(User.id == st.session_state.user_id).first()
        sessions = db.query(SessionModel).filter(SessionModel.user_id == st.session_state.user_id).all()
        progress = db.query(Progress).filter(Progress.user_id == st.session_state.user_id).all()
        materials = db.query(StudyMaterial).filter(StudyMaterial.user_id == st.session_state.user_id).all()

        export_data = {
            "export_version": "1.0",
            "export_date": datetime.utcnow().isoformat(),
            "user_profile": {
                "username": user.username,
                "created_at": user.created_at.isoformat(),
                "total_sessions": len(sessions)
            },
            "sessions": [
                {
                    "subject": s.subject,
                    "topic": s.topic,
                    "difficulty": s.difficulty_level,
                    "questions_answered": s.questions_answered,
                    "questions_correct": s.questions_correct,
                    "accuracy": s.accuracy,
                    "start_time": s.start_time.isoformat(),
                    "end_time": s.end_time.isoformat() if s.end_time else None
                }
                for s in sessions
            ],
            "progress": [
                {
                    "subject": p.subject,
                    "topic": p.topic,
                    "mastery_level": p.mastery_level,
                    "times_practiced": p.times_practiced,
                    "last_practiced": p.last_practiced.isoformat()
                }
                for p in progress
            ],
            "materials": [
                {
                    "original_filename": m.original_filename,
                    "subject": m.subject,
                    "file_type": m.file_type,
                    "page_count": m.page_count,
                    "upload_date": m.upload_date.isoformat()
                }
                for m in materials
            ]
        }

        db.close()

        # Create download
        json_str = json.dumps(export_data, indent=2)
        st.download_button(
            label="💾 Download JSON",
            data=json_str,
            file_name=f"learning_progress_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json"
        )

        st.success("✅ Export ready! Click above to download.")

    st.markdown("---")

    # Import
    st.write("**Import Progress Data**")
    st.write("Upload a previously exported JSON file to restore your progress.")

    import_file = st.file_uploader("Choose JSON file", type=['json'])

    if import_file:
        if st.button("📤 Import Data"):
            try:
                import_data = json.load(import_file)

                # Validate structure
                if "export_version" not in import_data:
                    st.error("❌ Invalid export file format")
                else:
                    st.info("Import feature coming soon! For now, this validates your file.")
                    st.json(import_data["user_profile"])
                    st.success("✅ File is valid!")
            except Exception as e:
                st.error(f"❌ Error reading file: {e}")

    st.markdown("---")

    # App settings
    st.subheader("⚙️ App Settings")

    st.write(f"**Ollama Model:** {settings.OLLAMA_MODEL}")
    st.write(f"**Session Duration:** {settings.SESSION_DURATION_MINUTES} minutes")
    st.write(f"**Questions Per Session:** {settings.QUESTIONS_PER_SESSION}")

    st.info("💡 To change these settings, edit `config/settings.py` or create a `.env` file.")

    st.markdown("---")

    # Reset/Delete options
    st.subheader("🗑️ Data Management")

    st.warning("⚠️ **Danger Zone**")

    if st.button("🗑️ Clear All Progress Data"):
        if st.checkbox("I understand this will delete all my progress"):
            db = SessionLocal()
            db.query(Interaction).filter(Interaction.session_id.in_(
                db.query(SessionModel.id).filter(SessionModel.user_id == st.session_state.user_id)
            )).delete(synchronize_session=False)
            db.query(SessionModel).filter(SessionModel.user_id == st.session_state.user_id).delete()
            db.query(Progress).filter(Progress.user_id == st.session_state.user_id).delete()
            db.commit()
            db.close()

            st.success("✅ All progress data cleared")
            time.sleep(2)
            st.rerun()

    st.markdown("---")

    # About
    st.subheader("ℹ️ About")
    st.write("""
    **AI Learning Tutor v1.0**

    An intelligent, adaptive learning assistant powered by locally-run LLMs.

    - 🤖 Powered by Ollama
    - 🔒 100% Private - runs on your machine
    - 📚 Supports document import
    - 📊 Tracks your progress

    Built with Python, Streamlit, and ❤️
    """)

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("AI Learning Tutor v1.0")
st.sidebar.caption("🔒 All data stored locally")
