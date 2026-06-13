"""去重检测引擎"""
import logging, re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def normalize_title(title: str) -> str:
    """标准化标题用于比较"""
    t = title.lower().strip()
    t = re.sub(r"[（(].*?[)）]", "", t)  # 去掉括号内容
    t = re.sub(r"[/\|、，,]", " ", t)   # 分隔符统一
    t = re.sub(r"\s+", " ", t).strip()
    return t


def title_similarity(a: str, b: str) -> float:
    """标题相似度"""
    return SequenceMatcher(None, normalize_title(a), normalize_title(b)).ratio()


def content_similarity(a: str, b: str) -> float:
    """内容相似度（基于词袋 Jaccard）"""
    if not a or not b:
        return 0.0
    def tokens(s):
        return set(re.findall(r"[\w一-鿿]+", s.lower()))
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def detect_duplicates(entries: list[dict], category: str = None) -> list[dict]:
    """
    检测重复条目，返回分组
    每个条目需有: id, category, title, company, content
    """
    if category:
        entries = [e for e in entries if e["category"] == category]
    
    groups = []
    used = set()
    
    for i, a in enumerate(entries):
        if a["id"] in used:
            continue
        group = [a]
        for j, b in enumerate(entries):
            if j <= i or b["id"] in used:
                continue
            
            # 判断是否重复
            same_company = a.get("company") and b.get("company") and a["company"] == b["company"]
            title_sim = title_similarity(a["title"], b["title"])
            content_sim = content_similarity(a.get("content", ""), b.get("content", ""))
            
            is_dup = False
            reason = ""
            
            # 规则1: 同公司 + 标题完全相同
            if same_company and a["title"] == b["title"]:
                is_dup = True
                reason = "同公司同标题"
            # 规则2: 同公司 + 标题高度相似 (>=0.85)
            elif same_company and title_sim >= 0.85:
                is_dup = True
                reason = f"同公司标题相似({title_sim:.0%})"
            # 规则3: 标题高度相似 + 内容高度相似
            elif title_sim >= 0.8 and content_sim >= 0.5:
                is_dup = True
                reason = f"标题{title_sim:.0%}+内容{content_sim:.0%}"
            # 规则4: 无公司 + 标题完全相同
            elif not a.get("company") and title_sim >= 0.95:
                is_dup = True
                reason = f"标题高度相似({title_sim:.0%})"
            
            if is_dup:
                b["_reason"] = reason
                b["_title_sim"] = round(title_sim, 2)
                b["_content_sim"] = round(content_sim, 2)
                group.append(b)
                used.add(b["id"])
        
        if len(group) > 1:
            used.add(a["id"])
            groups.append(group)
    
    return groups
