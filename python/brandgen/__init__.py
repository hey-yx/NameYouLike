"""brandgen —— 品牌名生成引擎。

种子词 + 风格参数 → 批量候选品牌名，每个候选附带：
拼音全拼 / 声母简拼（如 赤兔→cht）/ 破折号组合（如 Chi-Tu）等拉丁变体，
以及域名形式与可用性建议。

用法：
    from brandgen import BrandEngine, StyleParams
    engine = BrandEngine(StyleParams(style="tech", limit=12, live_check=True))
    candidates = engine.generate(["赤兔", "飞跃"])
"""

from .domains import (
    DEFAULT_TLDS,
    STATUS_LABEL,
    DomainSuggestion,
    check_domain,
    check_many,
    generate_forms,
)
from .engine import BrandCandidate, BrandEngine, StyleParams
from .patterns import NamePatterns, build
from .pinyin_util import Syllable, convert, initials, is_hanzi, letters
from .signals import (
    find_patterns,
    find_patterns_file,
    packaged_patterns_file,
    pipeline_patterns_file,
)
from .stats import PatternStats, collision_key, extract_slim, load_patterns

__all__ = [
    "BrandCandidate",
    "BrandEngine",
    "StyleParams",
    "NamePatterns",
    "build",
    "DomainSuggestion",
    "generate_forms",
    "check_domain",
    "check_many",
    "DEFAULT_TLDS",
    "STATUS_LABEL",
    "Syllable",
    "convert",
    "initials",
    "letters",
    "is_hanzi",
    "PatternStats",
    "load_patterns",
    "collision_key",
    "extract_slim",
    "find_patterns",
    "find_patterns_file",
    "packaged_patterns_file",
    "pipeline_patterns_file",
]
__version__ = "0.2.0"
