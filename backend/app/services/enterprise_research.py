"""企业调研引擎 — SearXNG 搜索 + AI 结构化提取"""
import json, re, httpx
from openai import AsyncOpenAI
from app.config import get_settings
from app import model_config as _mc

SEARXNG_URL = "http://192.168.120.16:8888/search"


class EnterpriseResearchEngine:
    def __init__(self):
        s = get_settings()
        self.client = AsyncOpenAI(api_key=s.DEEPSEEK_API_KEY, base_url=s.DEEPSEEK_BASE_URL)
        self.model = _mc.get_active_model_sync("generate")

    async def research(self, company_name: str, job_title: str = "") -> dict:
        """搜索企业信息并返回结构化数据。返回 {enterprise_info, recommendation}"""
        if not company_name:
            return {"enterprise_info": None, "recommendation": "unknown"}

        # 1. 搜索企业工商信息
        raw_data = await self._search_company(company_name)

        # 2. AI 解析
        enterprise_info = await self._parse_enterprise(raw_data, company_name)

        # 3. 生成投递建议等级
        recommendation = self._classify_recommendation(enterprise_info)

        return {"enterprise_info": enterprise_info, "recommendation": recommendation}

    async def _search_company(self, company_name: str) -> str:
        """通过 SearXNG 搜索企业信息"""
        queries = [
            f"{company_name} 工商信息 注册资本 成立时间",
            f"{company_name} 招聘 规模 参保人数",
        ]
        all_results = []
        async with httpx.AsyncClient(timeout=60) as client:
            for q in queries:
                try:
                    resp = await client.get(SEARXNG_URL, params={
                        "q": q, "format": "json", "language": "zh-CN"
                    })
                    data = resp.json()
                    for r in data.get("results", [])[:8]:
                        all_results.append(f"[{r.get('engine','')}] {r.get('title','')}\n{r.get('content','')}")
                except Exception:
                    continue
        return "\n\n---\n".join(all_results[:20])

    async def _parse_enterprise(self, raw_data: str, company_name: str) -> dict:
        """AI 解析搜索结果为结构化企业信息"""
        if not raw_data.strip():
            return {"company": company_name, "status": "no_data", "warning": "未找到公开信息"}

        prompt = f"""从以下搜索结果中提取「{company_name}」的企业信息，返回纯JSON。

{{
  "company": "公司全名",
  "established": "成立时间（如 2015年3月）",
  "registered_capital": "注册资本（万元，纯数字）",
  "address": "注册地址",
  "business_scope": "主营业务（一句话概括）",
  "qualifications": ["资质标签（高新技术企业/专精特新/科技型中小企业等）"],
  "employee_count": "参保人数或规模描述（如 50-100人）",
  "risk_signals": ["风险信号（经营异常/失信/大量诉讼等，无则为空数组）"],
  "salary_range": "该岗位或公司薪资区间（如有）",
  "data_quality": "数据完整度（full/partial/scarce）"
}}

搜索结果：
{raw_data[:4000]}"""

        resp = await self.client.chat.completions.create(
            model=self.model, max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_json(resp.choices[0].message.content)

    def _classify_recommendation(self, info: dict) -> str:
        """根据企业信息给出投递建议等级"""
        if not info or info.get("status") == "no_data":
            return "unknown"

        risk = info.get("risk_signals", [])
        capital = info.get("registered_capital", 0)
        data_quality = info.get("data_quality", "scarce")

        # 🔴 硬性否决
        hard_risks = ["失信", "被执行人", "经营异常", "吊销", "注销"]
        if any(any(kw in str(r) for kw in hard_risks) for r in risk):
            return "avoid"

        # 注册资本过低
        if isinstance(capital, (int, float)) and capital < 100:
            return "avoid"

        # 🟡 谨慎信号
        caution_signals = ["参保人数为0", "0人", "无参保", "小微企业", "成立不足1年"]
        if any(any(kw in str(r) for kw in caution_signals) for r in risk):
            return "cautious"

        if data_quality == "scarce":
            return "cautious"

        # 成立时间短
        est = info.get("established", "")
        if "2025" in str(est) or "2026" in str(est):
            return "cautious"

        # 规模太小
        emp = info.get("employee_count", "")
        if emp and any(x in str(emp) for x in ["0-", "1-", "少于10", "10人以下"]):
            return "cautious"

        # 🟢 正常
        return "recommend"

    def _parse_json(self, raw: str) -> dict:
        if not raw: return {}
        raw = re.sub(r'```\w*\n?', '', raw).replace('```', '').strip()
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            try: return json.loads(m.group())
            except: pass
        try: return json.loads(raw)
        except: return {}