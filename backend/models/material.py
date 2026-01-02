from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database.db import Base

class StudyMaterial(Base):
    __tablename__ = "study_materials"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String, nullable=False)
    
    filename = Column(String, nullable=False)
    original_filename = Column(String)
    file_path = Column(String, nullable=False)
    file_type = Column(String)  # pdf/docx/txt
    
    page_count = Column(Integer)
    total_chunks = Column(Integer)
    processing_status = Column(String, default="pending")  # pending/processing/ready/failed
    
    upload_date = Column(DateTime, default=datetime.utcnow)
    file_hash = Column(String)  # For duplicate detection
    
    # Relationships
    user = relationship("User", back_populates="materials")
    questions = relationship("Interaction", back_populates="material")
    annotations = relationship("Annotation", back_populates="material")

class Annotation(Base):
    __tablename__ = "annotations"
    
    id = Column(Integer, primary_key=True)
    material_id = Column(Integer, ForeignKey("study_materials.id"))
    
    page_number = Column(Integer)
    highlighted_text = Column(Text)
    user_note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    material = relationship("StudyMaterial", back_populates="annotations")