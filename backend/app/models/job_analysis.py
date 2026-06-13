import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class JobAnalysis(Base):
    __tablename__ = 'job_analyses'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200))
    company: Mapped[Optional[str]] = mapped_column(String(200))
    raw_requirement: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    structured_req: Mapped[Optional[dict]] = mapped_column(JSONB)
    match_result: Mapped[Optional[dict]] = mapped_column(JSONB)
    resume_focus: Mapped[Optional[dict]] = mapped_column(JSONB)
    enterprise_info: Mapped[Optional[dict]] = mapped_column(JSONB)
    recommendation: Mapped[Optional[str]] = mapped_column(String(20))
    advice: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[Optional[str]] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
