"""质量评估引擎"""
import json, re
from sqlalchemy import select
from openai import AsyncOpenAI
from app.config import get_settings
from app import model_config as _mc
from app.models.api_key import ApiKey
from app.routers.config import PROVIDERS, _decrypt

class ReviewEngine:
    def __init__(self):
        pass  # No hardcoded client — get it dynamically per request

    async def _get_client(self, db, user_id: str = None) -> AsyncOpenAI:
        """Build an AsyncOpenAI client from the user's active API key in the database."""
        model = await _mc.get_active_model("review", db, user_id)
        
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

    async def _call(self, system: str, user: str, db=None, max_tokens=3072, user_id: str = None) -> str:
        client = await self._get_client(db, user_id)
        model = await _mc.get_active_model("review", db, user_id)
        resp = await client.chat.completions.create(
            model=model, max_tokens=max_tokens,
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
        )
        return resp.choices[0].message.content or ""

    async def assess(self, resume: str, job: str = "", db=None, user_id: str = None) -> dict:
        jc = f"\n岗位要求：{job}" if job else ""
        prompt = f"""严格评审，返回纯JSON：
{{"overall_score":0,"dimension_scores":{{}},"issues":[{{"severity":"critical|major|minor","dimension":"...","description":"...","suggestion":"..."}}],"strengths":[],"summary":""}}
至少5个issues含1个critical。{jc}\n简历：{resume}"""
        raw = await self._call("你是顶级HR，铁面无私评审。", prompt, db, user_id=user_id)
        return self._parse(raw)

    async def improve(self, resume: str, issues: list, info: str = "", db=None, user_id: str = None) -> str:
        its = "\n".join(f"- [{i.get('severity','')}] {i.get('description','')}" for i in (issues or []))
        return await self._call("基于评审优化简历。修复所有问题，强化量化。", f"问题：{its}\n信息：{info}\n原简历：{resume}\n输出优化后的完整简历。", db, 4096, user_id=user_id)

    def _parse(self, raw):
        if not raw: return {}
        raw = re.sub(r'```\w*\n?','',raw).replace('```','').strip()
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m: return json.loads(m.group())
        return json.loads(raw)
