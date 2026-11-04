"""语音键单一口径契约：pipeline 与 brandgen 必须共用同一实现。

背景：``naming-pipeline/pipeline/dedup.py::phonetic_key`` 用于**构建**碰撞索引，
``brandgen/stats.py::collision_key`` 用于**查询**碰撞索引。两者口径若分叉，
排雷会静默失效（查不中索引）。现在 dedup 直接转发引擎侧实现，本测试锁住：
(1) 转发关系（单一来源）；(2) 口径行为（逐字无声调拼音、≥2 纯汉字、忽略空格）。
"""
import importlib.util
from pathlib import Path

PIPELINE_DEDUP = (
    Path(__file__).resolve().parent.parent
    / "naming-pipeline" / "pipeline" / "dedup.py"
)


def _load_dedup():
    spec = importlib.util.spec_from_file_location("pipeline_dedup", PIPELINE_DEDUP)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_phonetic_key_is_single_source():
    """pipeline 的 phonetic_key 必须就是引擎侧的 collision_key（不是拷贝）。"""
    from brandgen.stats import collision_key

    dedup = _load_dedup()
    assert dedup.phonetic_key is collision_key


def test_collision_key_semantics():
    """锁定口径：逐字 lazy_pinyin、多音字取默认读音、≥2 纯汉字才可靠。"""
    from brandgen.stats import collision_key

    assert collision_key("宁德时代") == "ningdeshidai"
    assert collision_key("银行") == "yinxing"  # 逐字默认读音（不是词组读音 yinhang）
    assert collision_key("玉 兔") == "yutu"  # 空格分隔忽略空格
    assert collision_key("TCL科技") is None  # 含非汉字不可靠
    assert collision_key("赤兔A") is None
    assert collision_key("宁") is None  # 单字不可靠（≥2 才可靠）
    assert collision_key("") is None


def test_two_sides_agree_on_corpus():
    """两侧对一批真实风格名称逐条同口径（防御未来有人再加一份实现）。"""
    from brandgen.stats import collision_key

    dedup = _load_dedup()
    corpus = ["赤兔", "美团", "宁德时代", "玉兔", "昆仑", "重庆", "银行",
              "茶π", "字节跳动", "青梅", "龙宇"]
    for name in corpus:
        assert dedup.phonetic_key(name) == collision_key(name), name
