from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine, init_db
from app.model_config import refresh_model_cache
from app.routers import info, jobs, resumes, reviews, upload, config
from app.auth.auth_router import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Init model cache from DB
    async with engine.begin() as conn:
        pass  # engine is async, use session for cache refresh
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Resume Forge API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(info.router, prefix=f"{settings.API_PREFIX}/info", tags=["信息统计"])
    app.include_router(jobs.router, prefix=f"{settings.API_PREFIX}/jobs", tags=["应聘分析"])
    app.include_router(resumes.router, prefix=f"{settings.API_PREFIX}/resumes", tags=["制作简历"])
    app.include_router(reviews.router, prefix=f"{settings.API_PREFIX}/reviews", tags=["质量评估"])
    app.include_router(upload.router, prefix=f"{settings.API_PREFIX}/info", tags=["附件上传"])
    app.include_router(auth_router, prefix=f"{settings.API_PREFIX}/auth", tags=["认证"])
    app.include_router(config.router, prefix=f"{settings.API_PREFIX}/config", tags=["系统配置"])

    @app.get("/health")
    @app.get("/api/health")
    async def api_health():
        return {"status": "ok"}
    async def health():
        return {"status": "ok"}

    return app


app = create_app()