from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, func
from .database import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(320), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Document(Base):
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    stored_path = Column(String(600), nullable=False)
    page_count = Column(Integer, default=0)
    extracted_text = Column(Text, default='')
    status = Column(String(30), default='pending', nullable=False)
    index_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class StudyEvent(Base):
    __tablename__ = 'study_events'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    event_type = Column(String(40), nullable=False)
    score = Column(Integer, nullable=True)
    total = Column(Integer, nullable=True)
    details = Column(Text, default='')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
