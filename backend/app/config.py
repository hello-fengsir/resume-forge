import os
from functools import lru_cache


class Settings:
    # 数据库
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://resume:resume-forge-2026@database:5432/resume_forge",
    )

    # AI Provider
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # 模型选择
    GENERATE_MODEL: str = os.getenv("GENERATE_MODEL", "deepseek-v4-pro")
    REVIEW_MODEL: str = os.getenv("REVIEW_MODEL", "deepseek-v4-pro")

    # 文件上传
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/app/uploads")
    MAX_UPLOAD_SIZE: int = 20 * 1024 * 1024  # 20MB

    # API
    API_PREFIX: str = "/api"
    CORS_ORIGINS: list[str] = ["*"]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
