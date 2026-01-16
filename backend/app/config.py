"""应用配置管理，从环境变量加载配置"""
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""

    # Database
    database_url: str

    # Redis
    redis_url: str

    # Reddit API (可选，未配置时使用HTTP fallback模式)
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "AI-Opinion-Monitor/1.0"

    # YouTube API
    youtube_api_key: str

    # LLM API
    llm_api_key: str
    llm_api_base_url: str
    llm_model: str

    # API Auth
    api_key: str = ""

    # X (Twitter) via Playwright + cookies
    x_accounts_path: str = ""
    x_accounts_json: str = ""
    x_headless: bool = True
    x_proxy: str = ""
    x_user_agent: str = ""
    x_timeout_ms: int = 30000
    x_account_error_limit: int = 3

    # App Config
    debug: bool
    log_level: str
    analysis_text_truncation_limit: int = 200

    # Scheduler
    scheduler_enabled: bool

    # Opinion clustering (adaptive)
    opinion_count_min: int = 2
    opinion_count_max: int = 6
    opinion_count_thresholds: str = "12,24,36,48"

    # Semantic sampling (local embedding)
    semantic_sampling_model: str = "intfloat/multilingual-e5-small"
    semantic_sampling_max_items: int = 200
    semantic_sampling_target_count: int = 50
    semantic_sampling_k_min: int = 3
    semantic_sampling_k_max: int = 10
    semantic_sampling_outlier_ratio: float = 0.1
    semantic_sampling_text_max_length: int = 400
    semantic_sampling_batch_size: int = 64

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            env_settings,
            dotenv_settings,
            init_settings,
            file_secret_settings,
        )


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
