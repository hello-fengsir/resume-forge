"""信息提取引擎 - 加固版"""
import json, re, logging
from sqlalchemy import select
from openai import AsyncOpenAI
from app.config import get_settings
from app import model_config as _mc
from app.models.api_key import ApiKey
from app.routers.config import PROVIDERS, _decrypt

logger = logging.getLogger(__name__)

class ExtractEngine:
    PROMPT = """从以下文本中提取简历相关信息。返回纯JSON数组，不要markdown代码块。

每个元素格式：
{"category":"work_experience|project|education|skill|certification","title":"职位/项目名","company":"公司名","start_date":"YYYY-MM","end_date":"YYYY-MM","content":"描述"}

规则：
- 只提取真实存在的信息，不要编造
- 日期尽量保留原始格式
- 如果内容很长，提取核心要点
- 返回纯JSON数组，一行一个元素也可以"""

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

    async def extract(self, text: str, db=None, user_id: str = None) -> list[dict]:
        # 限制输入长度（避免超 token）
        max_input = 12000
        if len(text) > max_input:
            text = text[:max_input]
            logger.info(f"Text truncated from {len(text)} to {max_input} chars")
        
        raw = await self._call_ai(text, db, user_id)
        return self._parse_json(raw)

    async def _call_ai(self, text: str, db=None, user_id: str = None) -> str:
        try:
            client = await self._get_client(db, user_id) if db else None
            model = await _mc.get_active_model("generate", db, user_id) if db else _mc.get_active_model_sync("generate")
            
            if client is None:
                from app.config import get_settings
                s = get_settings()
                client = AsyncOpenAI(api_key=s.DEEPSEEK_API_KEY, base_url=s.DEEPSEEK_BASE_URL)
            
            resp = await client.chat.completions.create(
                model=model,
                max_tokens=8192,
                messages=[
                    {"role": "system", "content": self.PROMPT},
                    {"role": "user", "content": text},
                ],
            )
            raw = resp.choices[0].message.content or ""
            logger.info(f"AI response: {len(raw)} chars, starts with: {raw[:100]}")
            return raw
        except Exception as e:
            logger.error(f"AI call failed: {e}")
            raise

    def _parse_json(self, raw: str) -> list[dict]:
        # Strip markdown code blocks
        raw = re.sub(r"```\w*\n?", "", raw).replace("```", "").strip()

        # Try direct JSON parse
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                for v in data.values():
                    if isinstance(v, list):
                        return v
                return [data]
        except json.JSONDecodeError as e:
            logger.warning(f"Direct JSON parse failed: {e}")

        # Try extracting JSON array with regex
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass

        # Try to fix truncated JSON: find last complete object
        fixed = self._fix_truncated_array(raw)
        if fixed:
            return fixed

        # Last resort: line-by-line parsing
        items = []
        for line in raw.split("\n"):
            line = line.strip().strip(",")
            if line.startswith("{") and line.endswith("}"):
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

        if items:
            return items

        logger.error(f"All JSON parsing failed. Raw: {raw[:500]}")
        return []

    def _fix_truncated_array(self, raw: str) -> list[dict] | None:
        """尝试修复被截断的JSON数组"""
        # Find last complete object before truncation
        # Look for pattern: },{ or }] and try parsing up to that point
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if not m:
            return None

        arr_str = m.group()
        # Try progressively shorter substrings
        for i in range(len(arr_str), 0, -1):
            if arr_str[i - 1] in ("}", "]"):
                candidate = arr_str[:i]
                if candidate.endswith("}"):
                    # Try closing the array
                    candidate += "]"
                try:
                    result = json.loads(candidate)
                    if isinstance(result, list) and len(result) > 0:
                        logger.info(f"Fixed truncated JSON: got {len(result)} items from {len(raw)} chars")
                        return result
                except json.JSONDecodeError:
                    continue

        return None
