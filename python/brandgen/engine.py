"""品牌名生成引擎：种子词 + 风格参数 → 批量候选（含变体与域名建议）。

流水线：构词池（规则 + 风格词库 + 外部注入词）→ 拼音/简拼/破折号变体
→ 启发式打分排序 → 域名形式生成（可选在线可用性核验）。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from .domains import STATUS_LABEL, DomainSuggestion, check_many, generate_forms
from .lexicon import AFFIXES, MORPHEMES
from .patterns import NamePatterns, build
from .pinyin_util import is_hanzi
from .stats import PatternStats, load_patterns

MAX_SEED_LEN = 6


@dataclass
class StyleParams:
    """风格参数：控制构词取向、长度过滤、域名池与核验行为。"""

    style: str = "neutral"  # tech / classic / international / playful / neutral
    lengths: tuple[int, ...] = (2, 3, 4)  # 允许的候选名字长（字）
    limit: int = 20  # 输出候选数
    tlds: list[str] | None = None  # 域名 TLD 池（None=默认池）
    max_domains: int = 8  # 每个候选生成的域名形式数
    live_check: bool = False  # 是否在线核验域名可用性
    live_per_name: int = 3  # 每个候选在线核验的域名形式数（按时序取前 N）
    extra_vocab: list[str] | None = None  # 外部词汇注入（如生肖、星宿词）
    include_seed: bool = True  # 种子词本身是否进入候选
    patterns_file: str | None = None  # 命名模式统计文件（opt-in；None=不启用，行为同 v1）


@dataclass
class BrandCandidate:
    """一个候选品牌名：中文名 + 全部拉丁变体 + 域名建议。

    collision / phonetic 仅在启用命名统计（StyleParams.patterns_file）时填充：
    collision 为与现有品牌的碰撞标注（同音强降权后保留），phonetic 为音节自然度。
    """

    name: str
    patterns: NamePatterns
    origin: str  # 构词来源说明
    score: float
    domains: list[DomainSuggestion]
    collision: dict[str, str] | None = None  # {'type': 'phonetic', 'existing': …}
    phonetic: float | None = None  # 音节自然度 ∈ [0,1]（统计模式）

    def as_dict(self) -> dict[str, object]:
        out: dict[str, object] = {
            "name": self.name,
            "variants": self.patterns.as_dict(),
            "origin": self.origin,
            "score": round(self.score, 2),
            "domains": [
                {
                    "domain": d.domain,
                    "pattern": d.pattern,
                    "status": d.status,
                    "status_label": STATUS_LABEL[d.status],
                    "method": d.method,
                    "note": d.note,
                    "checked_at": d.checked_at,
                }
                for d in self.domains
            ],
        }
        # 统计模式字段为「加性」：未启用时 JSON 与 v1 契约逐字节同构，
        # 已有下游引擎不启用统计即不受影响。
        if self.phonetic is not None or self.collision is not None:
            out["phonetic"] = self.phonetic
            out["collision"] = self.collision
        return out


def _dedupe(seq: list[str]) -> list[str]:
    return list(dict.fromkeys(seq))


class BrandEngine:
    """生成引擎。BrandEngine(StyleParams(...)).generate(seeds) → list[BrandCandidate]。"""

    def __init__(self, params: StyleParams | None = None, *,
                 stats: PatternStats | None = None):
        """``stats``：调用方已解析好的命名统计（如 CLI 单次解析后传入）。

        与 ``params.patterns_file`` 同时给出时 ``stats`` 优先——避免同一统计文件
        在一次请求里被重复解析。不传 ``stats`` 且给了 ``patterns_file`` 时才加载。
        """
        self.params = params or StyleParams()
        if self.params.style not in AFFIXES:
            raise ValueError(
                f"未知风格 {self.params.style!r}；可选: {', '.join(AFFIXES)}"
            )
        if not self.params.lengths or any(n < 2 or n > 6 for n in self.params.lengths):
            raise ValueError("lengths 必须为 2-6 之间的非空集合")
        # 命名模式统计（opt-in）：拼音自然度权重 + 品牌碰撞排雷。
        # 文件缺失/结构不符立即报错——静默降级会让调用方误以为排雷已生效。
        self.stats: PatternStats | None = None
        if stats is not None:
            if not isinstance(stats, PatternStats):
                raise TypeError("stats 必须是 PatternStats 实例")
            self.stats = stats
        elif self.params.patterns_file:
            self.stats = load_patterns(self.params.patterns_file)
        self.last_dropped: list[dict[str, str]] = []  # 最近一次 generate() 剔除的精确重名

    # ------------------------------------------------------------------ 对外 API

    def generate(self, seeds: list[str]) -> list[BrandCandidate]:
        """给定种子词（1-6 个汉字），批量产出候选品牌名列表。"""
        p = self.params
        seeds = self._validate_seeds(seeds)
        self.last_dropped = []
        candidates: list[BrandCandidate] = []
        for name, origin in self._build_pool(seeds):
            collision = self.stats.collision(name) if self.stats else None
            if collision and collision["type"] == "exact":
                # 精确重名：直接剔除。引擎的职责是产出「新」名，重名候选
                # 哪怕降权到 0 也不该出现在交付列表里；剔除记录留档可审计。
                self.last_dropped.append(
                    {"name": name, "origin": origin, **collision}
                )
                continue
            np = build(name)
            domains = generate_forms(
                np, tlds=p.tlds, style=p.style, max_forms=p.max_domains
            )
            score = self._base_score(np, origin)
            phonetic: float | None = None
            if self.stats:
                # 音节自然度：读音组合贴近真实品牌语料的候选加分（权重与
                # 其他启发式同量级，只影响排序、不构成一票否决）。
                phonetic = self.stats.phonetic_naturalness(np)
                score += round(phonetic * 1.2, 2)
                if collision:  # 此处只剩 phonetic：同音已有品牌，强降权
                    score = round(score * 0.4, 2)
            candidates.append(
                BrandCandidate(
                    name=name,
                    patterns=np,
                    origin=origin,
                    score=round(score, 2),
                    domains=domains,
                    collision=collision,
                    phonetic=phonetic,
                )
            )
        candidates.sort(key=lambda c: (-c.score, _tie_key(c.name)))
        candidates = candidates[: p.limit]
        if p.live_check and candidates:
            targets = [d for c in candidates for d in c.domains[: p.live_per_name]]
            check_many(targets)
            for c in candidates:
                c.score = round(c.score + _availability_bonus(c.domains[: p.live_per_name]), 2)
            candidates.sort(key=lambda c: (-c.score, _tie_key(c.name)))
        return candidates

    # ------------------------------------------------------------------ 构词

    def _validate_seeds(self, seeds: list[str]) -> list[str]:
        if not seeds:
            raise ValueError("种子词列表不能为空")
        clean, invalid = [], []
        for s in seeds:
            s = (s or "").strip()
            if s and is_hanzi(s) and len(s) <= MAX_SEED_LEN:
                clean.append(s)
            else:
                invalid.append(s or "<空>")
        if invalid:
            raise ValueError(f"种子词必须为 1-{MAX_SEED_LEN} 个纯汉字: {invalid}")
        return _dedupe(clean)

    def _build_pool(self, seeds: list[str]) -> list[tuple[str, str]]:
        """构词池：返回 (名字, 构词来源) 列表，插入序去重、结果确定。"""
        p = self.params
        prefixes = AFFIXES[p.style]["prefix"]
        suffixes = AFFIXES[p.style]["suffix"]
        morphemes = MORPHEMES.get(p.style, MORPHEMES["neutral"])
        vocab = _dedupe(p.extra_vocab or [])

        pool: dict[str, str] = {}

        def add(name: str, origin: str) -> None:
            if not name or not is_hanzi(name) or len(name) not in p.lengths:
                return
            pool.setdefault(name, origin)

        for seed in seeds:
            if p.include_seed:
                add(seed, f"种子词直用：{seed}")
            for a in suffixes:
                add(f"{seed}{a}", f"种子词『{seed}』+ 风格后缀『{a}』")
            for a in prefixes:
                add(f"{a}{seed}", f"风格前缀『{a}』+ 种子词『{seed}』")
            for ch in dict.fromkeys(seed):  # 插入序，保证跨进程确定性
                for a in suffixes:
                    if len(a) == 1:
                        add(f"{ch}{a}", f"种子字『{ch}』+ 后缀字『{a}』")
                for a in prefixes:
                    if len(a) == 1:
                        add(f"{a}{ch}", f"前缀字『{a}』+ 种子字『{ch}』")
                # 注入词优先于风格语素：注入词汇若与语素库撞词（如 classic 语素
                # 库本身含『鲲』），必须保留注入意图（origin 标注 + 排序加成），
                # 否则 setdefault 会让后到的通用语素覆盖不了、先到的通用语素冒领。
                for v in vocab:
                    add(f"{ch}{v}", f"种子字『{ch}』+ 注入词『{v}』")
                    add(f"{v}{ch}", f"注入词『{v}』+ 种子字『{ch}』")
                for m in morphemes:
                    add(f"{ch}{m}", f"种子字『{ch}』+ 风格语素『{m}』")
                    add(f"{m}{ch}", f"风格语素『{m}』+ 种子字『{ch}』")

        for v in vocab:
            if p.include_seed:
                add(v, f"注入词直用：{v}")

        # 跨种子组合
        for i, s1 in enumerate(seeds):
            for s2 in seeds[i + 1 :]:
                add(f"{s1}{s2[0]}", f"种子『{s1}』+ 种子『{s2}』首字")
                add(f"{s2}{s1[0]}", f"种子『{s2}』+ 种子『{s1}』首字")
                add(f"{s1[0]}{s2[0]}", f"种子『{s1}』首字 + 种子『{s2}』首字")

        return list(pool.items())

    # ------------------------------------------------------------------ 打分

    def _base_score(self, np: NamePatterns, origin: str) -> float:
        """启发式分值：只依赖名字本身与来源，与池内顺序无关（确定性）。"""
        s = 0.0
        n = len(np.name)
        if n == 2:
            s += 2.0  # 两字名记忆成本最低
        elif n == 3:
            s += 1.0
        if len(np.pinyin) <= 6:
            s += 1.0  # 拼音短、易拼读
        if len(np.pinyin) <= 4:
            s += 0.5
        if any(ch in "aeiou" for ch in np.initials):
            s += 0.5  # 简拼自带元音，可作单词发音（如 kimi 型）
        if "种子词直用" in origin:
            s += 1.5  # 最贴近用户原始意图
        elif "注入词" in origin:
            s += 0.8  # 外部注入词组合，确保注入词能在候选中浮出
        return round(s, 2)


def _tie_key(name: str) -> str:
    """同分候选的确定性打散键。

    若按 Unicode 码点排序，同分段会被某个种子字的同旁名字挤满（如全部『兔』开头），
    小 limit 下其他种子字完全没有出场机会。用名字的稳定散列打散同分段：
    跨进程确定（md5 不受 PYTHONHASHSEED 影响），且各种子字的组合均匀分布。
    """
    return hashlib.md5(name.encode("utf-8")).hexdigest()


def _availability_bonus(domains: list[DomainSuggestion]) -> float:
    """在线核验结果对排序的加成。只依据已核验过的域名子集。"""
    if not any(d.status != "unknown" for d in domains):
        return 0.0
    if any(d.status == "likely_available" and d.tld == "com" for d in domains):
        return 3.0
    if any(d.status == "likely_available" for d in domains):
        return 1.0
    return 0.0
