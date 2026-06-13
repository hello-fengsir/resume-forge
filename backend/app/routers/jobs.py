"""岗位分析路由 — 含企业调研"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import json
from app.database import get_db, async_session
from app.data_store import save as ds_save, load as ds_load, delete as ds_delete
from app.models.job_analysis import JobAnalysis
from app.models.info_entry import InfoEntry
from app.auth.auth_utils import get_current_user
from app.models.user import User
from openai import AsyncOpenAI
from app.services.analysis_engine import AnalysisEngine
from app.config import get_settings

router = APIRouter()
engine = AnalysisEngine()
ENTITY = "jobs"


def _combined_recommendation(company_rec: str, match_score) -> str:
    """综合公司质量和匹配度给出投递建议"""
    score = float(match_score or 0)
    if score <= 1:
        score = score * 100

    if company_rec == "avoid":
        return "avoid"
    if score < 30:
        return "avoid"
    if company_rec == "cautious" or score < 50:
        return "cautious"
    return "recommend"


@router.post("/analyze-screenshot")
async def analyze_screenshot(data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """上传截图 → AI 提取文字 → 分析岗位"""
    import base64 as b64
    image_b64 = data.get("image", "")
    if not image_b64:
        raise HTTPException(400, "请提供图片 base64 数据")

    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]

    import io, pytesseract
    from PIL import Image
    img_bytes = b64.b64decode(image_b64)
    img = Image.open(io.BytesIO(img_bytes))
    ocr_text = pytesseract.image_to_string(img, lang='chi_sim+eng')

    if not ocr_text.strip():
        raise HTTPException(400, "未能从截图中提取到文字")

    user_id = current_user.id
    try:
        structured = await engine.extract_requirement(ocr_text, db, user_id)
        result = await db.execute(select(InfoEntry).where(InfoEntry.user_id == current_user.id).order_by(InfoEntry.created_at.desc()))
        entries = result.scalars().all()
        info = "\n\n".join(f"[{e.category.value}] {e.title}\n{e.content or ''}" for e in entries)
        match = await engine.match_analysis(structured, info, db, user_id)

        company = structured.get("company") or "未知公司"
        job_title = structured.get("title") or "未识别岗位"
        enterprise_info, company_rec = await engine.research_enterprise(company, job_title, user_id)
        match_score = match.get("overall_match", 0)
        recommendation = _combined_recommendation(company_rec, match_score)
        advice = await engine.generate_advice(match, enterprise_info, recommendation, db, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))

    job = JobAnalysis(
        user_id=current_user.id,
        title=job_title, company=company,
        raw_requirement=ocr_text,
        structured_req=structured, match_result=match,
        resume_focus={"focus": match.get("resume_focus", []), "strategy": match.get("resume_strategy", "")},
        enterprise_info=enterprise_info, recommendation=recommendation,
    )
    db.add(job); await db.commit(); await db.refresh(job)

    result_dict = _fmt(job)
    result_dict["advice"] = advice
    result_dict["ocr_text"] = ocr_text
    return result_dict


@router.post("/analyze")
async def analyze_job(data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    req_text = data.get("requirement", "")
    if not req_text:
        raise HTTPException(400, "请提供岗位要求")

    user_id = current_user.id
    try:
        structured = await engine.extract_requirement(req_text, db, user_id)

        result = await db.execute(select(InfoEntry).where(InfoEntry.user_id == current_user.id).order_by(InfoEntry.created_at.desc()))
        entries = result.scalars().all()
        info = "\n\n".join(f"[{e.category.value}] {e.title}\n{e.content or ''}" for e in entries)
        match = await engine.match_analysis(structured, info, db, user_id)

        company = structured.get("company", "")
        job_title = structured.get("title", "")
        enterprise_info, company_rec = await engine.research_enterprise(company, job_title, user_id)

        match_score = match.get("overall_match", 0)
        recommendation = _combined_recommendation(company_rec, match_score)
        advice = await engine.generate_advice(match, enterprise_info, recommendation, db, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))

    job = JobAnalysis(
        user_id=current_user.id,
        title=job_title,
        company=company,
        raw_requirement=req_text,
        source_url=data.get("source_url"),
        structured_req=structured,
        match_result=match,
        resume_focus={"focus": match.get("resume_focus", []), "strategy": match.get("resume_strategy", "")},
        enterprise_info=enterprise_info,
        recommendation=recommendation,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    result_dict = _fmt(job)
    result_dict["advice"] = advice
    return result_dict


@router.post("/{job_id}/research")
async def research_enterprise(job_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """单独触发企业调研（用于已有分析记录）"""
    r = await db.execute(select(JobAnalysis).where(JobAnalysis.id == UUID(job_id), JobAnalysis.user_id == current_user.id))
    job = r.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "不存在")

    company = job.company or ""
    if not company:
        raise HTTPException(400, "该分析未识别到公司名")

    user_id = current_user.id
    try:
        enterprise_info, company_rec = await engine.research_enterprise(company, job.title or "", user_id)
        match = job.match_result or {}
        match_score = match.get("overall_match", 0)
        recommendation = _combined_recommendation(company_rec, match_score)
        advice = await engine.generate_advice(match, enterprise_info, recommendation, db, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))

    job.enterprise_info = enterprise_info
    job.recommendation = recommendation
    await db.commit()
    await db.refresh(job)

    result = _fmt(job)
    result["advice"] = advice
    return result


@router.get("/")
async def list_jobs(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    r = await db.execute(select(JobAnalysis).where(JobAnalysis.user_id == current_user.id).order_by(JobAnalysis.created_at.desc()))
    return [_fmt(j) for j in r.scalars().all()]


@router.get("/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    r = await db.execute(select(JobAnalysis).where(JobAnalysis.id == UUID(job_id), JobAnalysis.user_id == current_user.id))
    j = r.scalar_one_or_none()
    if not j:
        raise HTTPException(404, "不存在")
    return _fmt(j)


@router.put("/{job_id}")
async def update_job(job_id: str, data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    r = await db.execute(select(JobAnalysis).where(JobAnalysis.id == UUID(job_id), JobAnalysis.user_id == current_user.id))
    job = r.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "不存在")

    editable = ["title", "company", "raw_requirement", "source_url"]
    for field in editable:
        if field in data:
            setattr(job, field, data[field])

    await db.commit()
    await db.refresh(job)
    d = _fmt(job)
    ds_save(ENTITY, job_id, d)
    return d

@router.delete("/{job_id}")
async def delete_job(job_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    r = await db.execute(select(JobAnalysis).where(JobAnalysis.id == UUID(job_id), JobAnalysis.user_id == current_user.id))
    j = r.scalar_one_or_none()
    if not j:
        raise HTTPException(404, "不存在")
    await db.delete(j)
    await db.commit()
    return {"deleted": True}


def _fmt(j):
    return {
        "id": str(j.id),
        "title": j.title,
        "company": j.company,
        "raw_requirement": j.raw_requirement,
        "source_url": j.source_url,
        "structured_req": j.structured_req,
        "match_result": j.match_result,
        "resume_focus": j.resume_focus,
        "enterprise_info": j.enterprise_info,
        "recommendation": j.recommendation,
        "created_at": j.created_at.isoformat(),
    }
