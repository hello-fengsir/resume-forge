"""Dynamic model configuration — reads from DB with in-memory cache.

Usage:
    from app.model_config import get_active_model, refresh_model_cache, set_active_model

    model = await get_active_model("generate", db, user_id)   # async
    model = get_active_model_sync("generate")     # sync (uses cache)
"""

import os
import logging
from sqlalchemy import select
from app.models.system_config import SystemConfig
from app.models.api_key import ApiKey

logger = logging.getLogger(__name__)

# In-memory cache — populated at startup, refreshed on change
_cache: dict[str, str] = {}


def _env_default(key: str) -> str:
    """Fallback to env var."""
    return os.getenv(key, "")


def get_active_model_sync(purpose: str) -> str:
    """Synchronous read from cache (for non-async contexts like engine init)."""
    cache_key = f"{purpose}_model"
    if cache_key in _cache:
        return _cache[cache_key]
    # Fall back to env
    env_key = f"{purpose.upper()}_MODEL"
    return _env_default(env_key) or "deepseek-v4-pro"


async def get_active_model(purpose: str, db=None, user_id: str = None) -> str:
    """Async read: checks user's API key first, then cache, then DB, then env.
    
    返回 None 表示未配置模型（用户没有 API Key）
    """
    # 1. 如果提供了 user_id，优先从用户的 API Key 中获取
    if user_id and db is not None:
        try:
            result = await db.execute(
                select(ApiKey).where(
                    ApiKey.user_id == user_id,
                    ApiKey.is_active == True
                ).order_by(ApiKey.created_at.desc()).limit(1)
            )
            api_key = result.scalar_one_or_none()
            if api_key and api_key.model:
                return api_key.model
            else:
                # 用户没有配置 API Key，返回 None 表示未配置
                return None
        except Exception as e:
            logger.warning(f"Failed to read user API key: {e}")

    # 2. 检查内存缓存（用于全局配置）
    cache_key = f"{purpose}_model"
    if cache_key in _cache:
        return _cache[cache_key]

    # 3. 从数据库 system_configs 表读取
    if db is not None:
        try:
            result = await db.execute(
                select(SystemConfig).where(SystemConfig.key == cache_key)
            )
            row = result.scalar_one_or_none()
            if row and row.value:
                _cache[cache_key] = row.value
                return row.value
        except Exception as e:
            logger.warning(f"Failed to read model config from DB: {e}")

    # 4. 环境变量 fallback
    env_key = f"{purpose.upper()}_MODEL"
    return _env_default(env_key) or "deepseek-v4-pro"


async def refresh_model_cache(db) -> None:
    """Refresh the in-memory cache from DB."""
    try:
        for purpose in ("generate", "review"):
            result = await db.execute(
                select(SystemConfig).where(SystemConfig.key == f"{purpose}_model")
            )
            row = result.scalar_one_or_none()
            if row and row.value:
                _cache[f"{purpose}_model"] = row.value
            else:
                env_key = f"{purpose.upper()}_MODEL"
                _cache[f"{purpose}_model"] = _env_default(env_key) or "deepseek-v4-pro"
    except Exception as e:
        logger.warning(f"Failed to refresh model cache: {e}")


async def set_active_model(purpose: str, model: str, db) -> None:
    """Update the active model for a purpose (generate/review)."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    cache_key = f"{purpose}_model"
    stmt = pg_insert(SystemConfig).values(
        key=cache_key,
        value=model,
    ).on_conflict_do_update(
        index_elements=["key"],
        set_={"value": model},
    )
    await db.execute(stmt)
    await db.commit()
    _cache[cache_key] = model
    logger.info(f"Active {purpose} model set to: {model}")
