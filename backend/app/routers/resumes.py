"""简历生成路由 — 含进度追踪"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID, uuid4
import json, io, asyncio, time
from app.database import get_db
from app.models.resume_version import ResumeVersion
from app.models.job_analysis import JobAnalysis
from app.models.info_entry import InfoEntry
from app.auth.auth_utils import get_current_user
from app.models.user import User
from app.services.generate_engine import GenerateEngine
from app.data_store import save as ds_save, load as ds_load, delete as ds_delete

router = APIRouter()
engine = GenerateEngine()
ENTITY = "resumes"

# ====== 进度追踪（内存） ======
_gen_progress: dict[str, dict] = {}

STEPS = [
    {"stage": "preparing",     "label": "准备数据",       "pct": 5},
    {"stage": "core",          "label": "提炼核心优势",   "pct": 20},
    {"stage": "work",          "label": "匹配岗位梳理工作经历", "pct": 45},
    {"stage": "projects",      "label": "整理项目经验",   "pct": 70},
    {"stage": "education",     "label": "提取教育经历",   "pct": 80},
    {"stage": "merge",         "label": "整合生成完整简历", "pct": 95},
    {"stage": "done",          "label": "制作完成",       "pct": 100},
]


def _set_progress(gen_id: str, stage: str, pct: int, message: str = "", resume_id: str = None, error: str = None):
    _gen_progress[gen_id] = {
        "stage": stage,
        "pct": pct,
        "message": message,
        "resume_id": resume_id,
        "error": error,
        "updated_at": time.time(),
    }


async def _enrich(d: dict, db: AsyncSession) -> dict:
    """补充 job_title 和 company 字段"""
    if d.get("job_title") and d.get("company"):
        return d
    jid = d.get("job_analysis_id")
    if jid:
        try:
            jr = await db.execute(select(JobAnalysis).where(JobAnalysis.id == UUID(jid)))
            j = jr.scalar_one_or_none()
            if j:
                d["job_title"] = j.title
                d["company"] = j.company or ""
        except Exception:
            pass
    return d


# ====== 新接口：启动生成（异步） ======
@router.post("/generate-async")
async def generate_resume_async(data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """启动简历生成，返回 gen_id 用于轮询进度"""
    job_id = data.get("job_analysis_id")
    if not job_id:
        raise HTTPException(400, "请提供job_analysis_id")

    r = await db.execute(select(JobAnalysis).where(JobAnalysis.id == UUID(job_id), JobAnalysis.user_id == current_user.id))
    job = r.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "岗位不存在")

    gen_id = str(uuid4())
    _set_progress(gen_id, "preparing", 5, "正在准备数据...")

    # 后台异步执行生成
    asyncio.create_task(_run_generate(gen_id, job_id, current_user.id))

    return {"gen_id": gen_id, "status": "started"}


@router.get("/generate-status/{gen_id}")
async def get_generate_status(gen_id: str):
    """查询简历生成进度"""
    prog = _gen_progress.get(gen_id)
    if not prog:
        raise HTTPException(404, "生成任务不存在")
    return prog


async def _run_generate(gen_id: str, job_id: str, user_id):
    """后台执行简历生成的完整流程"""
    from app.database import async_session
    async with async_session() as db:
        try:
            r = await db.execute(select(JobAnalysis).where(JobAnalysis.id == UUID(job_id), JobAnalysis.user_id == user_id))
            job = r.scalar_one_or_none()
            if not job:
                _set_progress(gen_id, "error", 0, error="岗位不存在")
                return

            _set_progress(gen_id, "preparing", 8, "正在读取个人信息库...")
            ir = await db.execute(select(InfoEntry).where(InfoEntry.user_id == user_id).order_by(InfoEntry.created_at.desc()))
            entries = ir.scalars().all()
            info_parts = [f"[{e.category.value}] {e.title}\n{e.content or ''}" for e in entries]
            info = "\n\n".join(info_parts)
            job_text = json.dumps(job.structured_req or {}, ensure_ascii=False)
            focus = (job.resume_focus or {}).get("focus", [])

            # Step 1: 核心优势
            _set_progress(gen_id, "core", 15, "正在提炼核心优势，匹配岗位亮点...")
            core = await engine.gen_core(info, job_text, focus, db, user_id)
            _set_progress(gen_id, "core", 25, "核心优势提炼完成 ✓")

            # Step 2: 工作经历
            _set_progress(gen_id, "work", 30, "正在匹配岗位内容，梳理工作经历...")
            work = await engine.gen_work(info, job_text, db, user_id)
            _set_progress(gen_id, "work", 50, "工作经历梳理完成 ✓")

            # Step 3: 项目经验
            _set_progress(gen_id, "projects", 55, "正在整理项目经验，突出技术匹配...")
            projects = await engine.gen_projects(info, job_text, db, user_id)
            _set_progress(gen_id, "projects", 75, "项目经验整理完成 ✓")

            # Step 4: 教育经历
            _set_progress(gen_id, "education", 80, "正在提取教育经历...")
            education = await engine.gen_education(info, db, user_id)
            _set_progress(gen_id, "education", 85, "教育经历提取完成 ✓")

            # Step 5: 合并
            _set_progress(gen_id, "merge", 90, "正在整合生成完整简历，规范排版...")
            full = await engine.merge(core, work, projects, education, job_text, db, user_id)

            # 保存
            _set_progress(gen_id, "merge", 95, "正在保存...")
            r2 = await db.execute(select(ResumeVersion).where(ResumeVersion.job_analysis_id == UUID(job_id), ResumeVersion.user_id == user_id))
            v = len(r2.scalars().all()) + 1
            resume = ResumeVersion(
                user_id=user_id,
                job_analysis_id=UUID(job_id), version=v,
                core_strengths=core, work_experience=work,
                project_exp=projects, education=education,
                full_resume=full, status="draft"
            )
            db.add(resume)
            await db.commit()
            await db.refresh(resume)

            d = _fmt(resume)
            d["job_title"] = job.title
            d["company"] = job.company or ""
            ds_save(ENTITY, str(resume.id), d)

            _set_progress(gen_id, "done", 100, "简历制作完成！", resume_id=str(resume.id))

        except ValueError as e:
            _set_progress(gen_id, "error", 0, error=str(e))
        except Exception as e:
            _set_progress(gen_id, "error", 0, error=f"生成失败: {str(e)}")

        # 清理：10分钟后删除进度记录
        await asyncio.sleep(600)
        _gen_progress.pop(gen_id, None)


# ====== 旧接口保留兼容 ======
@router.post("/generate")
async def generate_resume(data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    job_id = data.get("job_analysis_id")
    if not job_id: raise HTTPException(400, "请提供job_analysis_id")
    r = await db.execute(select(JobAnalysis).where(JobAnalysis.id == UUID(job_id), JobAnalysis.user_id == current_user.id))
    job = r.scalar_one_or_none()
    if not job: raise HTTPException(404, "岗位不存在")
    r = await db.execute(select(InfoEntry).where(InfoEntry.user_id == current_user.id).order_by(InfoEntry.created_at.desc()))
    entries = r.scalars().all()
    info_parts = []
    for e in entries:
        info_parts.append(f"[{e.category.value}] {e.title}\n{e.content or ''}")
    info = "\n\n".join(info_parts)
    job_text = json.dumps(job.structured_req or {}, ensure_ascii=False)
    focus = (job.resume_focus or {}).get("focus", [])

    user_id = current_user.id
    try:
        core = await engine.gen_core(info, job_text, focus, db, user_id)
        work = await engine.gen_work(info, job_text, db, user_id)
        projects = await engine.gen_projects(info, job_text, db, user_id)
        education = await engine.gen_education(info, db, user_id)
        full = await engine.merge(core, work, projects, education, job_text, db, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))

    r = await db.execute(select(ResumeVersion).where(ResumeVersion.job_analysis_id == UUID(job_id), ResumeVersion.user_id == current_user.id))
    v = len(r.scalars().all()) + 1
    resume = ResumeVersion(user_id=current_user.id, job_analysis_id=UUID(job_id), version=v, core_strengths=core, work_experience=work, project_exp=projects, education=education, full_resume=full, status="draft")
    db.add(resume); await db.commit(); await db.refresh(resume)

    d = _fmt(resume)
    d["job_title"] = job.title
    d["company"] = job.company or ""
    ds_save(ENTITY, str(resume.id), d)
    return d


@router.get("/")
async def list_resumes(job_id: str = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(ResumeVersion).where(ResumeVersion.user_id == current_user.id).order_by(ResumeVersion.created_at.desc())
    if job_id:
        query = query.where(ResumeVersion.job_analysis_id == UUID(job_id))
    r = await db.execute(query)
    resumes = r.scalars().all()
    result = []
    for x in resumes:
        local = ds_load(ENTITY, str(x.id))
        if local:
            d = await _enrich(local, db)
            ds_save(ENTITY, str(x.id), d)
            result.append(d)
            continue
        d = _fmt(x)
        if x.job_analysis_id:
            jr = await db.execute(select(JobAnalysis).where(JobAnalysis.id == x.job_analysis_id))
            j = jr.scalar_one_or_none()
            if j:
                d["job_title"] = j.title
                d["company"] = j.company or ""
        ds_save(ENTITY, str(x.id), d)
        result.append(d)
    return result


@router.get("/{resume_id}")
async def get_resume(resume_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    local = ds_load(ENTITY, resume_id)
    if local:
        d = await _enrich(local, db)
        ds_save(ENTITY, resume_id, d)
        return d
    r = await db.execute(select(ResumeVersion).where(ResumeVersion.id == UUID(resume_id), ResumeVersion.user_id == current_user.id))
    x = r.scalar_one_or_none()
    if not x: raise HTTPException(404, "不存在")
    d = _fmt(x)
    if x.job_analysis_id:
        jr = await db.execute(select(JobAnalysis).where(JobAnalysis.id == x.job_analysis_id))
        j = jr.scalar_one_or_none()
        if j:
            d["job_title"] = j.title
            d["company"] = j.company or ""
    ds_save(ENTITY, resume_id, d)
    return d


@router.put("/{resume_id}")
async def update_resume(resume_id: str, data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    r = await db.execute(select(ResumeVersion).where(ResumeVersion.id == UUID(resume_id), ResumeVersion.user_id == current_user.id))
    x = r.scalar_one_or_none()
    if not x: raise HTTPException(404, "不存在")
    for f in ["core_strengths","work_experience","project_exp","education","full_resume","status"]:
        if f in data: setattr(x, f, data[f])
    await db.commit()
    await db.refresh(x)
    d = _fmt(x)
    ds_save(ENTITY, resume_id, d)
    return {"updated": True}


@router.delete("/{resume_id}")
async def delete_resume(resume_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    r = await db.execute(select(ResumeVersion).where(ResumeVersion.id == UUID(resume_id), ResumeVersion.user_id == current_user.id))
    x = r.scalar_one_or_none()
    if not x: raise HTTPException(404, "不存在")
    await db.delete(x)
    await db.commit()
    ds_delete(ENTITY, resume_id)
    return {"deleted": True}


@router.get("/{resume_id}/export")
async def export_resume(resume_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    local = ds_load(ENTITY, resume_id)
    content = ""
    ver = 1
    if local:
        content = local.get("full_resume", "")
        ver = local.get("version", 1)
    else:
        r = await db.execute(select(ResumeVersion).where(ResumeVersion.id == UUID(resume_id), ResumeVersion.user_id == current_user.id))
        x = r.scalar_one_or_none()
        if not x: raise HTTPException(404, "不存在")
        content = x.full_resume or ""
        ver = x.version
    return StreamingResponse(io.BytesIO(content.encode()), media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename=resume-v{ver}.md"})


def _fmt(r): return {"id":str(r.id),"job_analysis_id":str(r.job_analysis_id) if r.job_analysis_id else None,"version":r.version,"core_strengths":r.core_strengths,"work_experience":r.work_experience,"project_exp":r.project_exp,"education":r.education,"full_resume":r.full_resume,"status":r.status,"created_at":r.created_at.isoformat()}
