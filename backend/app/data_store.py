"""统一本地 JSON 文件存储 — 所有数据镜像到 /app/data/{type}/{id}.json"""
import json, os
from pathlib import Path
from typing import Optional

DATA_DIR = Path(os.environ.get("DATA_DIR", "/app/data"))


def _ensure_dir(entity_type: str) -> Path:
    d = DATA_DIR / entity_type
    d.mkdir(parents=True, exist_ok=True)
    return d


def save(entity_type: str, entity_id: str, data: dict):
    """保存实体到本地 JSON 文件"""
    try:
        _ensure_dir(entity_type)
        path = DATA_DIR / entity_type / f"{entity_id}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, default=str), encoding='utf-8')
    except Exception:
        pass


def load(entity_type: str, entity_id: str) -> Optional[dict]:
    """从本地 JSON 文件读取实体"""
    try:
        path = DATA_DIR / entity_type / f"{entity_id}.json"
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        pass
    return None


def delete(entity_type: str, entity_id: str):
    """删除本地 JSON 文件"""
    try:
        path = DATA_DIR / entity_type / f"{entity_id}.json"
        if path.exists():
            path.unlink()
    except Exception:
        pass


def list_all(entity_type: str) -> list[dict]:
    """列出某类型下所有实体（按修改时间倒序）"""
    d = DATA_DIR / entity_type
    if not d.exists():
        return []
    results = []
    for f in sorted(d.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            results.append(json.loads(f.read_text(encoding='utf-8')))
        except Exception:
            pass
    return results
