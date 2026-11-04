"""拼音底层 seam 测试。

期望值来自任务验收标准中的独立样例：
赤兔 → 全拼 chitu / 声母简拼 cht（ch+t）/ 破折号 Chi-Tu。
"""
from brandgen.pinyin_util import convert, initials, letters


def test_chitu_syllables():
    syls = convert("赤兔")
    assert [s.plain for s in syls] == ["chi", "tu"]
    assert [s.initial for s in syls] == ["ch", "t"]
    assert [s.toned for s in syls] == ["chì", "tù"]


def test_initials_join_is_shengmu_concat():
    """声母简拼 = 逐字声母拼接。赤兔 → ch + t → cht（任务验收示例）。"""
    assert initials(convert("赤兔")) == "cht"


def test_zero_initial_falls_back_to_first_letter():
    """零声母字（如 安 ān）取读音首字母。"""
    assert initials(convert("安居")) == "aj"


def test_letters_is_first_letter_per_char():
    assert letters(convert("赤兔")) == "ct"


def test_umlaut_becomes_v_for_domain_safety():
    assert convert("绿")[0].plain == "lv"


def test_hanzi_check():
    from brandgen.pinyin_util import is_hanzi

    assert is_hanzi("赤兔")
    assert not is_hanzi("赤兔A")
    assert not is_hanzi("")
