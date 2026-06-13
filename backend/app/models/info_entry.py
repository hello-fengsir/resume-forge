import uuid
from datetime import datetime
from typing import Optional
import enum
from sqlalchemy import String, ForeignKey, Text, DateTime, Enum as SAEnum, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.database import Base

class InfoCategory(str, enum.Enum):
    WORK_EXPERIENCE = 'work_experience'
    PROJECT = 'project'
    EDUCATION = 'education'
    SKILL = 'skill'
    CERTIFICATION = 'certification'
    PERSONAL_PROJECT = 'personal_project'

class InfoEntry(Base):
    __tablename__ = 'info_entries'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category: Mapped[InfoCategory] = mapped_column(SAEnum(InfoCategory, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    company: Mapped[Optional[str]] = mapped_column(String(200))
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    content: Mapped[Optional[str]] = mapped_column(Text)
    raw_input: Mapped[Optional[str]] = mapped_column(Text)
    source_file: Mapped[Optional[str]] = mapped_column(String(500))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey('users.id'), index=True, default='default')
    metadata_: Mapped[Optional[dict]] = mapped_column('metadata', JSONB)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(1536))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())