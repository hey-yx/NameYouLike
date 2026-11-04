"""拼音底层：汉字 → 全拼 / 声母 / 韵母 / 声调。

基于 pypinyin。多音字取 pypinyin 默认常用读音，保证输出确定性。
ü 统一输出为 v（pypinyin 默认），确保变体可直接用作域名字符。
"""
from __future__ import annotations

from dataclasses import dataclass

from pypinyin import Style, pinyin


def _is_han(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff"


def is_hanzi(text: str) -> bool:
    """全部字符均为汉字且非空。"""
    return bool(text) and all(_is_han(ch) for ch in text)


@dataclass(frozen=True)
class Syllable:
    """单字音节。"""

    char: str
    plain: str  # 无声调全拼，如 'chi'
    toned: str  # 带声调，如 'chì'
    initial: str  # 声母，如 'ch'；零声母为 ''
    final: str  # 韵母，如 'i'


def convert(text: str) -> list[Syllable]:
    """整词转拼音（利用 pypinyin 词组词典消歧多音字）。"""
    plains = pinyin(text, style=Style.NORMAL)
    toneds = pinyin(text, style=Style.TONE)
    inits = pinyin(text, style=Style.INITIALS)
    finals = pinyin(text, style=Style.FINALS)
    syllables: list[Syllable] = []
    for i, ch in enumerate(text):
        syllables.append(
            Syllable(
                char=ch,
                plain=plains[i][0].lower(),
                toned=toneds[i][0].lower(),
                initial=(inits[i][0].lower() if inits[i] else ""),
                final=(finals[i][0].lower() if finals[i] else ""),
            )
        )
    return syllables


def initials(syllables: list[Syllable]) -> str:
    """声母简拼：逐字取声母拼接；零声母字回退为读音首字母。

    赤兔 → ch + t → 'cht'（任务验收示例）。
    """
    return "".join(s.initial or s.plain[:1] for s in syllables)


def letters(syllables: list[Syllable]) -> str:
    """每字首字母：赤兔 → 'ct'。补充变体，供域名/商标形态参考。"""
    return "".join(s.plain[:1] for s in syllables)
