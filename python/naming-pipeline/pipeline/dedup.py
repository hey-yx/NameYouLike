"""去重与碰撞检测：精确键（规范化名称）+ 语音键（无声调拼音）。"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import Optional

# 语音键的唯一口径在引擎侧 brandgen.stats.collision_key（碰撞索引由引擎消费，
# 两侧口径必须一致，否则排雷静默失效）。naming-pipeline 是仓库内子项目：
# 把 python/ 包根加入 sys.path 后直接复用同一实现，不再本地维护第二份。
_PYTHON_ROOT = Path(__file__).resolve().parents[2]
if str(_PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(_PYTHON_ROOT))
from brandgen.stats import collision_key  # noqa: E402  # pyright: ignore[reportMissingImports]

NON_ALNUM_RE = re.compile(r"[^0-9a-zA-Z\u4e00-\u9fff]")


def norm_key(name: str) -> str:
    """规范化键：只保留 CJK/字母/数字，小写。"""
    return NON_ALNUM_RE.sub("", name).lower()


def record_id(source: str, name_raw: str) -> str:
    return hashlib.sha1((source + "\x1f" + name_raw).encode("utf-8")).hexdigest()[:16]


# 语音键**单一来源**：phonetic_key 只是 brandgen.stats.collision_key 的转发别名
# （兼容 pipeline/stats.py、consumer.py 的既有调用名），不做二次包装，
# 保证与引擎侧查询口径是同一个函数对象（tests/test_phonetics_contract.py 锁定）。
phonetic_key = collision_key


class DedupIndex:
    """跨源去重索引：record_id / 精确名称键 / 语音键 三层。"""

    def __init__(self) -> None:
        self.by_record_id: set[str] = set()
        self.by_exact: dict[str, dict] = {}
        self.by_phonetic: dict[str, dict] = {}

    @staticmethod
    def _richness(rec: dict) -> tuple:
        # 值越大的记录越"富有"，冲突时保留富有者
        kind_rank = {"brand_tradename": 2, "famous_brand": 1}.get(rec.get("kind"), 0)
        return (
            1 if rec.get("domain") else 0,
            1 if rec.get("industry") else 0,
            kind_rank,
            rec.get("source_priority", 0),
        )

    def add(self, rec: dict) -> dict:
        """加入记录；返回实际保留的记录（可能是已存在的旧记录）。

        rec 需含: record_id, source, name_clean。
        """
        rid = rec["record_id"]
        exact = norm_key(rec["name_clean"])
        ph = phonetic_key(rec["name_clean"])
        # 1) 同源同原始名 -> 幂等
        if rid in self.by_record_id:
            return self._lookup(rid, exact, rec)
        # 2) 精确名称冲突（跨源同名）
        if exact in self.by_exact:
            old = self.by_exact[exact]
            if self._richness(rec) > self._richness(old):
                self._replace(old, rec)
                return rec
            return old
        # 3) 语音冲突（同音不同字：淘宝 vs 桃宝）——保留富有者，弱者标记 phonetic_dup
        if ph and ph in self.by_phonetic:
            old = self.by_phonetic[ph]
            if self._richness(rec) > self._richness(old):
                self._replace(old, rec)
                return rec
            rec["phonetic_dup_of"] = old["name_clean"]
            self.by_record_id.add(rid)
            return old
        self._insert_new(rec, rid, exact, ph)
        return rec

    def _insert_new(self, rec: dict, rid: str, exact: str, ph: Optional[str]) -> None:
        self.by_record_id.add(rid)
        self.by_exact[exact] = rec
        if ph and ph not in self.by_phonetic:
            self.by_phonetic[ph] = rec

    def _replace(self, old: dict, new: dict) -> None:
        rid = new["record_id"]
        exact = norm_key(new["name_clean"])
        ph = phonetic_key(new["name_clean"])
        self.by_record_id.add(rid)
        self.by_exact[exact] = new
        if ph:
            self.by_phonetic[ph] = new

    def _lookup(self, rid: str, exact: str, rec: dict) -> dict:
        found = self.by_exact.get(exact)
        if found and found["record_id"] == rid:
            return found
        # record_id 命中但 exact 表被更富有的记录占据：返回占据者
        if exact in self.by_exact:
            return self.by_exact[exact]
        self._insert_new(rec, rid, exact, phonetic_key(rec["name_clean"]))
        return rec

    def collision_check(self, name: str) -> Optional[dict]:
        """供推荐引擎使用：返回精确/语音碰撞信息，无碰撞返回 None。"""
        exact = norm_key(name)
        if exact in self.by_exact:
            return {"type": "exact", "existing": self.by_exact[exact]["name_clean"]}
        ph = phonetic_key(name)
        if ph and ph in self.by_phonetic:
            return {"type": "phonetic", "existing": self.by_phonetic[ph]["name_clean"]}
        return None
