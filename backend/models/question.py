from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database.db import Base

class Interaction(Base):
    """
    Represents a single question-answer interaction.
    Every question you answer creates one of these records.
    """
    __tablename__ = "interactions"
    
    # IDs and relationships
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))  # Which session
    material_id = Column(Integer, ForeignKey("study_materials.id"), nullable=True)  # If from uploaded doc
    
    # The question and answer
    question = Column(Text, nullable=False)  # The question text
    user_answer = Column(Text)  # What you answered
    correct_answer = Column(Text)  # The right answer
    options = Column(Text)  # JSON string: {"A": "option1", "B": "option2", ...}
    
    # Evaluation
    is_correct = Column(Boolean)  # Was it right?
    response_time_seconds = Column(Integer)  # How long you took
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # If question came from uploaded material
    source_page = Column(Integer)  # Which page in the PDF
    source_section = Column(String)  # Which chapter/section
    
    # Relationships
    session = relationship("Session", back_populates="interactions")
    material = relationship("StudyMaterial", back_populates="questions")
    
    def __repr__(self):
        return f"<Interaction(id={self.id}, correct={self.is_correct})>"


class Progress(Base):
    """
    Tracks your mastery level for each topic.
    This is how the app knows what you're good at and what needs practice.
    """
    __tablename__ = "progress"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String, nullable=False)  # e.g., "Python"
    topic = Column(String, nullable=False)    # e.g., "Lists"
    
    # Mastery tracking
    mastery_level = Column(Float, default=0.0)  # 0.0 (novice) to 1.0 (master)
    times_practiced = Column(Integer, default=0)  # How many times studied
    last_practiced = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Progress(subject='{self.subject}', topic='{self.topic}', mastery={self.mastery_level:.2f})>"
    
    @property
    def mastery_percentage(self):
        """Get mastery as a percentage"""
        return self.mastery_level * 100
    
    @property
    def is_mastered(self):
        """Check if topic is mastered (80% or higher)"""
        return self.mastery_level >= 0.8