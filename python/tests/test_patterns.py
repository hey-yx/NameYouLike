"""模式引擎 seam 测试：汉字名 → 全拼/声母简拼/破折号 变体（验收标准原文样例）。"""
import pytest

from brandgen.patterns import NamePatterns, build


def test_acceptance_example_chitu():
    p = build("赤兔")
    assert isinstance(p, NamePatterns)
    assert p.name == "赤兔"
    assert p.pinyin == "chitu"
    assert p.initials == "cht"          # 声母简拼（任务示例）
    assert p.dash == "Chi-Tu"           # 破折号组合（任务示例）
    assert p.kebab == "chi-tu"
    assert p.camel == "ChiTu"
    assert p.letters == "ct"
    assert p.syllables == ("chi", "tu")
    assert p.pinyin_toned == "chì tù"


def test_three_char_name():
    p = build("赤兔云")
    assert p.pinyin == "chituyun"
    assert p.initials == "chty"
    assert p.dash == "Chi-Tu-Yun"


def test_zero_initial_name():
    p = build("安居")
    assert p.pinyin == "anju"
    assert p.initials == "aj"
    assert p.dash == "An-Ju"


def test_rejects_empty_name():
    with pytest.raises(ValueError):
        build("")


def test_rejects_non_hanzi():
    with pytest.raises(ValueError):
        build("赤兔A")


def test_all_pattern_strings_are_domain_safe():
    for p_field in ("pinyin", "initials", "letters", "dash", "kebab", "camel"):
        v = getattr(build("赤兔飞跃"), p_field)
        assert all(c.isascii() and (c.isalnum() or c == "-") for c in v), p_field
