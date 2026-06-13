"""岗位分析引擎 — 岗位解析 + 简历匹配 + 企业调研 + 投递建议"""
import json, re
from sqlalchemy import select
from openai import AsyncOpenAI
from app.config import get_settings
from app import model_config as _mc
from app.models.api_key import ApiKey
from app.routers.config import PROVIDERS, _decrypt
from app.services.enterprise_research import EnterpriseResearchEngine


class AnalysisEngine:
    def __init__(self):
        self.enterprise = EnterpriseResearchEngine()

    async def _get_client(self, db, user_id: str = None) -> AsyncOpenAI:
        """Build an AsyncOpenAI client from the user's active API key in the database."""
        # 1. Get active model name (with user_id)
        model = await _mc.get_active_model("generate", db, user_id)
        
        # 如果用户没有配置 API Key，抛出异常
        if model is None:
            raise ValueError("未配置模型，请先在设置中添加 API Key")
        
        # 2. Find matching active API key (优先用户自己的，然后全局)
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
            from app.config import get_settings
            s = get_settings()
            return AsyncOpenAI(api_key=s.DEEPSEEK_API_KEY, base_url=s.DEEPSEEK_BASE_URL)
        
        api_key = _decrypt(key_row.encrypted_key)
        provider_info = PROVIDERS.get(key_row.provider, {})
        base_url = provider_info.get("base_url", "https://api.deepseek.com")
        return AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def extract_requirement(self, text: str, db=None, user_id: str = None) -> dict:
        client = await self._get_client(db, user_id) if db else self.client
        model = await _mc.get_active_model("generate", db, user_id) if db else _mc.get_active_model_sync("generate")
        resp = await client.chat.completions.create(
            model=model, max_tokens=2048,
            messages=[{"role": "system", "content": "从JD提取结构化信息，返回纯JSON：{\"title\":\"\",\"company\":\"\",\"hard_skills\":[],\"soft_skills\":[],\"experience_years\":null,\"education\":\"\",\"responsibilities\":[],\"hidden_requirements\":[]}"},
                      {"role": "user", "content": text}],
        )
        return self._parse_json(resp.choices[0].message.content)

    async def match_analysis(self, req: dict, info: str, db=None, user_id: str = None) -> dict:
        client = await self._get_client(db, user_id) if db else self.client
        model = await _mc.get_active_model("generate", db, user_id) if db else _mc.get_active_model_sync("generate")
        system_prompt = """你是简历匹配度分析专家。分析岗位要求和候选人信息，给出匹配度评分和详细分析。

评分规则（必须严格遵守）：
- overall_match 为 0-100 的整数
- 即使匹配度不高，只要有相关经验，最低不低于 20
- 完全不匹配给 10-20，部分匹配给 40-70，高度匹配给 80-100
- 不要用 0 分，除非候选人信息完全为空

返回纯JSON：{"overall_match":85,"strength_points":["优势1","优势2"],"gap_points":["差距1","差距2"],"resume_focus":["重点1","重点2"],"resume_strategy":"简历优化策略"}"""
        resp = await client.chat.completions.create(
            model=model, max_tokens=2048,
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": f"岗位要求：{json.dumps(req,ensure_ascii=False)}\n\n候选人信息：{info}"}],
        )
        return self._parse_json(resp.choices[0].message.content)

    async def research_enterprise(self, company: str, job_title: str = "", user_id: str = None) -> tuple[dict | None, str]:
        """企业调研：返回 (enterprise_info, recommendation)"""
        if not company:
            return None, "unknown"
        result = await self.enterprise.research(company, job_title)
        return result.get("enterprise_info"), result.get("recommendation", "unknown")

    async def generate_advice(self, match: dict, enterprise_info: dict | None, recommendation: str, db=None, user_id: str = None) -> str:
        """综合匹配度 + 企业情况生成投递建议"""
        match_score = match.get("overall_match", 0)
        gaps = match.get("gap_points", [])
        strengths = match.get("strength_points", [])

        context = f"匹配度：{match_score}%\n"
        if strengths:
            context += f"优势：{'; '.join(strengths[:5])}\n"
        if gaps:
            context += f"差距：{'; '.join(gaps[:5])}\n"
        if enterprise_info:
            context += f"企业：注册资本{enterprise_info.get('registered_capital','?')}万，规模{enterprise_info.get('employee_count','?')}，风险{enterprise_info.get('risk_signals',[]) or '无'}\n"

        client = await self._get_client(db, user_id) if db else self.client
        model = await _mc.get_active_model("generate", db, user_id) if db else _mc.get_active_model_sync("generate")
        resp = await client.chat.completions.create(
            model=model, max_tokens=512,
            messages=[{"role": "system", "content": "你是求职顾问。根据匹配度和企业情况，给出100字以内的投递建议（是否值得投、重点准备什么、薪资预期）。简洁直接。"},
                      {"role": "user", "content": context}],
        )
        return resp.choices[0].message.content.strip()

    def _parse_json(self, raw):
        if not raw: return {}
        raw = re.sub(r'```\w*\n?', '', raw).replace('```', '').strip()
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            try: return json.loads(m.group())
            except: pass
        try: return json.loads(raw)
        except: return {}
