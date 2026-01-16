"""原始数据模型"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, Enum, Text, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Platform(str, enum.Enum):
    """平台枚举"""
    REDDIT = "reddit"
    YOUTUBE = "youtube"
    X = "x"


class ContentType(str, enum.Enum):
    """内容类型枚举"""
    POST = "post"
    COMMENT = "comment"
    VIDEO = "video"
    TRANSCRIPT = "transcript"


class RawData(Base):
    """原始采集数据表"""
    __tablename__ = "raw_data"
    __table_args__ = (
        UniqueConstraint("task_id", "platform", "source_id", name="uq_task_platform_source_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)

    platform = Column(Enum(Platform), nullable=False, index=True)
    content_type = Column(Enum(ContentType), nullable=False)
    source_id = Column(String(255), nullable=False)

    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    url = Column(String(1000), nullable=True)

    metrics = Column(JSON, default=dict)
    extra_fields = Column(JSON, default=dict)

    published_at = Column(DateTime, nullable=True)
    crawled_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="raw_data")
