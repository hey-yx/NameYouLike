"""命名模式统计消费：拼音自然度权重 + 品牌碰撞排雷。

数据来源（上游数据管道任务交付）：
- 完整格式 ``naming_patterns.v1.json``（schema ``naming-patterns/v1``）：
  ``recommendation_weights.w_initial``（首字母分布）、``w_syllable``（Top150 音节）、
  ``collision_index.exact_names``（精确品牌名）、``collision_index.phonetic_keys``
  （无声调拼音键 → 已有品牌）。
- 瘦身格式 ``naming_patterns.slim.json``（schema ``brandgen/pattern-stats-slim/v1``）：
  引擎内置数据，字段平铺，附带来源版本（provenance）。

碰撞语义与上游 ``pipeline/consumer.py`` 参考实现保持一致：
- 精确重名（exact）→ 候选直接剔除（引擎生成的是「新」品牌名）；
- 同音碰撞（phonetic）→ 强降权（评分 ×0.4）并标注已有品牌。

语音键口径注意：上游索引按**逐字** ``lazy_pinyin`` 拼接构建（多音字取默认读音，
如 银行 → ``yinxing``），与引擎变体的**词组级**拼音（``yinhang``，pypinyin 词组
词典消歧）可能不同。查碰撞必须用逐字口径，否则查不中索引。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from pypinyin import lazy_pinyin

from .patterns import NamePatterns
from .pinyin_util import is_hanzi

FULL_SCHEMA = "naming-patterns/v1"
SLIM_SCHEMA = "brandgen/pattern-stats-slim/v1"


def collision_key(name: str) -> str | None:
    """语音键：逐字无声调拼音连写（碰撞索引构建与查询的**唯一口径**）。

    仅对 ≥2 个纯汉字的名称可靠（允许空格分隔，忽略空格），其余返回 None。
    多音字取 pypinyin 默认常用读音（如 银行 → yinxing）。数据管道的
    ``pipeline/dedup.py::phonetic_key`` 直接复用本函数——索引构建与碰撞查询
    必须同口径，否则排雷会静默失效（查不中索引）。
    """
    if not name:
        return None
    stripped = name.replace(" ", "")
    if len(stripped) < 2 or not is_hanzi(stripped):
        return None
    return "".join(lazy_pinyin(ch)[0] for ch in stripped) or None


@dataclass(frozen=True)
class PatternStats:
    """统计文件的引擎侧消费视图（加载后只读）。"""

    version: str
    source: str  # 加载路径（provenance）
    w_initial: dict[str, float] = field(default_factory=dict)
    w_syllable: dict[str, float] = field(default_factory=dict)
    exact_names: frozenset[str] = frozenset()
    phonetic_keys: dict[str, str] = field(default_factory=dict)
    max_initial: float = 0.0  # 归一化基准（加载时预计算）
    max_syllable: float = 0.0

    # ------------------------------------------------------------------ 消费 API

    def phonetic_naturalness(self, np: NamePatterns) -> float:
        """音节自然度 ∈ [0,1]：首字母分布 × 0.5 + 音节分布均值 × 0.5（各自归一化）。

        值高 = 读音组合接近真实品牌语料（如 h/s/z/l/y 开头、ji/ke/xin 音节常见），
        生僻组合（如冷门声母 + 罕见音节）得低分。仅依赖名字读音，结果确定。
        """
        if not np.syllables:
            return 0.0
        ini = 0.0
        if self.w_initial and self.max_initial > 0:
            ini = self.w_initial.get(np.pinyin[:1], 0.0) / self.max_initial
        syl = 0.0
        if self.w_syllable and self.max_syllable > 0:
            vals = [self.w_syllable.get(s, 0.0) for s in np.syllables]
            syl = sum(vals) / len(vals) / self.max_syllable
        return round(0.5 * ini + 0.5 * syl, 4)

    def collision(self, name: str) -> dict[str, str] | None:
        """碰撞检测：精确重名 → {'type':'exact'}；同音 → {'type':'phonetic'}。"""
        if name in self.exact_names:
            return {"type": "exact", "existing": name}
        key = collision_key(name)
        if key and key in self.phonetic_keys:
            return {"type": "phonetic", "existing": self.phonetic_keys[key]}
        return None


# ---------------------------------------------------------------------- 加载

def _finalize(
    version: str,
    source: str,
    w_initial: dict[str, float],
    w_syllable: dict[str, float],
    exact_names: Any,
    phonetic_keys: Any,
) -> PatternStats:
    return PatternStats(
        version=version,
        source=source,
        w_initial={k: float(v) for k, v in (w_initial or {}).items()},
        w_syllable={k: float(v) for k, v in (w_syllable or {}).items()},
        exact_names=frozenset(exact_names or []),
        phonetic_keys=dict(phonetic_keys or {}),
        max_initial=max((float(v) for v in (w_initial or {}).values()), default=0.0),
        max_syllable=max((float(v) for v in (w_syllable or {}).values()), default=0.0),
    )


def load_patterns(path: str) -> PatternStats:
    """加载统计文件（完整格式或瘦身格式），结构不符时明确报错。"""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise ValueError(f"统计文件不存在: {path}") from None
    except json.JSONDecodeError as e:
        raise ValueError(f"统计文件不是合法 JSON: {path}（{e}）") from None

    schema = data.get("schema")
    if schema == FULL_SCHEMA:
        rw = data.get("recommendation_weights") or {}
        coll = data.get("collision_index") or {}
        return _finalize(
            version=str(data.get("version", "?")),
            source=path,
            w_initial=rw.get("w_initial") or data.get("pinyin_initial_dist") or {},
            w_syllable=rw.get("w_syllable") or data.get("pinyin_syllable_dist") or {},
            exact_names=coll.get("exact_names"),
            phonetic_keys=coll.get("phonetic_keys"),
        )
    if schema == SLIM_SCHEMA:
        return _finalize(
            version=str(data.get("version", "?")),
            source=path,
            w_initial=data.get("w_initial"),
            w_syllable=data.get("w_syllable"),
            exact_names=data.get("exact_names"),
            phonetic_keys=data.get("phonetic_keys"),
        )
    raise ValueError(
        f"统计文件 schema 不受支持: {schema!r}（需要 {FULL_SCHEMA} 或 {SLIM_SCHEMA}）: {path}"
    )


# ---------------------------------------------------------------------- 瘦身提取

def extract_slim(src: str, dst: str) -> dict[str, Any]:
    """从管道完整统计文件提取引擎所需字段，写出瘦身格式（含 provenance）。

    只保留 w_initial / w_syllable / exact_names / phonetic_keys 四项，
    供 ``brandgen/data/`` 内置打包，引擎离线开箱即可用真实统计。
    """
    stats = load_patterns(src)
    slim = {
        "schema": SLIM_SCHEMA,
        "version": stats.version,
        "provenance": {
            "source_file": src,
            "full_schema": FULL_SCHEMA,
            "fields": ["w_initial", "w_syllable", "exact_names", "phonetic_keys"],
            "note": "由 brandgen.stats.extract_slim 从管道完整统计提取",
        },
        "w_initial": stats.w_initial,
        "w_syllable": stats.w_syllable,
        "exact_names": sorted(stats.exact_names),
        "phonetic_keys": stats.phonetic_keys,
    }
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(slim, f, ensure_ascii=False, sort_keys=True)
    return {
        "version": stats.version,
        "w_initial": len(stats.w_initial),
        "w_syllable": len(stats.w_syllable),
        "exact_names": len(stats.exact_names),
        "phonetic_keys": len(stats.phonetic_keys),
    }
