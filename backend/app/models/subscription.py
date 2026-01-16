"""订阅模型"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Subscription(Base):
    """关键词订阅表"""
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keyword = Column(String(255), nullable=False, index=True)
    platforms = Column(JSON, nullable=False)
    language = Column(String(10), default="en")
    report_language = Column(String(10), default="auto")
    semantic_sampling = Column(Boolean, default=False)
    limit = Column(Integer, default=50)
    platform_configs = Column(JSON, default=dict)

    interval_hours = Column(Integer, default=6)
    interval_minutes = Column(Integer, nullable=True)
    alert_threshold = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)

    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    alerts = relationship("Alert", back_populates="subscription", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="subscription")
