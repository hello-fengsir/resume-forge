"""内容优化引擎 — AI 一键调优"""
import json, re, logging
from openai import AsyncOpenAI
from app.config import get_settings
from app import model_config as _mc

logger = logging.getLogger(__name__)

OPTIMIZE_PROMPT = """你是一位资深简历优化顾问。请优化以下信息条目，使其更专业、更有说服力。

规则：
1. 保留所有事实信息，不编造任何不存在的数据或经历
2. 使用动作动词开头（主导、设计、实现、交付、优化、推动）
3. 量化成果优先（已有数字保留，不要编造数字）
4. 行业术语准确（如：超融合、虚拟化、等保2.0、信创）
5. 简洁有力，删除"负责"等模糊表述
6. 如果原标题/内容已经很好，微调即可，不要大幅改写

返回纯JSON，格式：
{"title":"优化后的标题","content":"优化后的详细内容","improvements":["具体改进点1","具体改进点2"]}

只输出JSON，不要任何markdown标记或解释文字。"""


class OptimizeEngine:
    def __init__(self):
        s = get_settings()
        self.client = AsyncOpenAI(api_key=s.DEEPSEEK_API_KEY, base_url=s.DEEPSEEK_BASE_URL)
        self.model = _mc.get_active_model_sync("generate")

    async def optimize(self, title: str, content: str, category: str) -> dict:
        """优化单条信息条目"""
        text = f"分类：{category}\n原标题：{title}\n原内容：{content or '(空)'}"
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": OPTIMIZE_PROMPT},
                    {"role": "user", "content": text},
                ],
            )
            raw = resp.choices[0].message.content or ""
            logger.info(f"Optimize response: {len(raw)} chars")
        except Exception as e:
            logger.error(f"AI optimize call failed: {e}")
            raise

        # Parse JSON
        raw = re.sub(r"```\w*\n?", "", raw).replace("```", "").strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group())
                except json.JSONDecodeError:
                    pass
        # Fallback: return original
        return {
            "title": title,
            "content": content,
            "improvements": ["（AI 返回格式异常，已保留原文）"]
        }
