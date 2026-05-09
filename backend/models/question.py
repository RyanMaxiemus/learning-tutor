from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.database.db import Base


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    question = Column(String(2000), nullable=False)
    user_answer = Column(String(500), nullable=False)
    correct_answer = Column(String(500), nullable=False)
    options = Column(String(2000), nullable=True)  # JSON
    is_correct = Column(Boolean, nullable=False)
    response_time_seconds = Column(Integer, nullable=True)
    material_id = Column(Integer, ForeignKey("study_materials.id"), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class Progress(Base):
    __tablename__ = "progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(200), nullable=False)
    topic = Column(String(200), nullable=False)
    mastery_level = Column(Float, nullable=False, default=0.0)  # 0.0 to 1.0
    times_practiced = Column(Integer, nullable=False, default=0)
    last_practiced = Column(DateTime(timezone=True), nullable=True)
    next_review_date = Column(DateTime(timezone=True), nullable=True)
    interval = Column(Integer, nullable=False, default=1)
