from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database.db import Base

class StudyMaterial(Base):
    """
    Represents an uploaded study document (PDF, Word, etc.).
    Stores metadata about the file and processing status.
    """
    __tablename__ = "study_materials"
    
    # Basic info
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String, nullable=False)  # Which subject it belongs to
    
    # File information
    filename = Column(String, nullable=False)  # Internal storage name
    original_filename = Column(String)  # What user named it
    file_path = Column(String, nullable=False)  # Where it's saved
    file_type = Column(String)  # pdf, docx, txt
    
    # Processing information
    page_count = Column(Integer)  # How many pages
    total_chunks = Column(Integer)  # How many searchable pieces
    processing_status = Column(String, default="pending")
    # Status can be: pending, processing, ready, failed
    
    upload_date = Column(DateTime, default=datetime.utcnow)
    file_hash = Column(String)  # Unique fingerprint to detect duplicates
    
    # Relationships
    user = relationship("User", back_populates="materials")
    questions = relationship("Interaction", back_populates="material")
    annotations = relationship("Annotation", back_populates="material")
    
    def __repr__(self):
        return f"<StudyMaterial(id={self.id}, filename='{self.original_filename}', status='{self.processing_status}')>"


class Annotation(Base):
    """
    Stores user notes and highlights on study materials.
    Like taking notes in a textbook.
    """
    __tablename__ = "annotations"
    
    id = Column(Integer, primary_key=True)
    material_id = Column(Integer, ForeignKey("study_materials.id"))
    
    # What was annotated
    page_number = Column(Integer)  # Which page
    highlighted_text = Column(Text)  # The text they highlighted
    user_note = Column(Text)  # Their note about it
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    material = relationship("StudyMaterial", back_populates="annotations")
    
    def __repr__(self):
        return f"<Annotation(id={self.id}, page={self.page_number})>"