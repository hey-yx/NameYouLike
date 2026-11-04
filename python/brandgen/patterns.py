"""模式引擎：汉字品牌名 → 拼音全拼 / 声母简拼 / 破折号 等规范变体。

所有变体均为 ASCII、可安全用作域名/商标拉丁转写。
"""
from __future__ import annotations

from dataclasses import dataclass

from .pinyin_util import convert, initials, is_hanzi, letters


@dataclass(frozen=True)
class NamePatterns:
    """一个品牌名的全部拉丁转写变体。"""

    name: str  # 中文原名
    pinyin: str  # 拼音全拼，小写连写，如 'chitu'
    pinyin_toned: str  # 带声调显示形式，如 'chì tù'
    syllables: tuple[str, ...]  # 逐字全拼，如 ('chi', 'tu')
    initials: str  # 声母简拼，如 'cht'（赤兔：ch+t）
    letters: str  # 每字首字母，如 'ct'
    dash: str  # 破折号组合（首字母大写），如 'Chi-Tu'
    kebab: str  # 全拼短横线，如 'chi-tu'
    camel: str  # 驼峰，如 'ChiTu'

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "pinyin": self.pinyin,
            "pinyin_toned": self.pinyin_toned,
            "syllables": list(self.syllables),
            "initials": self.initials,
            "letters": self.letters,
            "dash": self.dash,
            "kebab": self.kebab,
            "camel": self.camel,
        }


def _cap(syl: str) -> str:
    return syl[:1].upper() + syl[1:]


def build(name: str) -> NamePatterns:
    """由纯汉字名构建全部变体。非纯汉字输入直接拒绝。"""
    if not name:
        raise ValueError("品牌名不能为空")
    if not is_hanzi(name):
        raise ValueError(f"品牌名必须是纯汉字: {name!r}")
    syls = convert(name)
    plains = [s.plain for s in syls]
    return NamePatterns(
        name=name,
        pinyin="".join(plains),
        pinyin_toned=" ".join(s.toned for s in syls),
        syllables=tuple(plains),
        initials=initials(syls),
        letters=letters(syls),
        dash="-".join(_cap(p) for p in plains),
        kebab="-".join(plains),
        camel="".join(_cap(p) for p in plains),
    )
