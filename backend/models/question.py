from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database.db import Base

class Interaction(Base):
    __tablename__ = "interactions"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    material_id = Column(Integer, ForeignKey("study_materials.id"), nullable=True)
    
    question = Column(Text, nullable=False)
    user_answer = Column(Text)
    correct_answer = Column(Text)
    options = Column(Text)  # JSON string of multiple choice options
    
    is_correct = Column(Boolean)
    response_time_seconds = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # For material-based questions
    source_page = Column(Integer)
    source_section = Column(String)
    
    # Relationships
    session = relationship("Session", back_populates="interactions")
    material = relationship("StudyMaterial", back_populates="questions")

class Progress(Base):
    __tablename__ = "progress"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    
    mastery_level = Column(Float, default=0.0)  # 0.0 to 1.0
    times_practiced = Column(Integer, default=0)
    last_practiced = Column(DateTime, default=datetime.utcnow)