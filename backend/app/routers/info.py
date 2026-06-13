"""信息条目 CRUD 路由 — 仅 DB 存储（用户录入数据，不镜像本地）"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth.auth_utils import get_current_user
from app.models.user import User
from app.models.info_entry import InfoEntry, InfoCategory
from app.routers.upload import _parse_date
from app.engines.optimize_engine import OptimizeEngine
from app.services.dedup_engine import detect_duplicates
from app.engines.info_extractor import InfoExtractor
from sqlalchemy import select
from uuid import UUID

router = APIRouter()
optimize_engine = OptimizeEngine()


def _fmt(e): return {
    "id": str(e.id),
    "category": e.category.value if hasattr(e.category, 'value') else e.category,
    "title": e.title,
    "company": e.company,
    "start_date": e.start_date.isoformat() if e.start_date else None,
    "end_date": e.end_date.isoformat() if e.end_date else None,
    "content": e.content,
    "raw_input": e.raw_input,
    "source_file": e.source_file,
    "created_at": e.created_at.isoformat(),
    "updated_at": e.updated_at.isoformat(),
}


@router.get("/entries")
async def list_entries(
    current_user: User = Depends(get_current_user),
    category: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(InfoEntry).where(InfoEntry.user_id == current_user.id).order_by(InfoEntry.created_at.desc())
    if category:
        stmt = stmt.where(InfoEntry.category == category)
    result = await db.execute(stmt)
    entries = result.scalars().all()
    return [_fmt(e) for e in entries]


@router.get("/entries/{entry_id}")
async def get_entry(entry_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = select(InfoEntry).where(InfoEntry.user_id == current_user.id).where(InfoEntry.id == UUID(entry_id))
    result = await db.execute(stmt)
    e = result.scalar_one_or_none()
    if not e:
        raise HTTPException(404, "条目不存在")
    return _fmt(e)


@router.post("/entries", status_code=201)
async def create_entry(data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    entry = InfoEntry(user_id=current_user.id,
        category=data.get("category", "work_experience"),
        title=data.get("title", ""),
        company=data.get("company"),
        content=data.get("content"),
        raw_input=data.get("raw_input"),
        start_date=_parse_date(data.get("start_date")),
        end_date=_parse_date(data.get("end_date")),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return {"id": str(entry.id), "title": entry.title, "category": entry.category.value}


@router.put("/entries/{entry_id}")
async def update_entry(entry_id: str, data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = select(InfoEntry).where(InfoEntry.user_id == current_user.id).where(InfoEntry.id == UUID(entry_id))
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "条目不存在")

    for field in ["category", "title", "company", "content", "raw_input", "start_date", "end_date"]:
        if field in data:
            setattr(entry, field, data[field])

    await db.commit()
    await db.refresh(entry)
    return {"id": str(entry.id), "title": entry.title, "updated": True}


@router.delete("/entries/{entry_id}")
async def delete_entry(entry_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = select(InfoEntry).where(InfoEntry.user_id == current_user.id).where(InfoEntry.id == UUID(entry_id))
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "条目不存在")
    await db.delete(entry)
    await db.commit()
    return {"deleted": True}


@router.post("/entries/{entry_id}/optimize")
async def optimize_entry(entry_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = select(InfoEntry).where(InfoEntry.user_id == current_user.id).where(InfoEntry.id == UUID(entry_id))
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "条目不存在")

    try:
        optimized = await optimize_engine.optimize(
            title=entry.title,
            content=entry.content or "",
            category=entry.category.value,
        )
    except Exception as e:
        raise HTTPException(500, f"AI 优化失败: {str(e)}")

    return {
        "entry_id": entry_id,
        "original": {"title": entry.title, "content": entry.content},
        "optimized": {
            "title": optimized.get("title", entry.title),
            "content": optimized.get("content", entry.content),
            "improvements": optimized.get("improvements", []),
        },
    }


@router.post("/analyze-text")
async def analyze_text(data: dict, current_user: User = Depends(get_current_user)):
    text = data.get("text", "").strip()
    if not text:
        raise HTTPException(400, "文本不能为空")
    try:
        extractor = InfoExtractor()
        result = await extractor.extract(text)
        return {
            "category": result.get("category", "project"),
            "title": result.get("title", "未命名"),
            "company": result.get("company", ""),
            "content": result.get("content", text),
            "raw_text": text,
        }
    except Exception as e:
        raise HTTPException(500, f"AI 分析失败: {str(e)}")


@router.post("/detect-duplicates")
async def api_detect_duplicates(category: str = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = select(InfoEntry).where(InfoEntry.user_id == current_user.id).order_by(InfoEntry.created_at.desc())
    if category:
        stmt = stmt.where(InfoEntry.category == category)
    result = await db.execute(stmt)
    entries = result.scalars().all()
    entry_dicts = [{"id": str(e.id), "category": e.category.value, "title": e.title, "company": e.company, "content": e.content or ""} for e in entries]
    groups = detect_duplicates(entry_dicts, category)
    return {"total_entries": len(entries), "duplicate_groups": len(groups), "groups": [{"entries": g, "total": len(g)} for g in groups]}


@router.post("/merge")
async def api_merge(data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    entry_ids = data.get("entry_ids", [])
    use_ai = data.get("use_ai", False)
    if len(entry_ids) < 2:
        raise HTTPException(400, "至少需要2个条目才能合并")

    entries = []
    for eid in entry_ids:
        stmt = select(InfoEntry).where(InfoEntry.user_id == current_user.id).where(InfoEntry.id == UUID(eid))
        result = await db.execute(stmt)
        e = result.scalar_one_or_none()
        if e:
            entries.append(e)

    if len(entries) < 2:
        raise HTTPException(400, "找不到足够的条目")

    best = max(entries, key=lambda e: len(e.content or ""))
    others = [e for e in entries if e.id != best.id]

    if use_ai:
        combined = f"原标题: {best.title}\\n原内容: {best.content or ''}"
        for o in others:
            combined += f"\\n\\n补充内容 (来源: {o.title}): {o.content or ''}"
        try:
            optimized = await optimize_engine.optimize(title=best.title, content=combined, category=best.category.value)
            best.title = optimized.get("title", best.title)
            best.content = optimized.get("content", best.content)
        except Exception as e:
            raise HTTPException(500, f"AI 合并失败: {str(e)}")
    else:
        existing = set(best.content or "").union(set(best.title))
        extras = []
        for o in others:
            oc = o.content or ""
            unique_parts = [p for p in oc.split("；") if p.strip() and p.strip() not in str(existing)]
            if unique_parts:
                extras.extend(unique_parts)
        if extras:
            best.content = (best.content or "") + "；" + "；".join(extras)

    for o in others:
        await db.delete(o)
    await db.commit()
    await db.refresh(best)

    return {"merged": {"id": str(best.id), "title": best.title, "content": best.content, "category": best.category.value}, "deleted": [str(o.id) for o in others], "deleted_count": len(others)}
