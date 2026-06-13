"""质量评估路由 — 本地 JSON 镜像存储"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import json
from app.database import get_db
from app.models.resume_version import ResumeVersion
from app.models.quality_review import QualityReview
from app.models.job_analysis import JobAnalysis
from app.models.info_entry import InfoEntry
from app.auth.auth_utils import get_current_user
from app.models.user import User
from app.services.review_engine import ReviewEngine
from app.data_store import save as ds_save, load as ds_load, delete as ds_delete

router = APIRouter()
engine = ReviewEngine()
ENTITY = "reviews"


@router.post("/assess")
async def assess_resume(data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    rid = data.get("resume_id")
    if not rid: raise HTTPException(400, "请提供resume_id")
    r = await db.execute(select(ResumeVersion).where(ResumeVersion.id == UUID(rid), ResumeVersion.user_id == current_user.id))
    resume = r.scalar_one_or_none()
    if not resume or not resume.full_resume: raise HTTPException(404, "简历不存在")
    job_req = ""
    if resume.job_analysis_id:
        jr = await db.execute(select(JobAnalysis).where(JobAnalysis.id == resume.job_analysis_id))
        job = jr.scalar_one_or_none()
        if job: job_req = json.dumps(job.structured_req or {}, ensure_ascii=False)
    
    user_id = current_user.id
    try:
        report = await engine.assess(resume.full_resume, job_req, db, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    review = QualityReview(user_id=current_user.id, resume_id=UUID(rid), scores={"overall_score": report.get("overall_score", 0), **report.get("dimension_scores", {})}, issues=report.get("issues",[]), suggestions=[{"issue":i.get("description",""),"suggestion":i.get("suggestion","")} for i in report.get("issues",[])])
    db.add(review); await db.commit(); await db.refresh(review)
    d = _fmt(review)
    ds_save(ENTITY, str(review.id), d)
    return d


@router.get("/{review_id}")
async def get_review(review_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    local = ds_load(ENTITY, review_id)
    if local:
        return local
    r = await db.execute(select(QualityReview).where(QualityReview.id == UUID(review_id), QualityReview.user_id == current_user.id))
    x = r.scalar_one_or_none()
    if not x: raise HTTPException(404, "不存在")
    d = _fmt(x)
    ds_save(ENTITY, review_id, d)
    return d


@router.post("/{review_id}/improve")
async def improve_resume(review_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    r = await db.execute(select(QualityReview).where(QualityReview.id == UUID(review_id), QualityReview.user_id == current_user.id))
    review = r.scalar_one_or_none()
    if not review: raise HTTPException(404, "不存在")
    rr = await db.execute(select(ResumeVersion).where(ResumeVersion.id == review.resume_id, ResumeVersion.user_id == current_user.id))
    resume = rr.scalar_one_or_none()
    if not resume: raise HTTPException(404, "简历不存在")
    ir = await db.execute(select(InfoEntry).where(InfoEntry.user_id == current_user.id).order_by(InfoEntry.created_at.desc()))
    entries = ir.scalars().all()
    info = "\n\n".join(f"[{e.category.value}] {e.title}\n{e.content or ''}" for e in entries)
    
    user_id = current_user.id
    try:
        improved = await engine.improve(resume.full_resume or "", review.issues or [], info, db, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    cr = await db.execute(select(ResumeVersion).where(ResumeVersion.job_analysis_id == resume.job_analysis_id, ResumeVersion.user_id == current_user.id))
    v = len(cr.scalars().all()) + 1
    new_r = ResumeVersion(user_id=current_user.id, job_analysis_id=resume.job_analysis_id, version=v, full_resume=improved, status="reviewed")
    db.add(new_r); await db.commit(); await db.refresh(new_r)
    # 新简历也存本地
    from app.routers.resumes import _fmt as res_fmt
    ds_save("resumes", str(new_r.id), res_fmt(new_r))
    return {"improved": True, "id": str(new_r.id), "version": new_r.version}


def _fmt(r): return {"id":str(r.id),"resume_id":str(r.resume_id),"scores":r.scores,"issues":r.issues,"suggestions":r.suggestions,"improved_resume":r.improved_resume,"created_at":r.created_at.isoformat()}
