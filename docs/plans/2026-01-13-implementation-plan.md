# AI舆情分析系统实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建一个多源AI舆情分析系统，支持Reddit/YouTube数据采集、LLM智能分析、Flutter可视化展示。

**Architecture:** 三层异步架构 - FastAPI提供REST API，Celery+Redis处理异步任务，PostgreSQL持久化存储。采集器和分析器均采用插件化设计，支持水平扩展。

**Tech Stack:** Python 3.10+, FastAPI, Celery, Redis, PostgreSQL, SQLAlchemy, PRAW, youtube-transcript-api, Flutter 3.x, Riverpod

---

## 并行开发模块划分

本计划分为 **4个可并行开发的模块**：

| 模块 | 负责内容 | 依赖 |
|------|---------|------|
| **Module A** | 后端基础架构（FastAPI + DB + Celery） | 无 |
| **Module B** | 数据采集器（Reddit + YouTube） | Module A 的数据模型 |
| **Module C** | AI分析模块 | Module A 的数据模型 |
| **Module D** | Flutter前端 | Module A 的API接口定义 |

**并行策略：** Module A 优先启动，完成数据模型后 B/C/D 可并行开发。

---

## Module A: 后端基础架构

### Task A1: 项目初始化与依赖配置

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/.gitignore`

**Step 1: 创建 pyproject.toml**

```toml
[project]
name = "ai-sentiment-backend"
version = "0.1.0"
description = "AI舆情分析系统后端"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.13.0",
    "psycopg2-binary>=2.9.0",
    "celery[redis]>=5.3.0",
    "redis>=5.0.0",
    "praw>=7.7.0",
    "youtube-transcript-api>=0.6.0",
    "google-api-python-client>=2.100.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "python-dotenv>=1.0.0",
    "langdetect>=1.0.9",
    "openai>=1.30.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "black>=24.1.0",
    "ruff>=0.1.0",
]
```

**Step 2: 创建 requirements.txt**

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
alembic>=1.13.0
psycopg2-binary>=2.9.0
celery[redis]>=5.3.0
redis>=5.0.0
praw>=7.7.0
youtube-transcript-api>=0.6.0
google-api-python-client>=2.100.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-dotenv>=1.0.0
langdetect>=1.0.9
openai>=1.30.0
pytest>=7.4.0
pytest-asyncio>=0.23.0
# APScheduler for dynamic scheduled tasks
apscheduler>=3.10.0
```

**Step 3: 创建 .env.example**

```
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ai_sentiment

# Redis
REDIS_URL=redis://localhost:6379/0

# Reddit API
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=ai-sentiment-bot/1.0

# YouTube API
YOUTUBE_API_KEY=your_youtube_api_key

# LLM API
LLM_API_KEY=your_llm_api_key
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# App Config
DEBUG=true
LOG_LEVEL=INFO
SCHEDULER_ENABLED=true
```

**Step 4: 创建 .gitignore**

```
__pycache__/
*.py[cod]
.env
.venv/
venv/
*.egg-info/
dist/
build/
.pytest_cache/
.ruff_cache/
*.log
```

---

### Task A2: 配置管理模块

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`

**Step 1: 创建空的 __init__.py**

```python
"""AI舆情分析系统后端"""
```

**Step 2: 创建配置管理 config.py**

```python
"""应用配置管理，从环境变量加载配置"""
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""

    # Database
    database_url: str

    # Redis
    redis_url: str

    # Reddit API
    reddit_client_id: str
    reddit_client_secret: str
    reddit_user_agent: str

    # YouTube API
    youtube_api_key: str

    # LLM API
    llm_api_key: str
    llm_api_base_url: str
    llm_model: str

    # App Config
    debug: bool
    log_level: str

    # Scheduler
    scheduler_enabled: bool

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
```

---

### Task A3: 数据库模型定义

**Files:**
- Create: `backend/app/database.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/task.py`
- Create: `backend/app/models/raw_data.py`
- Create: `backend/app/models/analysis_result.py`
- Create: `backend/app/models/subscription.py`
- Create: `backend/app/models/alert.py`

**Step 1: 创建数据库连接 database.py**

```python
"""数据库连接配置"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """获取数据库会话的依赖注入函数"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Step 2: 创建 models/__init__.py**

```python
"""数据库模型"""
from app.models.task import Task, TaskStatus
from app.models.raw_data import RawData, Platform, ContentType
from app.models.analysis_result import AnalysisResult
from app.models.subscription import Subscription
from app.models.alert import Alert

__all__ = [
    "Task",
    "TaskStatus",
    "RawData",
    "Platform",
    "ContentType",
    "AnalysisResult",
    "Subscription",
    "Alert",
]
```

**Step 3: 创建 Task 模型 models/task.py**

```python
"""任务模型"""
import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, String, Integer, DateTime, Enum, Text, JSON
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
    keyword = Column(String(255), nullable=False, index=True)
    language = Column(String(10), default="en")
    limit_count = Column(Integer, default=50)
    platforms = Column(JSON, nullable=False)  # ["reddit", "youtube"]
    platform_configs = Column(JSON, default=dict)

    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, index=True)
    progress = Column(Integer, default=0)  # 0-100
    celery_task_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    raw_data = relationship("RawData", back_populates="task", cascade="all, delete-orphan")
    analysis_result = relationship("AnalysisResult", back_populates="task", uselist=False, cascade="all, delete-orphan")
```

**Step 4: 创建 RawData 模型 models/raw_data.py**

```python
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
        UniqueConstraint("platform", "source_id", name="uq_platform_source_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)

    platform = Column(Enum(Platform), nullable=False, index=True)
    content_type = Column(Enum(ContentType), nullable=False)
    source_id = Column(String(255), nullable=False)  # 平台原始ID

    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    url = Column(String(1000), nullable=True)

    metrics = Column(JSON, default=dict)  # {"upvotes": 100, "comments": 50}
    extra_fields = Column(JSON, default=dict)  # 平台特有字段

    published_at = Column(DateTime, nullable=True)
    crawled_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    task = relationship("Task", back_populates="raw_data")
```

**Step 5: 创建 AnalysisResult 模型 models/analysis_result.py**

```python
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

    sentiment_score = Column(Integer, nullable=False)  # 0-100
    key_opinions = Column(JSON, nullable=False)  # [{"title": "...", "description": "..."}]
    summary = Column(Text, nullable=False)
    mermaid_code = Column(Text, nullable=True)

    heat_index = Column(Float, default=0.0)  # 热度指数
    total_items = Column(Integer, default=0)  # 分析的数据条数
    platform_distribution = Column(JSON, default=dict)  # {"reddit": 60, "youtube": 40}

    analyzed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    task = relationship("Task", back_populates="analysis_result")
```

**Step 6: 创建 Subscription 模型 models/subscription.py**

```python
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
    platforms = Column(JSON, nullable=False)  # ["reddit", "youtube"]
    language = Column(String(10), default="en")
    limit = Column(Integer, default=50)
    platform_configs = Column(JSON, default=dict)

    interval_hours = Column(Integer, default=6)  # 采集间隔
    alert_threshold = Column(Integer, default=30)  # 报警阈值，低于此分数触发
    is_active = Column(Boolean, default=True)

    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    alerts = relationship("Alert", back_populates="subscription", cascade="all, delete-orphan")
```

**Step 7: 创建 Alert 模型 models/alert.py**

```python
"""报警模型"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Alert(Base):
    """报警记录表"""
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)

    sentiment_score = Column(Integer, nullable=False)
    alert_type = Column(String(50), default="negative_sentiment")
    is_read = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    subscription = relationship("Subscription", back_populates="alerts")
```

---

### Task A4: Pydantic Schemas定义

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/task.py`
- Create: `backend/app/schemas/analysis.py`
- Create: `backend/app/schemas/subscription.py`

**Step 1: 创建 schemas/__init__.py**

```python
"""API请求/响应模型"""
from app.schemas.task import (
    TaskCreate,
    TaskResponse,
    TaskStatusResponse,
    RawDataResponse,
    RawDataListResponse,
)
from app.schemas.analysis import AnalysisResultResponse, KeyOpinion
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    AlertResponse,
)

__all__ = [
    "TaskCreate",
    "TaskResponse",
    "TaskStatusResponse",
    "RawDataResponse",
    "RawDataListResponse",
    "AnalysisResultResponse",
    "KeyOpinion",
    "SubscriptionCreate",
    "SubscriptionUpdate",
    "SubscriptionResponse",
    "AlertResponse",
]
```

**Step 2: 创建 schemas/task.py**

```python
"""任务相关的请求/响应模型"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    """创建任务请求"""
    keyword: str = Field(..., min_length=1, max_length=255, description="搜索关键词")
    language: str = Field(default="en", pattern="^(en|zh)$", description="语言")
    limit: int = Field(default=50, ge=10, le=100, description="采集条数")
    platforms: List[str] = Field(..., min_length=1, description="采集平台列表")
    platform_configs: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "keyword": "DeepSeek",
                "language": "en",
                "limit": 50,
                "platforms": ["reddit", "youtube"]
            }
        }


class TaskResponse(BaseModel):
    """创建任务响应"""
    task_id: UUID
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: UUID
    keyword: str
    platforms: List[str]
    status: str
    progress: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RawDataResponse(BaseModel):
    """单条原始数据响应"""
    id: UUID
    platform: str
    content_type: str
    title: Optional[str]
    content: Optional[str]
    author: Optional[str]
    url: Optional[str]
    metrics: Dict[str, Any]
    published_at: Optional[datetime]

    class Config:
        from_attributes = True


class RawDataListResponse(BaseModel):
    """原始数据列表响应"""
    total: int
    page: int
    page_size: int
    data: List[RawDataResponse]
```

**Step 3: 创建 schemas/analysis.py**

```python
"""分析结果相关的请求/响应模型"""
from datetime import datetime
from typing import List, Dict, Optional
from uuid import UUID

from pydantic import BaseModel


class KeyOpinion(BaseModel):
    """核心观点"""
    title: str
    description: str


class AnalysisResultResponse(BaseModel):
    """分析结果响应"""
    task_id: UUID
    sentiment_score: int
    key_opinions: List[KeyOpinion]
    summary: str
    mermaid_code: Optional[str]
    heat_index: float
    total_items: int
    platform_distribution: Dict[str, int]
    analyzed_at: datetime

    class Config:
        from_attributes = True
```

**Step 4: 创建 schemas/subscription.py**

```python
"""订阅相关的请求/响应模型"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class SubscriptionCreate(BaseModel):
    """创建订阅请求"""
    keyword: str = Field(..., min_length=1, max_length=255)
    platforms: List[str] = Field(..., min_length=1)
    language: str = Field(default="en", pattern="^(en|zh)$")
    limit: int = Field(default=50, ge=10, le=200)
    interval_hours: int = Field(default=6, ge=1, le=24)
    alert_threshold: int = Field(default=30, ge=0, le=100)
    platform_configs: Optional[Dict[str, Any]] = None


class SubscriptionUpdate(BaseModel):
    """更新订阅请求"""
    keyword: Optional[str] = Field(None, min_length=1, max_length=255)
    platforms: Optional[List[str]] = None
    language: Optional[str] = Field(None, pattern="^(en|zh)$")
    limit: Optional[int] = Field(None, ge=10, le=200)
    interval_hours: Optional[int] = Field(None, ge=1, le=24)
    alert_threshold: Optional[int] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None
    platform_configs: Optional[Dict[str, Any]] = None


class SubscriptionResponse(BaseModel):
    """订阅响应"""
    id: UUID
    keyword: str
    platforms: List[str]
    language: str
    limit: int
    interval_hours: int
    alert_threshold: int
    is_active: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    created_at: datetime
    platform_configs: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    """报警响应"""
    id: UUID
    subscription_id: UUID
    task_id: Optional[UUID]
    sentiment_score: int
    alert_type: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
```

---

### Task A5: Celery配置

**Files:**
- Create: `backend/app/workers/__init__.py`
- Create: `backend/app/workers/celery_app.py`

**Step 1: 创建 workers/__init__.py**

```python
"""Celery任务模块"""
from app.workers.celery_app import celery_app

__all__ = ["celery_app"]
```

**Step 2: 创建 celery_app.py**

```python
"""Celery应用配置

注意：定时任务调度已迁移至 APScheduler (app/services/scheduler_service.py)
Celery 仅用于异步任务处理，不再使用 beat_schedule
"""
from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_sentiment",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.collect_tasks",
        "app.workers.analyze_tasks",
    ],
)

# Celery配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30分钟超时
    task_soft_time_limit=25 * 60,  # 25分钟软超时
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,  # 结果1小时过期
)

# 注意：定时任务调度已由 APScheduler 接管
# 参见：app/services/scheduler_service.py
```

---

### Task A5.1: APScheduler调度服务

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/scheduler_service.py`

**Step 1: 创建 services/__init__.py**

```python
"""服务模块"""
from app.services.scheduler_service import SchedulerService

__all__ = ["SchedulerService"]
```

**Step 2: 创建 scheduler_service.py**

```python
"""APScheduler调度服务

使用 APScheduler 替代 Celery Beat，支持：
- 实时 CRUD 订阅的定时任务
- 精确的时间调度
- 持久化到 PostgreSQL

配置说明：
- `SCHEDULER_ENABLED=true|false`（默认 true）
  - true：API 进程启动 APScheduler
  - false：API 不启动调度器（适用于单独部署调度进程或避免多实例重复调度）
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class SchedulerService:
    """APScheduler 调度服务单例"""

    _instance: Optional["SchedulerService"] = None
    _scheduler: Optional[BackgroundScheduler] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "SchedulerService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def init_scheduler(self):
        """初始化调度器"""
        if self._scheduler is not None:
            return

        jobstores = {
            'default': SQLAlchemyJobStore(url=settings.database_url)
        }
        executors = {
            'default': ThreadPoolExecutor(10)
        }
        job_defaults = {
            'coalesce': True,
            'max_instances': 1,
            'misfire_grace_time': 60 * 5,
        }

        self._scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC',
        )
        self._scheduler.start()
        logger.info("APScheduler started")

    def shutdown(self, wait: bool = True):
        """关闭调度器"""
        if self._scheduler:
            self._scheduler.shutdown(wait=wait)
            logger.info("APScheduler shutdown")

    def add_subscription_job(
        self,
        subscription_id: str,
        interval_hours: int,
        run_immediately: bool = True,
    ):
        """添加订阅的定时任务"""
        job_id = f"subscription_{subscription_id}"

        self._scheduler.add_job(
            func=trigger_subscription_task,
            trigger=IntervalTrigger(hours=interval_hours),
            id=job_id,
            args=[subscription_id],
            replace_existing=True,
            name=f"Subscription: {subscription_id}",
        )
        logger.info(f"Added job {job_id} with interval {interval_hours}h")

        if run_immediately:
            trigger_subscription_task(subscription_id)

    def update_subscription_job(self, subscription_id: str, interval_hours: int):
        """更新任务间隔"""
        job_id = f"subscription_{subscription_id}"
        self._scheduler.reschedule_job(
            job_id,
            trigger=IntervalTrigger(hours=interval_hours),
        )
        logger.info(f"Updated job {job_id} to {interval_hours}h interval")

    def pause_subscription_job(self, subscription_id: str):
        """暂停任务"""
        job_id = f"subscription_{subscription_id}"
        self._scheduler.pause_job(job_id)
        logger.info(f"Paused job {job_id}")

    def resume_subscription_job(self, subscription_id: str):
        """恢复任务"""
        job_id = f"subscription_{subscription_id}"
        self._scheduler.resume_job(job_id)
        logger.info(f"Resumed job {job_id}")

    def remove_subscription_job(self, subscription_id: str):
        """移除任务"""
        job_id = f"subscription_{subscription_id}"
        try:
            self._scheduler.remove_job(job_id)
            logger.info(f"Removed job {job_id}")
        except Exception as e:
            logger.warning(f"Job {job_id} not found: {e}")

    def get_job_info(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        job_id = f"subscription_{subscription_id}"
        job = self._scheduler.get_job(job_id)

        if not job:
            return None

        return {
            "job_id": job.id,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        }

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """获取所有任务"""
        jobs = self._scheduler.get_jobs()
        return [
            {
                "job_id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
            for job in jobs
        ]


def trigger_subscription_task(subscription_id: str):
    """触发订阅任务（APScheduler调用）"""
    from app.database import SessionLocal
    from app.models import Subscription, Task, TaskStatus
    from app.workers.collect_tasks import collect_and_analyze

    db = SessionLocal()
    try:
        subscription = db.query(Subscription).filter(
            Subscription.id == subscription_id
        ).first()

        if not subscription or not subscription.is_active:
            logger.warning(f"Subscription {subscription_id} not found or inactive")
            return

        # 创建任务
        task = Task(
            keyword=subscription.keyword,
            language=subscription.language,
            limit_count=50,
            platforms=subscription.platforms,
            status=TaskStatus.PENDING,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # 触发Celery任务
        celery_task = collect_and_analyze.delay(str(task.id))
        task.celery_task_id = celery_task.id

        # 更新订阅
        subscription.last_run_at = datetime.utcnow()
        db.commit()

        logger.info(f"Triggered task {task.id} for subscription {subscription_id}")

    except Exception as e:
        logger.error(f"Failed to trigger subscription {subscription_id}: {e}")
    finally:
        db.close()
```

---

### Task A6: FastAPI主应用

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/tasks.py`
- Create: `backend/app/api/platforms.py`

**Step 1: 创建 main.py**

```python
"""FastAPI应用入口"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import tasks, platforms, subscriptions, alerts
from app.database import SessionLocal
from app.models import Subscription
from app.services.scheduler_service import SchedulerService

settings = get_settings()
logger = logging.getLogger(__name__)

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动时：
    1. 初始化 APScheduler
    2. 从数据库恢复所有活跃订阅的定时任务

    关闭时：
    1. 优雅关闭 APScheduler
    """
    # ========== 启动逻辑 ==========
    logger.info("Starting application...")

    scheduler = SchedulerService.get_instance()
    if settings.scheduler_enabled:
        # 初始化调度器
        scheduler.init_scheduler()

        # 从数据库恢复活跃订阅的调度任务
        db = SessionLocal()
        try:
            active_subscriptions = db.query(Subscription).filter(
                Subscription.is_active == True
            ).all()

            restored_count = 0
            for sub in active_subscriptions:
                try:
                    scheduler.add_subscription_job(
                        subscription_id=str(sub.id),
                        interval_hours=sub.interval_hours,
                        run_immediately=False,  # 启动时不立即执行，等待正常调度
                    )
                    restored_count += 1
                except Exception as e:
                    logger.error(f"Failed to restore subscription job {sub.id}: {e}")

            logger.info(f"Restored {restored_count}/{len(active_subscriptions)} subscription jobs")

        except Exception as e:
            logger.error(f"Error restoring subscription jobs: {e}")
        finally:
            db.close()
    else:
        logger.info("Scheduler disabled by config; skipping init")

    logger.info("Application startup complete")

    yield  # 应用运行中

    # ========== 关闭逻辑 ==========
    logger.info("Shutting down application...")

    # 优雅关闭调度器（等待当前任务完成）
    if settings.scheduler_enabled:
        scheduler.shutdown(wait=True)

    logger.info("Application shutdown complete")


app = FastAPI(
    title="AI舆情分析系统",
    description="多源数据采集与AI智能分析API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS配置
# 注意：生产环境应配置具体的 allow_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: 生产环境改为具体域名
    allow_credentials=False,  # 使用 * 时必须为 False
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """健康检查接口"""
    scheduler = SchedulerService.get_instance()
    jobs = scheduler.get_all_jobs()

    return {
        "status": "healthy",
        "version": "1.0.0",
        "scheduler": {
            "active_jobs": len(jobs),
        }
    }


@app.get("/scheduler/jobs")
async def list_scheduler_jobs():
    """列出所有调度任务（调试用）"""
    scheduler = SchedulerService.get_instance()
    return {
        "jobs": scheduler.get_all_jobs()
    }


# 注册路由
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["任务管理"])
app.include_router(platforms.router, prefix="/api/v1/platforms", tags=["平台管理"])
app.include_router(subscriptions.router, prefix="/api/v1/subscriptions", tags=["订阅管理"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["报警管理"])
```

**Step 2: 创建 api/__init__.py**

```python
"""API路由模块"""
from app.api import tasks, platforms, subscriptions, alerts

__all__ = ["tasks", "platforms", "subscriptions", "alerts"]
```

**Step 3: 创建 api/tasks.py**

```python
"""任务相关API"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Task, TaskStatus, RawData, AnalysisResult
from app.schemas import (
    TaskCreate,
    TaskResponse,
    TaskStatusResponse,
    RawDataListResponse,
    RawDataResponse,
    AnalysisResultResponse,
    KeyOpinion,
)
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.post("", response_model=TaskResponse)
async def create_task(task_data: TaskCreate, db: Session = Depends(get_db)):
    """
    创建新的采集分析任务

    - **keyword**: 搜索关键词
    - **language**: 语言 (en/zh)
    - **limit**: 采集条数 (10-100)
    - **platforms**: 平台列表 ["reddit", "youtube"]
    """
    # 校验平台
    for platform in task_data.platforms:
        if platform not in settings.supported_platforms:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的平台: {platform}，支持的平台: {settings.supported_platforms}"
            )

    # 创建任务
    task = Task(
        keyword=task_data.keyword,
        language=task_data.language,
        limit_count=task_data.limit,
        platforms=task_data.platforms,
        status=TaskStatus.PENDING,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 触发Celery任务
    from app.workers.collect_tasks import collect_and_analyze
    celery_task = collect_and_analyze.delay(str(task.id))

    # 更新celery_task_id
    task.celery_task_id = celery_task.id
    db.commit()

    return TaskResponse(
        task_id=task.id,
        status=task.status.value,
        created_at=task.created_at,
    )


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: UUID, db: Session = Depends(get_db)):
    """查询任务状态"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return TaskStatusResponse(
        task_id=task.id,
        keyword=task.keyword,
        platforms=task.platforms,
        status=task.status.value,
        progress=task.progress,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.get("/{task_id}/result", response_model=AnalysisResultResponse)
async def get_task_result(task_id: UUID, db: Session = Depends(get_db)):
    """获取分析结果"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"任务尚未完成，当前状态: {task.status.value}")

    result = db.query(AnalysisResult).filter(AnalysisResult.task_id == task_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="分析结果不存在")

    return AnalysisResultResponse(
        task_id=result.task_id,
        sentiment_score=result.sentiment_score,
        key_opinions=[KeyOpinion(**op) for op in result.key_opinions],
        summary=result.summary,
        mermaid_code=result.mermaid_code,
        heat_index=result.heat_index,
        total_items=result.total_items,
        platform_distribution=result.platform_distribution,
        analyzed_at=result.analyzed_at,
    )


@router.get("/{task_id}/raw-data", response_model=RawDataListResponse)
async def get_raw_data(
    task_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    platform: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """获取原始采集数据"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    query = db.query(RawData).filter(RawData.task_id == task_id)

    if platform:
        query = query.filter(RawData.platform == platform)

    total = query.count()
    data = query.offset((page - 1) * page_size).limit(page_size).all()

    return RawDataListResponse(
        total=total,
        page=page,
        page_size=page_size,
        data=[RawDataResponse(
            id=item.id,
            platform=item.platform.value,
            content_type=item.content_type.value,
            title=item.title,
            content=item.content,
            author=item.author,
            url=item.url,
            metrics=item.metrics,
            published_at=item.published_at,
        ) for item in data],
    )
```

**Step 4: 创建 api/platforms.py**

```python
"""平台管理API"""
from typing import List

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("", response_model=List[str])
async def list_platforms():
    """获取支持的平台列表"""
    return settings.supported_platforms
```

---

### Task A7: 订阅和报警API

**Files:**
- Create: `backend/app/api/subscriptions.py`
- Create: `backend/app/api/alerts.py`

**Step 1: 创建 api/subscriptions.py**

```python
"""订阅管理API"""
from datetime import datetime, timedelta
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Subscription
from app.schemas import SubscriptionCreate, SubscriptionUpdate, SubscriptionResponse
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.post("", response_model=SubscriptionResponse)
async def create_subscription(data: SubscriptionCreate, db: Session = Depends(get_db)):
    """创建订阅"""
    for platform in data.platforms:
        if platform not in settings.supported_platforms:
            raise HTTPException(status_code=400, detail=f"不支持的平台: {platform}")

    subscription = Subscription(
        keyword=data.keyword,
        platforms=data.platforms,
        language=data.language,
        interval_hours=data.interval_hours,
        alert_threshold=data.alert_threshold,
        next_run_at=datetime.utcnow() + timedelta(hours=data.interval_hours),
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    return SubscriptionResponse.model_validate(subscription)


@router.get("", response_model=List[SubscriptionResponse])
async def list_subscriptions(db: Session = Depends(get_db)):
    """列出所有订阅"""
    subscriptions = db.query(Subscription).order_by(Subscription.created_at.desc()).all()
    return [SubscriptionResponse.model_validate(s) for s in subscriptions]


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(subscription_id: UUID, db: Session = Depends(get_db)):
    """获取单个订阅"""
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="订阅不存在")
    return SubscriptionResponse.model_validate(subscription)


@router.put("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: UUID,
    data: SubscriptionUpdate,
    db: Session = Depends(get_db),
):
    """更新订阅"""
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="订阅不存在")

    update_data = data.model_dump(exclude_unset=True)

    if "platforms" in update_data:
        for platform in update_data["platforms"]:
            if platform not in settings.supported_platforms:
                raise HTTPException(status_code=400, detail=f"不支持的平台: {platform}")

    for key, value in update_data.items():
        setattr(subscription, key, value)

    db.commit()
    db.refresh(subscription)

    return SubscriptionResponse.model_validate(subscription)


@router.delete("/{subscription_id}")
async def delete_subscription(subscription_id: UUID, db: Session = Depends(get_db)):
    """删除订阅"""
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="订阅不存在")

    db.delete(subscription)
    db.commit()

    return {"message": "删除成功"}
```

**Step 2: 创建 api/alerts.py**

```python
"""报警管理API"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert
from app.schemas import AlertResponse

router = APIRouter()


@router.get("", response_model=List[AlertResponse])
async def list_alerts(
    is_read: bool = Query(default=None),
    db: Session = Depends(get_db),
):
    """获取报警列表"""
    query = db.query(Alert).order_by(Alert.created_at.desc())

    if is_read is not None:
        query = query.filter(Alert.is_read == is_read)

    alerts = query.limit(100).all()
    return [AlertResponse.model_validate(a) for a in alerts]


@router.put("/{alert_id}/read")
async def mark_alert_read(alert_id: UUID, db: Session = Depends(get_db)):
    """标记报警为已读"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="报警不存在")

    alert.is_read = True
    db.commit()

    return {"message": "已标记为已读"}


@router.put("/read-all")
async def mark_all_alerts_read(db: Session = Depends(get_db)):
    """标记所有报警为已读"""
    db.query(Alert).filter(Alert.is_read == False).update({"is_read": True})
    db.commit()

    return {"message": "已全部标记为已读"}
```

---

### Task A8: 数据库迁移配置

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/.gitkeep`

**Step 1: 创建 alembic.ini**

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

**Step 2: 创建 alembic/env.py**

```python
"""Alembic迁移环境配置"""
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.config import get_settings
from app.database import Base
from app.models import *  # noqa: F401, F403

config = context.config
settings = get_settings()

config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

## Module B: 数据采集器

### Task B1: 采集器基类设计

**Files:**
- Create: `backend/app/collectors/__init__.py`
- Create: `backend/app/collectors/base.py`

**Step 1: 创建 collectors/__init__.py**

```python
"""数据采集器模块"""
from app.collectors.base import BaseCollector, CollectorRegistry
from app.collectors.reddit import RedditCollector
from app.collectors.youtube import YouTubeCollector

# 注册采集器
CollectorRegistry.register("reddit", RedditCollector)
CollectorRegistry.register("youtube", YouTubeCollector)

__all__ = [
    "BaseCollector",
    "CollectorRegistry",
    "RedditCollector",
    "YouTubeCollector",
]
```

**Step 2: 创建 collectors/base.py**

```python
"""采集器基类和注册机制"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Type


@dataclass
class CollectedItem:
    """采集到的数据项"""
    platform: str
    content_type: str
    source_id: str
    title: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    url: Optional[str] = None
    metrics: Dict = field(default_factory=dict)
    extra_fields: Dict = field(default_factory=dict)
    published_at: Optional[datetime] = None


class BaseCollector(ABC):
    """采集器基类"""

    platform_name: str = ""

    def __init__(self, config: Dict = None):
        """
        初始化采集器

        Args:
            config: 平台相关配置
        """
        self.config = config or {}

    @abstractmethod
    async def collect(
        self,
        keyword: str,
        limit: int = 50,
        language: str = "en",
    ) -> List[CollectedItem]:
        """
        采集数据

        Args:
            keyword: 搜索关键词
            limit: 采集数量限制
            language: 语言

        Returns:
            采集到的数据列表
        """
        pass

    def clean_text(self, text: Optional[str]) -> Optional[str]:
        """
        清洗文本

        Args:
            text: 原始文本

        Returns:
            清洗后的文本
        """
        if not text:
            return None
        # 去除首尾空白
        text = text.strip()
        # 过滤过短文本
        if len(text) < 10:
            return None
        return text

    def is_valid_item(self, item: CollectedItem) -> bool:
        """
        校验数据项是否有效

        Args:
            item: 数据项

        Returns:
            是否有效
        """
        # 至少有标题或内容
        return bool(item.title or item.content)


class CollectorRegistry:
    """采集器注册表"""

    _collectors: Dict[str, Type[BaseCollector]] = {}

    @classmethod
    def register(cls, platform: str, collector_class: Type[BaseCollector]):
        """注册采集器"""
        cls._collectors[platform] = collector_class

    @classmethod
    def get(cls, platform: str) -> Optional[Type[BaseCollector]]:
        """获取采集器类"""
        return cls._collectors.get(platform)

    @classmethod
    def get_instance(cls, platform: str, config: Dict = None) -> Optional[BaseCollector]:
        """获取采集器实例"""
        collector_class = cls.get(platform)
        if collector_class:
            return collector_class(config)
        return None

    @classmethod
    def list_platforms(cls) -> List[str]:
        """列出所有已注册平台"""
        return list(cls._collectors.keys())
```

---

### Task B2: Reddit采集器实现

**Files:**
- Create: `backend/app/collectors/reddit.py`

**Step 1: 创建 reddit.py**

```python
"""Reddit数据采集器"""
import asyncio
from datetime import datetime
from typing import List, Optional

import praw
from praw.models import Submission

from app.collectors.base import BaseCollector, CollectedItem
from app.config import get_settings


class RedditCollector(BaseCollector):
    """Reddit采集器，使用PRAW官方API"""

    platform_name = "reddit"

    def __init__(self, config: dict = None):
        super().__init__(config)
        settings = get_settings()

        self.reddit = praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
        )

    async def collect(
        self,
        keyword: str,
        limit: int = 50,
        language: str = "en",
    ) -> List[CollectedItem]:
        """
        采集Reddit数据

        Args:
            keyword: 搜索关键词
            limit: 采集数量
            language: 语言
        """
        items = []

        # 使用线程池执行同步PRAW调用
        loop = asyncio.get_event_loop()
        posts = await loop.run_in_executor(
            None,
            lambda: list(self.reddit.subreddit("all").search(
                keyword,
                sort="relevance",
                time_filter="week",
                limit=limit,
            ))
        )

        for post in posts:
            # 采集帖子
            post_item = self._parse_post(post)
            if post_item and self.is_valid_item(post_item):
                items.append(post_item)

            # 采集热门评论
            try:
                post.comments.replace_more(limit=0)
                top_comments = sorted(
                    post.comments.list()[:20],
                    key=lambda c: getattr(c, 'score', 0),
                    reverse=True
                )[:10]

                for comment in top_comments:
                    comment_item = self._parse_comment(comment, post)
                    if comment_item and self.is_valid_item(comment_item):
                        items.append(comment_item)
            except Exception:
                pass  # 评论采集失败不影响整体

        return items

    def _parse_post(self, post: Submission) -> Optional[CollectedItem]:
        """解析帖子"""
        try:
            content = self.clean_text(post.selftext) if post.selftext else None

            return CollectedItem(
                platform=self.platform_name,
                content_type="post",
                source_id=post.id,
                title=self.clean_text(post.title),
                content=content,
                author=str(post.author) if post.author else None,
                url=f"https://reddit.com{post.permalink}",
                metrics={
                    "upvotes": post.score,
                    "upvote_ratio": post.upvote_ratio,
                    "num_comments": post.num_comments,
                },
                extra_fields={
                    "subreddit": str(post.subreddit),
                    "is_video": post.is_video,
                },
                published_at=datetime.utcfromtimestamp(post.created_utc),
            )
        except Exception:
            return None

    def _parse_comment(self, comment, post: Submission) -> Optional[CollectedItem]:
        """解析评论"""
        try:
            content = self.clean_text(comment.body)
            if not content or content in ["[deleted]", "[removed]"]:
                return None

            # 过滤bot
            author = str(comment.author) if comment.author else None
            if author and "bot" in author.lower():
                return None

            return CollectedItem(
                platform=self.platform_name,
                content_type="comment",
                source_id=comment.id,
                title=None,
                content=content,
                author=author,
                url=f"https://reddit.com{post.permalink}{comment.id}",
                metrics={
                    "upvotes": comment.score,
                },
                extra_fields={
                    "post_id": post.id,
                    "subreddit": str(post.subreddit),
                },
                published_at=datetime.utcfromtimestamp(comment.created_utc),
            )
        except Exception:
            return None
```

---

### Task B3: YouTube采集器实现

**Files:**
- Create: `backend/app/collectors/youtube.py`

**Step 1: 创建 youtube.py**

```python
"""YouTube数据采集器"""
from datetime import datetime
from typing import List, Optional

from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

from app.collectors.base import BaseCollector, CollectedItem
from app.config import get_settings


class YouTubeCollector(BaseCollector):
    """YouTube采集器，使用官方API + youtube-transcript-api"""

    platform_name = "youtube"

    def __init__(self, config: dict = None):
        super().__init__(config)
        settings = get_settings()

        self.youtube = build(
            "youtube", "v3",
            developerKey=settings.youtube_api_key,
        )

    async def collect(
        self,
        keyword: str,
        limit: int = 50,
        language: str = "en",
    ) -> List[CollectedItem]:
        """
        采集YouTube数据

        Args:
            keyword: 搜索关键词
            limit: 采集数量（视频数，每个视频会产生多条数据）
            language: 语言
        """
        items = []
        video_limit = min(limit // 5, 10)  # 每个视频约产生5条数据

        # 搜索视频
        search_response = self.youtube.search().list(
            q=keyword,
            part="snippet",
            type="video",
            maxResults=video_limit,
            order="relevance",
            relevanceLanguage=language,
        ).execute()

        video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]

        if not video_ids:
            return items

        # 获取视频详情
        videos_response = self.youtube.videos().list(
            part="snippet,statistics",
            id=",".join(video_ids),
        ).execute()

        for video in videos_response.get("items", []):
            # 采集视频信息
            video_item = self._parse_video(video)
            if video_item and self.is_valid_item(video_item):
                items.append(video_item)

            # 采集字幕
            transcript_items = self._get_transcript(video["id"], language)
            items.extend(transcript_items)

        return items

    def _parse_video(self, video: dict) -> Optional[CollectedItem]:
        """解析视频信息"""
        try:
            snippet = video["snippet"]
            statistics = video.get("statistics", {})

            return CollectedItem(
                platform=self.platform_name,
                content_type="video",
                source_id=video["id"],
                title=self.clean_text(snippet.get("title")),
                content=self.clean_text(snippet.get("description")),
                author=snippet.get("channelTitle"),
                url=f"https://www.youtube.com/watch?v={video['id']}",
                metrics={
                    "views": int(statistics.get("viewCount", 0)),
                    "likes": int(statistics.get("likeCount", 0)),
                    "comments": int(statistics.get("commentCount", 0)),
                },
                extra_fields={
                    "channel_id": snippet.get("channelId"),
                    "tags": snippet.get("tags", []),
                },
                published_at=datetime.fromisoformat(
                    snippet["publishedAt"].replace("Z", "+00:00")
                ),
            )
        except Exception:
            return None

    def _get_transcript(self, video_id: str, language: str) -> List[CollectedItem]:
        """获取视频字幕"""
        items = []

        try:
            # 尝试获取字幕
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # 优先获取指定语言，否则获取自动生成的
            try:
                transcript = transcript_list.find_transcript([language])
            except NoTranscriptFound:
                try:
                    transcript = transcript_list.find_generated_transcript([language, "en"])
                except NoTranscriptFound:
                    return items

            # 获取字幕内容
            transcript_data = transcript.fetch()

            # 将字幕分段（每5分钟一段）
            segments = self._segment_transcript(transcript_data, video_id)
            items.extend(segments)

        except (TranscriptsDisabled, VideoUnavailable):
            pass  # 字幕不可用，静默处理
        except Exception:
            pass

        return items

    def _segment_transcript(
        self,
        transcript_data: List[dict],
        video_id: str,
        segment_duration: int = 300,  # 5分钟
    ) -> List[CollectedItem]:
        """
        将字幕分段

        Args:
            transcript_data: 字幕数据
            video_id: 视频ID
            segment_duration: 分段时长（秒）
        """
        items = []
        current_segment = []
        current_start = 0
        segment_index = 0

        for entry in transcript_data:
            start_time = entry.get("start", 0)
            text = entry.get("text", "").strip()

            if not text:
                continue

            # 检查是否需要开始新段
            if start_time - current_start >= segment_duration and current_segment:
                # 保存当前段
                segment_text = " ".join(current_segment)
                if len(segment_text) >= 50:  # 过滤过短的段
                    items.append(CollectedItem(
                        platform=self.platform_name,
                        content_type="transcript",
                        source_id=f"{video_id}_seg_{segment_index}",
                        title=None,
                        content=self.clean_text(segment_text),
                        author=None,
                        url=f"https://www.youtube.com/watch?v={video_id}&t={int(current_start)}",
                        metrics={},
                        extra_fields={
                            "video_id": video_id,
                            "segment_index": segment_index,
                            "start_time": current_start,
                            "end_time": start_time,
                        },
                        published_at=None,
                    ))

                # 重置
                current_segment = []
                current_start = start_time
                segment_index += 1

            current_segment.append(text)

        # 保存最后一段
        if current_segment:
            segment_text = " ".join(current_segment)
            if len(segment_text) >= 50:
                items.append(CollectedItem(
                    platform=self.platform_name,
                    content_type="transcript",
                    source_id=f"{video_id}_seg_{segment_index}",
                    title=None,
                    content=self.clean_text(segment_text),
                    author=None,
                    url=f"https://www.youtube.com/watch?v={video_id}&t={int(current_start)}",
                    metrics={},
                    extra_fields={
                        "video_id": video_id,
                        "segment_index": segment_index,
                        "start_time": current_start,
                    },
                    published_at=None,
                ))

        return items
```

---

## Module C: AI分析模块

### Task C1: LLM客户端封装

**Files:**
- Create: `backend/app/analyzers/__init__.py`
- Create: `backend/app/analyzers/llm_client.py`

**Step 1: 创建 analyzers/__init__.py**

```python
"""AI分析模块"""
from app.analyzers.llm_client import LLMClient
from app.analyzers.preprocessor import DataPreprocessor
from app.analyzers.sentiment import SentimentAnalyzer
from app.analyzers.clustering import ClusteringAnalyzer
from app.analyzers.mermaid import MermaidGenerator

__all__ = [
    "LLMClient",
    "DataPreprocessor",
    "SentimentAnalyzer",
    "ClusteringAnalyzer",
    "MermaidGenerator",
]
```

**Step 2: 创建 llm_client.py**

```python
"""LLM客户端封装"""
import json
from typing import Optional, Dict, Any, List

from app.config import get_settings
from openai import AsyncOpenAI


class LLMClient:
    """LLM API客户端"""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_api_base_url
        self.timeout = 60.0
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url or None,
            timeout=self.timeout,
        )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: Optional[str] = None,
    ) -> str:
        """
        发送聊天请求

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式 ("json" 或 None)

        Returns:
            LLM响应文本
        """
        payload = {
            "model": "gpt-4o-mini",  # 根据实际API调整
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(**payload)
        return response.choices[0].message.content or ""

    async def analyze_json(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful assistant that responds in JSON format.",
    ) -> Dict[str, Any]:
        """
        发送请求并解析JSON响应

        Args:
            prompt: 用户提示
            system_prompt: 系统提示

        Returns:
            解析后的JSON对象
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        response = await self.chat(messages, response_format="json")
        return json.loads(response)
```

---

### Task C2: 数据预处理器

**Files:**
- Create: `backend/app/analyzers/preprocessor.py`

**Step 1: 创建 preprocessor.py**

```python
"""数据预处理器，过滤脏数据"""
import re
from typing import List, Optional

from langdetect import detect, LangDetectException

from app.collectors.base import CollectedItem


class DataPreprocessor:
    """数据预处理器"""

    # 广告关键词
    AD_PATTERNS = [
        r"buy\s+now",
        r"click\s+here",
        r"limited\s+offer",
        r"subscribe\s+to",
        r"follow\s+me",
        r"check\s+out\s+my",
        r"promo\s*code",
        r"discount",
        r"free\s+shipping",
        r"http[s]?://[^\s]+",  # URL过滤（可选）
    ]

    # Bot关键词
    BOT_PATTERNS = [
        r"bot$",
        r"automoderator",
        r"^auto",
        r"_bot$",
    ]

    def __init__(
        self,
        min_length: int = 10,
        max_length: int = 5000,
        target_language: str = "en",
        filter_ads: bool = True,
        filter_bots: bool = True,
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.target_language = target_language
        self.filter_ads = filter_ads
        self.filter_bots = filter_bots

        # 编译正则
        self.ad_regex = re.compile(
            "|".join(self.AD_PATTERNS),
            re.IGNORECASE,
        )
        self.bot_regex = re.compile(
            "|".join(self.BOT_PATTERNS),
            re.IGNORECASE,
        )

    def preprocess(self, items: List[CollectedItem]) -> List[CollectedItem]:
        """
        预处理数据列表

        Args:
            items: 原始数据列表

        Returns:
            过滤后的数据列表
        """
        result = []
        seen_ids = set()

        for item in items:
            # 去重
            if item.source_id in seen_ids:
                continue

            # 校验
            if not self._is_valid(item):
                continue

            seen_ids.add(item.source_id)
            result.append(item)

        # 按互动数排序（高赞优先）
        result.sort(key=self._get_engagement_score, reverse=True)

        return result

    def _is_valid(self, item: CollectedItem) -> bool:
        """校验数据项是否有效"""
        text = item.content or item.title or ""

        # 长度检查
        if len(text) < self.min_length:
            return False
        if len(text) > self.max_length:
            return False

        # Bot过滤
        if self.filter_bots and item.author:
            if self.bot_regex.search(item.author):
                return False

        # 广告过滤
        if self.filter_ads:
            if self.ad_regex.search(text):
                return False

        # 语言检测（对较长文本）
        if len(text) > 50:
            try:
                detected_lang = detect(text)
                if self.target_language == "en" and detected_lang not in ["en"]:
                    return False
                if self.target_language == "zh" and detected_lang not in ["zh-cn", "zh-tw", "zh"]:
                    return False
            except LangDetectException:
                pass  # 检测失败时保留

        return True

    def _get_engagement_score(self, item: CollectedItem) -> int:
        """计算互动分数"""
        metrics = item.metrics or {}
        score = 0

        # Reddit
        score += metrics.get("upvotes", 0)
        score += metrics.get("num_comments", 0) * 2

        # YouTube
        score += metrics.get("views", 0) // 1000
        score += metrics.get("likes", 0) * 10

        return score

    def extract_top_items(
        self,
        items: List[CollectedItem],
        limit: int = 50,
        min_engagement: int = 5,
    ) -> List[CollectedItem]:
        """
        提取高质量数据项

        Args:
            items: 预处理后的数据列表
            limit: 数量限制
            min_engagement: 最低互动分数

        Returns:
            高质量数据列表
        """
        filtered = [
            item for item in items
            if self._get_engagement_score(item) >= min_engagement
        ]

        return filtered[:limit]
```

---

### Task C3: 情感分析器

**Files:**
- Create: `backend/app/analyzers/sentiment.py`

**Step 1: 创建 sentiment.py**

```python
"""情感分析器"""
from typing import List, Dict, Any

from app.analyzers.llm_client import LLMClient
from app.collectors.base import CollectedItem


class SentimentAnalyzer:
    """情感分析器，使用LLM进行情感打分"""

    SYSTEM_PROMPT = """You are a sentiment analysis expert. Analyze the given texts and provide sentiment scores.

For each text, provide a score from 0-100:
- 0-20: Very negative (angry, frustrated, disappointed)
- 21-40: Negative (critical, dissatisfied)
- 41-60: Neutral (factual, mixed feelings)
- 61-80: Positive (satisfied, approving)
- 81-100: Very positive (enthusiastic, highly praising)

Consider the overall tone, word choice, and context.
Respond in JSON format with a list of scores."""

    def __init__(self):
        self.llm = LLMClient()

    async def analyze_batch(
        self,
        items: List[CollectedItem],
        batch_size: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        批量分析情感

        Args:
            items: 数据列表
            batch_size: 每批数量

        Returns:
            分析结果列表 [{"source_id": "...", "score": 75, "snippets": [...]}]
        """
        results = []

        # 分批处理
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = await self._analyze_single_batch(batch)
            results.extend(batch_results)

        return results

    async def _analyze_single_batch(
        self,
        items: List[CollectedItem],
    ) -> List[Dict[str, Any]]:
        """分析单个批次"""
        # 构建提示
        texts = []
        for idx, item in enumerate(items):
            text = item.content or item.title or ""
            # 截断过长文本
            if len(text) > 500:
                text = text[:500] + "..."
            texts.append(f"[{idx + 1}] {text}")

        prompt = f"""Analyze the sentiment of the following {len(texts)} texts about a product/topic.

Texts:
{chr(10).join(texts)}

Respond with a JSON object in this format:
{{
    "scores": [
        {{"index": 1, "score": 75, "key_phrases": ["positive phrase 1", "positive phrase 2"]}},
        {{"index": 2, "score": 45, "key_phrases": ["neutral phrase"]}}
    ]
}}"""

        try:
            response = await self.llm.analyze_json(prompt, self.SYSTEM_PROMPT)
            scores_data = response.get("scores", [])

            results = []
            for item, score_info in zip(items, scores_data):
                results.append({
                    "source_id": item.source_id,
                    "score": score_info.get("score", 50),
                    "key_phrases": score_info.get("key_phrases", []),
                    "platform": item.platform,
                    "engagement": item.metrics.get("upvotes", 0) + item.metrics.get("likes", 0),
                })

            return results

        except Exception as e:
            # 失败时返回默认分数
            return [
                {
                    "source_id": item.source_id,
                    "score": 50,
                    "key_phrases": [],
                    "platform": item.platform,
                    "engagement": 0,
                }
                for item in items
            ]

    def calculate_weighted_score(
        self,
        results: List[Dict[str, Any]],
    ) -> int:
        """
        计算加权平均情感分数

        Args:
            results: 分析结果列表

        Returns:
            加权平均分数 (0-100)
        """
        if not results:
            return 50

        total_weight = 0
        weighted_sum = 0

        for r in results:
            # 基于互动数加权
            weight = max(1, r.get("engagement", 0) // 10 + 1)
            weighted_sum += r["score"] * weight
            total_weight += weight

        return round(weighted_sum / total_weight) if total_weight > 0 else 50
```

---

### Task C4: 观点聚类和摘要生成

**Files:**
- Create: `backend/app/analyzers/clustering.py`

**Step 1: 创建 clustering.py**

```python
"""观点聚类和摘要生成"""
from typing import List, Dict, Any

from app.analyzers.llm_client import LLMClient


class ClusteringAnalyzer:
    """观点聚类和摘要生成器"""

    SYSTEM_PROMPT = """You are an expert at analyzing public opinions and discussions.
Your task is to:
1. Identify the 3 most important/controversial discussion points
2. Generate a concise, readable summary of public sentiment
3. Extract key themes and patterns from the discussions

Be objective and balanced in your analysis.
Respond in JSON format."""

    def __init__(self):
        self.llm = LLMClient()

    async def analyze(
        self,
        sentiment_results: List[Dict[str, Any]],
        items_text: List[str],
        keyword: str,
    ) -> Dict[str, Any]:
        """
        分析观点聚类和生成摘要

        Args:
            sentiment_results: 情感分析结果
            items_text: 原始文本列表
            keyword: 分析的关键词

        Returns:
            {
                "key_opinions": [...],
                "summary": "..."
            }
        """
        # 提取关键短语
        all_phrases = []
        for r in sentiment_results:
            all_phrases.extend(r.get("key_phrases", []))

        # 构建提示
        prompt = f"""Analyze public discussions about "{keyword}".

Sample texts (truncated):
{chr(10).join(items_text[:20])}

Key phrases extracted from sentiment analysis:
{', '.join(all_phrases[:50])}

Overall sentiment distribution:
- Positive (score >= 60): {len([r for r in sentiment_results if r['score'] >= 60])} items
- Neutral (40-59): {len([r for r in sentiment_results if 40 <= r['score'] < 60])} items
- Negative (< 40): {len([r for r in sentiment_results if r['score'] < 40])} items

Tasks:
1. Identify exactly 3 key discussion points/opinions that people are talking about
2. Write a 2-3 sentence summary of the overall public sentiment

Respond with JSON in this exact format:
{{
    "key_opinions": [
        {{"title": "Short title (5 words max)", "description": "1-2 sentence explanation"}},
        {{"title": "...", "description": "..."}},
        {{"title": "...", "description": "..."}}
    ],
    "summary": "2-3 sentence summary of what people think about {keyword}..."
}}"""

        try:
            response = await self.llm.analyze_json(prompt, self.SYSTEM_PROMPT)

            return {
                "key_opinions": response.get("key_opinions", []),
                "summary": response.get("summary", f"Analysis of {keyword} is currently unavailable."),
            }

        except Exception as e:
            return {
                "key_opinions": [
                    {"title": "Analysis Error", "description": "Unable to cluster opinions at this time."}
                ],
                "summary": f"Unable to generate summary for {keyword}.",
            }
```

---

### Task C5: 思维导图生成器

**Files:**
- Create: `backend/app/analyzers/mermaid.py`

**Step 1: 创建 mermaid.py**

```python
"""Mermaid思维导图生成器"""
from typing import List, Dict, Any

from app.analyzers.llm_client import LLMClient


class MermaidGenerator:
    """生成Mermaid格式的思维导图"""

    SYSTEM_PROMPT = """You are an expert at creating clear, well-structured mind maps.
Generate Mermaid mindmap syntax that visualizes the key opinions and themes.
Use proper Mermaid mindmap syntax with indentation.
Keep labels concise (under 30 characters each)."""

    def __init__(self):
        self.llm = LLMClient()

    async def generate(
        self,
        keyword: str,
        key_opinions: List[Dict[str, str]],
        sentiment_score: int,
    ) -> str:
        """
        生成思维导图代码

        Args:
            keyword: 分析关键词
            key_opinions: 核心观点列表
            sentiment_score: 情感分数

        Returns:
            Mermaid格式的思维导图代码
        """
        # 构建提示
        opinions_text = "\n".join([
            f"- {op['title']}: {op['description']}"
            for op in key_opinions
        ])

        sentiment_label = self._get_sentiment_label(sentiment_score)

        prompt = f"""Create a Mermaid mindmap for the topic "{keyword}".

Key opinions:
{opinions_text}

Overall sentiment: {sentiment_label} ({sentiment_score}/100)

Generate a Mermaid mindmap with:
1. Root node: the keyword
2. Branch for overall sentiment
3. Branches for each key opinion with 2-3 sub-points

Use this exact format:
```mermaid
mindmap
  root(({keyword}))
    Sentiment
      {sentiment_label}
    Opinion 1
      Sub-point 1
      Sub-point 2
    Opinion 2
      Sub-point 1
```

Only output the mermaid code, no explanation."""

        try:
            response = await self.llm.chat([
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ], temperature=0.5, max_tokens=1000)

            # 提取mermaid代码
            code = self._extract_mermaid_code(response)
            return code

        except Exception:
            # 返回默认模板
            return self._generate_fallback(keyword, key_opinions, sentiment_label)

    def _get_sentiment_label(self, score: int) -> str:
        """获取情感标签"""
        if score >= 80:
            return "Very Positive"
        elif score >= 60:
            return "Positive"
        elif score >= 40:
            return "Neutral"
        elif score >= 20:
            return "Negative"
        else:
            return "Very Negative"

    def _extract_mermaid_code(self, response: str) -> str:
        """从响应中提取mermaid代码"""
        # 尝试提取```mermaid块
        if "```mermaid" in response:
            start = response.find("```mermaid") + len("```mermaid")
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()

        # 尝试提取mindmap开头
        if "mindmap" in response:
            start = response.find("mindmap")
            return response[start:].strip()

        return response.strip()

    def _generate_fallback(
        self,
        keyword: str,
        key_opinions: List[Dict[str, str]],
        sentiment_label: str,
    ) -> str:
        """生成备用思维导图"""
        lines = [
            "mindmap",
            f"  root(({keyword}))",
            "    Sentiment",
            f"      {sentiment_label}",
        ]

        for i, op in enumerate(key_opinions[:3], 1):
            title = op.get("title", f"Point {i}")[:25]
            lines.append(f"    {title}")
            desc = op.get("description", "")[:50]
            if desc:
                lines.append(f"      {desc}")

        return "\n".join(lines)
```

---

## Module D: Celery任务实现

### Task D1: 采集任务

**Files:**
- Create: `backend/app/workers/collect_tasks.py`

**Step 1: 创建 collect_tasks.py**

```python
"""采集任务"""
import asyncio
from typing import List

from celery import shared_task
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Task, TaskStatus, RawData, Platform, ContentType
from app.collectors import CollectorRegistry
from app.collectors.base import CollectedItem


@shared_task(bind=True, max_retries=3)
def collect_and_analyze(self, task_id: str):
    """
    采集并分析任务

    Args:
        task_id: 任务ID
    """
    db = SessionLocal()

    try:
        # 获取任务
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": "Task not found"}

        # 更新状态
        task.status = TaskStatus.RUNNING
        task.progress = 0
        db.commit()

        # 执行采集
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            all_items = loop.run_until_complete(
                _collect_all_platforms(task.keyword, task.limit_count, task.language, task.platforms)
            )
        finally:
            loop.close()

        # 保存原始数据
        _save_raw_data(db, task.id, all_items)
        task.progress = 50
        db.commit()

        # 触发分析任务
        from app.workers.analyze_tasks import analyze_task
        analyze_task.delay(task_id)

        return {"status": "collecting_done", "items_count": len(all_items)}

    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        db.commit()
        raise
    finally:
        db.close()


async def _collect_all_platforms(
    keyword: str,
    limit: int,
    language: str,
    platforms: List[str],
) -> List[CollectedItem]:
    """并发采集所有平台"""
    from app.config import get_settings
    settings = get_settings()

    all_items = []

    for platform in platforms:
        collector = CollectorRegistry.get_instance(
            platform,
            config={
                "reddit_client_id": settings.reddit_client_id,
                "reddit_client_secret": settings.reddit_client_secret,
                "youtube_api_key": settings.youtube_api_key,
            }
        )

        if collector:
            try:
                items = await collector.collect(keyword, limit // len(platforms), language)
                all_items.extend(items)
            except Exception as e:
                print(f"Error collecting from {platform}: {e}")

    return all_items


def _save_raw_data(db: Session, task_id: str, items: List[CollectedItem]):
    """保存原始数据到数据库"""
    for item in items:
        raw_data = RawData(
            task_id=task_id,
            platform=Platform(item.platform),
            content_type=ContentType(item.content_type),
            source_id=item.source_id,
            title=item.title,
            content=item.content,
            author=item.author,
            url=item.url,
            metrics=item.metrics,
            extra_fields=item.extra_fields,
            published_at=item.published_at,
        )
        db.merge(raw_data)  # merge处理重复

    db.commit()
```

---

### Task D2: 分析任务

**Files:**
- Create: `backend/app/workers/analyze_tasks.py`

**Step 1: 创建 analyze_tasks.py**

```python
"""AI分析任务"""
import asyncio
from collections import Counter

from celery import shared_task

from app.database import SessionLocal
from app.models import Task, TaskStatus, RawData, AnalysisResult, Alert
from app.collectors.base import CollectedItem
from app.analyzers import (
    DataPreprocessor,
    SentimentAnalyzer,
    ClusteringAnalyzer,
    MermaidGenerator,
)


@shared_task(bind=True, max_retries=2)
def analyze_task(self, task_id: str):
    """
    执行AI分析

    Args:
        task_id: 任务ID
    """
    db = SessionLocal()

    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": "Task not found"}

        # 获取原始数据
        raw_data_list = db.query(RawData).filter(RawData.task_id == task_id).all()

        if not raw_data_list:
            task.status = TaskStatus.FAILED
            task.error_message = "No data collected"
            db.commit()
            return {"error": "No data"}

        # 转换为CollectedItem
        items = [
            CollectedItem(
                platform=r.platform.value,
                content_type=r.content_type.value,
                source_id=r.source_id,
                title=r.title,
                content=r.content,
                author=r.author,
                url=r.url,
                metrics=r.metrics or {},
                extra_fields=r.extra_fields or {},
                published_at=r.published_at,
            )
            for r in raw_data_list
        ]

        # 执行分析
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(_run_analysis(task.keyword, items))
        finally:
            loop.close()

        # 计算平台分布
        platform_counts = Counter(item.platform for item in items)
        total = len(items)
        platform_distribution = {
            p: round(c / total * 100) for p, c in platform_counts.items()
        }

        # 计算热度
        heat_index = _calculate_heat_index(items)

        # 保存分析结果
        analysis_result = AnalysisResult(
            task_id=task_id,
            sentiment_score=result["sentiment_score"],
            key_opinions=result["key_opinions"],
            summary=result["summary"],
            mermaid_code=result["mermaid_code"],
            heat_index=heat_index,
            total_items=total,
            platform_distribution=platform_distribution,
        )
        db.add(analysis_result)

        # 更新任务状态
        task.status = TaskStatus.COMPLETED
        task.progress = 100
        db.commit()

        # 检查是否需要触发报警（用于订阅任务）
        _check_and_create_alert(db, task_id, result["sentiment_score"])

        return {
            "status": "completed",
            "sentiment_score": result["sentiment_score"],
        }

    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        db.commit()
        raise
    finally:
        db.close()


async def _run_analysis(keyword: str, items: list) -> dict:
    """执行完整分析流程"""
    # 1. 预处理
    preprocessor = DataPreprocessor()
    cleaned_items = preprocessor.preprocess(items)
    top_items = preprocessor.extract_top_items(cleaned_items, limit=50)

    # 2. 情感分析 (Map)
    sentiment_analyzer = SentimentAnalyzer()
    sentiment_results = await sentiment_analyzer.analyze_batch(top_items)

    # 3. 计算加权分数
    sentiment_score = sentiment_analyzer.calculate_weighted_score(sentiment_results)

    # 4. 观点聚类和摘要 (Reduce)
    clustering_analyzer = ClusteringAnalyzer()
    items_text = [
        (item.content or item.title or "")[:200]
        for item in top_items
    ]
    clustering_result = await clustering_analyzer.analyze(
        sentiment_results, items_text, keyword
    )

    # 5. 生成思维导图
    mermaid_generator = MermaidGenerator()
    mermaid_code = await mermaid_generator.generate(
        keyword,
        clustering_result["key_opinions"],
        sentiment_score,
    )

    return {
        "sentiment_score": sentiment_score,
        "key_opinions": clustering_result["key_opinions"],
        "summary": clustering_result["summary"],
        "mermaid_code": mermaid_code,
    }


def _calculate_heat_index(items: list) -> float:
    """计算热度指数"""
    total_engagement = 0

    for item in items:
        metrics = item.metrics or {}
        total_engagement += metrics.get("upvotes", 0)
        total_engagement += metrics.get("likes", 0)
        total_engagement += metrics.get("views", 0) // 100
        total_engagement += metrics.get("num_comments", 0) * 5

    # 归一化到0-100
    heat = min(100, total_engagement / max(len(items), 1) / 10)
    return round(heat, 2)


def _check_and_create_alert(db, task_id: str, sentiment_score: int):
    """检查是否需要创建报警"""
    from app.models import Subscription

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return

    # 查找相关订阅
    subscription = db.query(Subscription).filter(
        Subscription.keyword == task.keyword,
        Subscription.is_active == True,
    ).first()

    if subscription and sentiment_score < subscription.alert_threshold:
        alert = Alert(
            subscription_id=subscription.id,
            task_id=task_id,
            sentiment_score=sentiment_score,
            alert_type="negative_sentiment",
        )
        db.add(alert)
        db.commit()
```

---

### Task D3: 定时任务 (已废弃)

**注意：此任务已被 APScheduler 替代，参见 Task A5.1**

**Files:**
- Create: `backend/app/workers/scheduled_tasks.py` (保留供参考，不再使用)

**Step 1: 创建 scheduled_tasks.py**

```python
"""定时任务 (已废弃)

注意：此模块已被 APScheduler 替代。
订阅任务的调度现在由 app/services/scheduler_service.py 管理。

保留此文件仅供参考，不再使用 Celery Beat 轮询机制。
新的实现支持：
- 实时 CRUD 订阅的定时任务
- 精确的时间调度
- 持久化到 PostgreSQL

参见：app/services/scheduler_service.py
"""
from datetime import datetime, timedelta

from celery import shared_task

from app.database import SessionLocal
from app.models import Subscription, Task, TaskStatus


# ==================== 已废弃 ====================
# 以下代码保留供参考，实际调度由 APScheduler 处理
# ==============================================

@shared_task
def check_subscriptions():
    """
    [已废弃] 检查并执行到期的订阅任务

    此任务已被 APScheduler 替代，不再通过 Celery Beat 调用。
    保留此函数仅供参考和回退使用。
    """
    db = SessionLocal()

    try:
        now = datetime.utcnow()

        due_subscriptions = db.query(Subscription).filter(
            Subscription.is_active == True,
            Subscription.next_run_at <= now,
        ).all()

        for subscription in due_subscriptions:
            task = Task(
                keyword=subscription.keyword,
                language=subscription.language,
                limit_count=50,
                platforms=subscription.platforms,
                status=TaskStatus.PENDING,
            )
            db.add(task)
            db.commit()
            db.refresh(task)

            from app.workers.collect_tasks import collect_and_analyze
            celery_task = collect_and_analyze.delay(str(task.id))

            task.celery_task_id = celery_task.id

            subscription.last_run_at = now
            subscription.next_run_at = now + timedelta(hours=subscription.interval_hours)

            db.commit()

        return {"checked": len(due_subscriptions), "timestamp": now.isoformat()}

    finally:
        db.close()
```

---

## 后续步骤

**Module E: Flutter前端** 将在后端API稳定后单独创建计划文档，包含：
- 项目初始化和依赖配置
- 数据模型和API服务
- 状态管理(Riverpod)
- 页面实现（首页、进度页、仪表盘页、数据页、订阅页）
- 组件实现（情感仪表盘、观点卡片、Mermaid渲染）

---

## 执行命令汇总

```bash
# 1. 创建虚拟环境
cd backend
python -m venv venv
venv\Scripts\activate  # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
copy .env.example .env
# 编辑 .env 填入实际配置

# 4. 初始化数据库（创建数据库与表）
python scripts/init_db.py
# 如需 Alembic 迁移，再执行：
# alembic revision --autogenerate -m "Initial migration"
# alembic upgrade head

# 5. 启动服务
# 终端1: API服务 (包含 APScheduler 调度器)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端2: Celery Worker (处理异步任务)
celery -A app.workers.celery_app worker --loglevel=info

# 注意：不再需要 Celery Beat，APScheduler 已集成到 FastAPI 应用中
# 定时任务调度由 APScheduler 在应用启动时自动管理
# 若使用多进程/多实例 API，建议仅在一个进程设置 SCHEDULER_ENABLED=true，
# 其余设置为 false，或将调度器独立部署为单独服务。
```
