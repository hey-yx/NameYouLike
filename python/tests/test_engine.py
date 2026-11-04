"""生成引擎 seam 测试：种子词 + 风格参数 → 批量候选（验收标准）。"""
import pytest

from brandgen.engine import BrandCandidate, BrandEngine, StyleParams


def _eng(**kw):
    return BrandEngine(StyleParams(**kw))


def test_batch_generation_with_variants():
    """验收标准：给定种子词与风格参数，批量产出候选列表，每个候选附带全部变体。"""
    cands = _eng(style="tech", limit=12).generate(["赤兔"])
    assert isinstance(cands, list) and len(cands) == 12
    for c in cands:
        assert isinstance(c, BrandCandidate)
        assert all("\u4e00" <= ch <= "\u9fff" for ch in c.name)
        assert 2 <= len(c.name) <= 4
        assert c.patterns.pinyin and c.patterns.initials and c.patterns.dash
        assert c.origin  # 构词来源说明
        assert c.domains  # 域名形式已生成
        assert c.score >= 0


def test_seed_itself_is_first_candidate():
    cands = _eng(style="tech", limit=10).generate(["赤兔"])
    assert cands[0].name == "赤兔"
    assert "种子" in cands[0].origin


def test_style_affixes_reach_output():
    """风格后缀应参与构词：classic 里应出现『坊/阁/轩』类名字。"""
    cands = _eng(style="classic", limit=20).generate(["赤兔"])
    names = {c.name for c in cands}
    assert any(name != "赤兔" and any(a in name for a in "坊阁轩堂记斋") for name in names)


def test_extra_vocab_injection():
    """外部词汇注入（如『鲲』『麟』），必须出现在构词池。"""
    cands = _eng(style="tech", limit=20, extra_vocab=["鲲"]).generate(["赤兔"])
    assert any("鲲" in c.name for c in cands)


def test_injected_word_beats_duplicate_morpheme():
    """注入词与风格语素撞词时（classic 语素库本身含『鲲』），注入意图必须优先。"""
    cands = _eng(style="classic", limit=8, extra_vocab=["鲲"]).generate(["麒麟"])
    match = [c for c in cands if "鲲" in c.name]
    assert match, "注入词未浮出 top-N"
    assert all("注入词" in c.origin for c in match), [c.origin for c in match]


def test_deterministic_output():
    e = _eng(style="tech", limit=15)
    a = e.generate(["赤兔", "飞跃"])
    b = e.generate(["赤兔", "飞跃"])
    assert [c.name for c in a] == [c.name for c in b]


def test_different_styles_differ():
    t = _eng(style="tech", limit=15).generate(["灵犀"])
    c = _eng(style="classic", limit=15).generate(["灵犀"])
    assert {x.name for x in t} != {x.name for x in c}


def test_limit_respected():
    cands = _eng(style="tech", limit=5).generate(["赤兔", "飞跃", "灵犀"])
    assert len(cands) == 5


def test_rejects_invalid_seeds():
    with pytest.raises(ValueError):
        _eng(style="tech").generate(["赤兔A"])
    with pytest.raises(ValueError):
        _eng(style="tech").generate([])


def test_tlds_param_selects_forms():
    cands = _eng(style="tech", limit=3, tlds=["com", "xyz"]).generate(["赤兔"])
    for c in cands:
        assert {d.tld for d in c.domains} <= {"com", "xyz"}
        assert c.domains


def test_tie_groups_spread_across_seed_chars():
    """同分段不能被单一种子字挤满：小 limit 下各种子字都应有出场（候选 slate 多样性）。"""
    cands = _eng(style="tech", limit=12).generate(["赤兔", "飞跃"])
    derived = [c for c in cands if c.name not in ("赤兔", "飞跃")]
    first_chars = {c.name[0] for c in derived}
    assert len(first_chars) >= 3, f"同分打散失效，首位字仅 {first_chars}"


def test_live_bonus_keeps_two_decimals(monkeypatch):
    """在线可用性加成后分值仍为 2 位小数（防浮点尾巴泄漏到输出）。"""
    import brandgen.engine as eng_mod

    def fake_check_many(items):
        for s in items:
            s.status = "likely_available"
            s.method = "rdap"
        return items

    monkeypatch.setattr(eng_mod, "check_many", fake_check_many)
    cands = _eng(style="tech", limit=5, live_check=True).generate(["赤兔"])
    assert cands
    for c in cands:
        assert round(c.score, 2) == c.score
