from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.database.db import Base


class StudyMaterial(Base):
    __tablename__ = "study_materials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(200), nullable=False)
    filename = Column(String(255), nullable=False)  # stored filename (e.g. UUID.pdf)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)
    processing_status = Column(String(20), nullable=False, default="pending")  # pending | processing | ready | failed
    file_hash = Column(String(64), nullable=True)
    page_count = Column(Integer, nullable=True)
    total_chunks = Column(Integer, nullable=True)
    upload_date = Column(DateTime(timezone=True), server_default=func.now())


class Annotation(Base):
    """Optional: user annotations on study materials (for future use)."""
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("study_materials.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(String(2000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
