"""文本快速识别引擎 — 粘贴一段文本，AI 识别分类/标题/公司/内容"""
import os
from app import model_config as _mc
from app.models.api_key import ApiKey
from app.routers.config import PROVIDERS, _decrypt
import json
import httpx
from sqlalchemy import select


class InfoExtractor:
    """使用 DeepSeek API 分析自由文本，提取结构化信息条目"""

    def __init__(self):
        pass  # No hardcoded client — get it dynamically per request

    async def _get_api_key_and_model(self, db=None, user_id: str = None) -> tuple[str, str, str]:
        """获取用户的 API Key、模型和 Base URL"""
        model = await _mc.get_active_model("generate", db, user_id) if db else _mc.get_active_model_sync("generate")
        
        # 如果用户没有配置 API Key，返回 None
        if model is None:
            return None, None, None
        
        # 优先使用用户的 API Key
        if user_id and db:
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
                return api_key, model, base_url

        # Fallback: 任意活跃的 key
        if db:
            result2 = await db.execute(
                select(ApiKey).where(ApiKey.is_active == True).order_by(ApiKey.created_at.desc())
            )
            key_row = result2.scalars().first()
            if key_row:
                api_key = _decrypt(key_row.encrypted_key)
                provider_info = PROVIDERS.get(key_row.provider, {})
                base_url = provider_info.get("base_url", "https://api.deepseek.com")
                return api_key, model, base_url

        # 最后 fallback: 环境变量
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        return api_key, model, base_url

    async def extract(self, text: str, db=None, user_id: str = None) -> dict:
        """分析文本，返回 {category, title, company, content}"""
        api_key, model, base_url = await self._get_api_key_and_model(db, user_id)
        
        if not api_key or not model:
            return self._fallback(text)

        prompt = f"""你是一个简历信息提取助手。请分析以下文本，将其结构化为一个信息条目。

文本内容：
{text[:2000]}

请返回 JSON 格式（只返回 JSON，不要其他内容）：
{{
    "category": "分类，从以下选一个：project(项目经验) / work_experience(工作经历) / skill(技能) / certification(证书) / education(教育) / self_learning(学习能力)",
    "title": "条目标题，简洁概括（15字以内）",
    "company": "关联的公司或机构名称，没有填空字符串",
    "content": "整理后的内容描述，保持原文中关键的量化数据和细节"
}}

注意：
- category 必须严格从给定选项中选择
- title 要简洁有力
- content 保留原文的量化数据（金额、数量、百分比等）
- 如果文本是自学经历，选择 self_learning
"""

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 500,
                        "response_format": {"type": "json_object"},
                    },
                )
                data = resp.json()
                content_text = data["choices"][0]["message"]["content"]
                result = json.loads(content_text)
                return {
                    "category": result.get("category", "project"),
                    "title": result.get("title", "未命名"),
                    "company": result.get("company", ""),
                    "content": result.get("content", text),
                }
        except Exception:
            return self._fallback(text)

    def _fallback(self, text: str) -> dict:
        """无 AI 时的简单回退"""
        # 截取前50字作为标题
        title = text[:50].replace("\n", " ").strip()
        if len(title) > 20:
            title = title[:20] + "…"
        return {
            "category": "project",
            "title": title or "未命名",
            "company": "",
            "content": text,
        }
