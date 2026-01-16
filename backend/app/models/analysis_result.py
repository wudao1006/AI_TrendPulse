"""分析结果模型"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class AnalysisResult(Base):
    """AI分析结果表"""
    __tablename__ = "analysis_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, unique=True)

    sentiment_score = Column(Integer, nullable=False)
    key_opinions = Column(JSON, nullable=False)
    summary = Column(Text, nullable=False)
    mermaid_code = Column(Text, nullable=True)

    heat_index = Column(Float, default=0.0)
    total_items = Column(Integer, default=0)
    platform_distribution = Column(JSON, default=dict)

    analyzed_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="analysis_result")
