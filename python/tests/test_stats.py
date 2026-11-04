"""命名统计集成测试：音节自然度权重 + 品牌碰撞排雷（数据管道交付消费）。

合成统计文件走瘦身格式（最小可构造）；另有针对内置真实数据与完整管道格式的
集成测试。全部离线、确定性。
"""
import json
from pathlib import Path

import pytest

from brandgen import BrandEngine, StyleParams, build
from brandgen.stats import (
    SLIM_SCHEMA,
    PatternStats,
    collision_key,
    load_patterns,
)

BUNDLED = (
    Path(__file__).resolve().parent.parent
    / "brandgen"
    / "data"
    / "naming_patterns.slim.json"
)

V1_KEYS = {"name", "variants", "origin", "score", "domains"}


# ------------------------------------------------------------------ 构造工具

def _slim(
    path,
    *,
    w_initial=None,
    w_syllable=None,
    exact_names=None,
    phonetic_keys=None,
):
    data = {
        "schema": SLIM_SCHEMA,
        "version": "test-synth-1",
        "w_initial": w_initial or {},
        "w_syllable": w_syllable or {},
        "exact_names": exact_names or [],
        "phonetic_keys": phonetic_keys or {},
    }
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )
    return str(path)


def _full(path):
    data = {
        "schema": "naming-patterns/v1",
        "version": "test-full-1",
        "recommendation_weights": {
            "w_initial": {"h": 0.5, "c": 0.2},
            "w_syllable": {"chi": 0.3, "tu": 0.1},
        },
        "collision_index": {
            "exact_names": ["美团"],
            "phonetic_keys": {"meituan": "美团"},
        },
    }
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )
    return str(path)


def _eng(stats_file=None, **kw):
    return BrandEngine(StyleParams(patterns_file=stats_file, **kw))


# ---------------------------------------------------------------------- 加载

def test_load_full_pipeline_format(tmp_path):
    stats = load_patterns(_full(tmp_path / "full.json"))
    assert isinstance(stats, PatternStats)
    assert stats.version == "test-full-1"
    assert stats.w_initial == {"h": 0.5, "c": 0.2}
    assert stats.exact_names == {"美团"}
    assert stats.phonetic_keys == {"meituan": "美团"}
    assert stats.max_initial == 0.5 and stats.max_syllable == 0.3


def test_load_slim_format(tmp_path):
    stats = load_patterns(
        _slim(
            tmp_path / "slim.json",
            w_initial={"c": 1.0},
            w_syllable={"chi": 0.8},
            exact_names=["赤兔"],
            phonetic_keys={"feiyue": "飞跃"},
        )
    )
    assert stats.w_initial == {"c": 1.0}
    assert stats.exact_names == {"赤兔"}
    assert stats.phonetic_keys == {"feiyue": "飞跃"}


def test_load_rejects_missing_and_bad_schema(tmp_path):
    with pytest.raises(ValueError):
        load_patterns(str(tmp_path / "nope.json"))
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schema": "whatever"}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_patterns(str(bad))


def test_engine_rejects_bad_patterns_file(tmp_path):
    with pytest.raises(ValueError):
        _eng(stats_file=str(tmp_path / "nope.json"), style="tech")


# ------------------------------------------------------------------ 语音键口径

def test_collision_key_is_per_char_pinyin():
    """语音键必须与上游索引同口径（逐字 lazy_pinyin），多音字取默认读音。"""
    assert collision_key("赤兔") == "chitu"
    assert collision_key("美团") == "meituan"
    # 银行：逐字口径 yin+xing，与词组级拼音 yinhang 不同——查索引必须用前者
    assert collision_key("银行") == "yinxing"
    assert build("银行").pinyin == "yinhang"
    assert collision_key("赤兔A") is None  # 非纯汉字不可靠


# ---------------------------------------------------------------------- 碰撞排雷

def test_exact_collision_dropped_with_audit_trail(tmp_path):
    """精确重名候选直接剔除，剔除记录可审计；衍生名不受影响。

    limit 取全池规模：观察剔除语义要看池级行为，top-N 截断会遮住低分衍生名。
    """
    stats = _slim(tmp_path / "s.json", exact_names=["赤兔"])
    eng = _eng(stats_file=stats, style="tech", limit=300)
    cands = eng.generate(["赤兔"])
    assert all(c.name != "赤兔" for c in cands)
    assert eng.last_dropped and eng.last_dropped[0]["name"] == "赤兔"
    assert eng.last_dropped[0]["type"] == "exact"
    assert eng.last_dropped[0]["existing"] == "赤兔"
    assert eng.last_dropped[0]["origin"]  # 构词来源留档
    # 衍生名（如 赤兔+风格后缀）不是精确重名，应保留在池内
    assert cands and any("赤兔" in c.name and c.name != "赤兔" for c in cands)


def test_phonetic_collision_strongly_downweighted_and_marked(tmp_path):
    """同音已有品牌：评分 ×0.4 强降权（与上游 consumer 语义一致），保留并标注。

    强降权后碰撞候选通常沉到 top-N 之外——这正是排雷的目的；用全池 limit
    验证「保留不剔除 + 标注 + 精确 ×0.4」。
    """
    stats = _slim(tmp_path / "s.json", phonetic_keys={"chitu": "驰途"})
    plain = _eng(style="tech", limit=300).generate(["赤兔"])
    eng = _eng(stats_file=stats, style="tech", limit=300)
    cands = eng.generate(["赤兔"])
    hit = [c for c in cands if c.name == "赤兔"]
    assert hit, "同音碰撞只降权不剔除，候选应保留在池内"
    base = next(c.score for c in plain if c.name == "赤兔")
    assert hit[0].score == round(base * 0.4, 2)
    assert hit[0].collision == {"type": "phonetic", "existing": "驰途"}
    # 其他无碰撞候选分值不变
    plain_by_name = {c.name: c.score for c in plain}
    for c in cands:
        if c.collision is None:
            assert c.score == plain_by_name[c.name]


# ------------------------------------------------------------------ 音节自然度

def test_phonetic_naturalness_normalized():
    stats = PatternStats(
        version="t",
        source="t",
        w_initial={"c": 1.0},
        w_syllable={"chi": 0.8, "tu": 0.4},
        max_initial=1.0,
        max_syllable=0.8,
    )
    np = build("赤兔")
    # ini = 1.0；syl = (0.8+0.4)/2 / 0.8 = 0.75 → 0.5*1.0 + 0.5*0.75
    assert stats.phonetic_naturalness(np) == 0.875
    # 音节完全缺席 → 0；零声母字取读音首字母做首字母分布查询
    assert stats.phonetic_naturalness(build("飞跃")) == 0.0


def test_naturalness_steer_ranking(tmp_path):
    """自然度权重足以主导 top-1：两组对立统计把同分种子分别推到第一。"""
    pro_feiyue = _slim(
        tmp_path / "a.json", w_initial={"f": 1.0}, w_syllable={"fei": 1.0, "yue": 1.0}
    )
    pro_chitu = _slim(
        tmp_path / "b.json", w_initial={"c": 1.0}, w_syllable={"chi": 1.0, "tu": 1.0}
    )
    seeds = ["赤兔", "飞跃"]
    assert _eng(stats_file=pro_feiyue, style="tech", limit=5).generate(seeds)[
        0
    ].name == "飞跃"
    assert _eng(stats_file=pro_chitu, style="tech", limit=5).generate(seeds)[
        0
    ].name == "赤兔"


def test_naturalness_score_delta_is_weighted_bonus(tmp_path):
    stats = _slim(
        tmp_path / "s.json", w_initial={"c": 1.0}, w_syllable={"chi": 1.0, "tu": 1.0}
    )
    plain = _eng(style="tech", limit=10).generate(["赤兔"])
    cands = _eng(stats_file=stats, style="tech", limit=10).generate(["赤兔"])
    base = next(c.score for c in plain if c.name == "赤兔")
    hit = next(c for c in cands if c.name == "赤兔")
    assert hit.phonetic == 1.0
    assert hit.score == round(base + 1.2, 2)


# ------------------------------------------------------------------ 契约兼容

def test_as_dict_v1_shape_unchanged_without_stats():
    """未启用统计：as_dict() 键集与 v1 契约完全一致（下游不受影响）。"""
    cands = _eng(style="tech", limit=3).generate(["赤兔"])
    for c in cands:
        assert set(c.as_dict()) == V1_KEYS
        assert c.collision is None and c.phonetic is None


def test_as_dict_additive_fields_with_stats(tmp_path):
    stats = _slim(tmp_path / "s.json", w_initial={"c": 1.0})
    cands = _eng(stats_file=stats, style="tech", limit=3).generate(["赤兔"])
    for c in cands:
        d = c.as_dict()
        assert set(d) == V1_KEYS | {"phonetic", "collision"}
        assert isinstance(d["phonetic"], float)


# ------------------------------------------------------------------ 内置真实数据

@pytest.mark.skipif(not BUNDLED.exists(), reason="内置瘦身数据未打包")
def test_bundled_stats_from_real_pipeline():
    stats = load_patterns(str(BUNDLED))
    assert len(stats.exact_names) > 5000
    assert len(stats.phonetic_keys) > 5000
    assert len(stats.w_syllable) >= 100
    assert stats.version  # provenance：来源版本号
    # 真实语料先验：h 开头（约 9.6%）应显著高于冷门首字母
    assert stats.w_initial.get("h", 0.0) > stats.w_initial.get("v", 0.0)
    # 赤兔 的音节自然度应在 (0, 1]：chi/tu 均为常见音节
    assert 0.0 < stats.phonetic_naturalness(build("赤兔")) <= 1.0


@pytest.mark.skipif(not BUNDLED.exists(), reason="内置瘦身数据未打包")
def test_bundled_exact_brand_is_dropped():
    """用索引里的真实品牌名做种子：精确重名必须被排雷剔除。"""
    stats = load_patterns(str(BUNDLED))
    real = next(
        (n for n in stats.exact_names if 2 <= len(n) <= 4 and all(
            "\u4e00" <= ch <= "\u9fff" for ch in n
        )),
        None,
    )
    assert real, "索引中应存在纯汉字品牌名"
    eng = _eng(stats_file=str(BUNDLED), style="tech", limit=8)
    cands = eng.generate([real])
    assert all(c.name != real for c in cands)
    assert any(d["name"] == real for d in eng.last_dropped)


# ------------------------------------------------------------------ CLI

def test_cli_patterns_file_smoke(tmp_path, capsys):
    from brandgen.cli import main

    stats = _slim(tmp_path / "s.json", exact_names=["赤兔"], w_initial={"c": 1.0})
    out_json = tmp_path / "out.json"
    rc = main(
        [
            "--seed", "赤兔",
            "--style", "tech",
            "--limit", "5",
            "--patterns-file", stats,
            "--json", str(out_json),
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "命名统计" in out and "精确重名剔除 1 个" in out
    assert "音节自然度" in out  # 统计模式下每个候选都带读音先验行
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["patterns"]["dropped_exact_collisions"][0]["name"] == "赤兔"
    assert set(payload["candidates"][0]) == V1_KEYS | {"phonetic", "collision"}
