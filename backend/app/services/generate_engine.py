"""简历生成引擎 — 动态读取 API Key"""
import json, re
from sqlalchemy import select
from openai import AsyncOpenAI
from app.config import get_settings
from app import model_config as _mc
from app.models.api_key import ApiKey
from app.routers.config import PROVIDERS, _decrypt

class GenerateEngine:
    def __init__(self):
        pass  # No hardcoded client — get it dynamically per request

    async def _get_client(self, db, user_id: str = None) -> AsyncOpenAI:
        """Build an AsyncOpenAI client from the user's active API key in the database."""
        model = await _mc.get_active_model("generate", db, user_id)
        
        # 如果用户没有配置 API Key，抛出异常
        if model is None:
            raise ValueError("未配置模型，请先在设置中添加 API Key")
        
        # 优先使用用户的 API Key
        if user_id:
            result = await db.execute(
                select(ApiKey).where(
                    ApiKey.user_id == user_id,
                    ApiKey.is_active == True,
                ).order_by(ApiKey.created_at.desc())
            )
            key_row = result.scalars().first()
            if key_row:
                api_key = _decrypt(key_row.encrypted_key)
                provider_info = PROVIDERS.get(key_row.provider, {})
                base_url = provider_info.get("base_url", "https://api.deepseek.com")
                return AsyncOpenAI(api_key=api_key, base_url=base_url)

        # Fallback: 任意活跃的 key
        result2 = await db.execute(
            select(ApiKey).where(ApiKey.is_active == True).order_by(ApiKey.created_at.desc())
        )
        key_row = result2.scalars().first()
        if not key_row:
            s = get_settings()
            return AsyncOpenAI(api_key=s.DEEPSEEK_API_KEY, base_url=s.DEEPSEEK_BASE_URL)

        api_key = _decrypt(key_row.encrypted_key)
        provider_info = PROVIDERS.get(key_row.provider, {})
        base_url = provider_info.get("base_url", "https://api.deepseek.com")
        return AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def _call(self, system: str, user: str, db, max_tokens=3072, user_id: str = None) -> str:
        client = await self._get_client(db, user_id)
        model = await _mc.get_active_model("generate", db, user_id)
        resp = await client.chat.completions.create(
            model=model, max_tokens=max_tokens,
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
        )
        text = resp.choices[0].message.content or ""
        # Strip remaining Markdown formatting as safety net
        import re as _re
        text = _re.sub(r'^#{1,6}\s+', '', text, flags=_re.MULTILINE)  # headings
        text = _re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)  # bold/italic
        text = _re.sub(r'^[\*\-]\s+', '', text, flags=_re.MULTILINE)  # list markers
        return text

    async def gen_core(self, info: str, job: str, focus: list, db=None, user_id: str = None) -> str:
        f = "\n".join(f"- {x}" for x in focus)
        return await self._call("撰写简历核心优势，含3-5条含量化数据。纯文本格式，禁止Markdown符号。", f"岗位：{job}\n重点：{f}\n信息：{info}", db, user_id=user_id)

    async def gen_work(self, info: str, job: str, db=None, user_id: str = None) -> str:
        return await self._call("撰写工作经历，STAR法则，量化优先。纯文本格式，禁止Markdown符号。", f"岗位：{job}\n信息：{info}", db, user_id=user_id)

    async def gen_projects(self, info: str, job: str, db=None, user_id: str = None) -> str:
        return await self._call("撰写项目经验，突出技术栈和量化成果。纯文本格式，禁止Markdown符号。", f"岗位：{job}\n信息：{info}", db, user_id=user_id)

    async def gen_education(self, info: str, db=None, user_id: str = None) -> str:
        return await self._call("提取教育经历。纯文本格式，禁止Markdown符号。", info, db, 1024, user_id=user_id)

    async def merge(self, core: str, work: str, projects: str, edu: str, job: str, db=None, user_id: str = None) -> str:
        return await self._call("融合为完整简历。使用纯文本格式，禁止任何Markdown符号（如*、-、#、**等），不用标题标记，用自然段落。", f"核心优势：{core}\n工作经历：{work}\n项目经验：{projects}\n教育：{edu}", db, 4096, user_id=user_id)
