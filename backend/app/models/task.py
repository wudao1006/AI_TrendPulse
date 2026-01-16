"""任务模型"""
import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, String, Integer, DateTime, Enum, Text, JSON, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class TaskStatus(str, enum.Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(Base):
    """采集分析任务表"""
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=True, index=True)
    keyword = Column(String(255), nullable=False, index=True)
    language = Column(String(10), default="en")
    report_language = Column(String(10), default="auto")
    semantic_sampling = Column(Boolean, default=False)
    limit_count = Column(Integer, default=50)
    platforms = Column(JSON, nullable=False)
    platform_configs = Column(JSON, default=dict)

    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, index=True)
    progress = Column(Integer, default=0)
    celery_task_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    raw_data = relationship("RawData", back_populates="task", cascade="all, delete-orphan")
    analysis_result = relationship("AnalysisResult", back_populates="task", uselist=False, cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="tasks")
