from sqlalchemy import Column, Integer, String, Text, DateTime, func
from .database import Base

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    stored_path = Column(String(600), nullable=False)
    page_count = Column(Integer, default=0)
    extracted_text = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class StudyEvent(Base):
    __tablename__ = "study_events"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(40), nullable=False)
    score = Column(Integer, nullable=True)
    total = Column(Integer, nullable=True)
    details = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
