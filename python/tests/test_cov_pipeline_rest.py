"""naming-pipeline 其余模块的缺口行为测试：consumer / dedup / clean / features /
stats / store（均不联网）。
"""
import json
import os
import runpy
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "naming-pipeline"))

from pipeline import consumer, dedup, stats as pstats, store as pstore  # noqa: E402
from pipeline.clean import clean_full_name, clean_short_name, _parse_region_hints  # noqa: E402
from pipeline.features import classify_pinyin_style, domain_root  # noqa: E402

NAMING_PIPELINE_DIR = Path(__file__).resolve().parent.parent / "naming-pipeline"


# ---------------------------------------------------------------- consumer

def test_validate_output_unreadable_file(tmp_path):
    v = consumer.validate_output(str(tmp_path / "missing.json"))
    assert v["ok"] is False
    assert v["errors"][0].startswith("无法读取/解析")


def test_validate_output_top_level_not_object(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("[1, 2]", encoding="utf-8")
    v = consumer.validate_output(str(p))
    assert v == {"ok": False, "errors": ["顶层不是对象"]}


def _valid_patterns():
    return pstats.build_patterns(
        [{"record_id": "1", "source": "curated_seed", "kind": "famous_brand",
          "name_clean": "青云", "domain": "qingcloud.com"}],
        {"version": "v", "generated_at": "t", "run_id": "r"})


def test_validate_output_missing_keys_and_bad_schema(tmp_path):
    p = tmp_path / "b.json"
    p.write_text(json.dumps({"schema": "wrong/v0"}), encoding="utf-8")
    v = consumer.validate_output(str(p))
    assert not v["ok"]
    assert any("缺少顶层字段" in e for e in v["errors"])
    assert any("schema 版本不符: wrong/v0" in e for e in v["errors"])


def test_validate_output_bad_dist_and_weights(tmp_path):
    data = _valid_patterns()
    data["schema"] = "naming-patterns/v1"
    data["length_dist"] = {"2": 0.9, "3": 0.9}                  # 概率和 != 1
    data["recommendation_weights"]["w_char"] = {"青": 2.0}      # 越界权重
    p = tmp_path / "c.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    v = consumer.validate_output(str(p))
    assert not v["ok"]
    assert any("概率和" in e for e in v["errors"])
    assert any("越界权重: ['青']" in e for e in v["errors"])


def test_validate_output_accepts_build_patterns_output(tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps(_valid_patterns(), ensure_ascii=False), encoding="utf-8")
    v = consumer.validate_output(str(p))
    assert v["ok"] is True and v["stats_records"] == 1


def test_consumer_main_and_module_guard(tmp_path, monkeypatch, capsys):
    p = tmp_path / "e.json"
    p.write_text(json.dumps(_valid_patterns(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["consumer", str(p), "--validate-only"])
    assert consumer.main() == 0
    assert "PASS" in capsys.readouterr().out

    monkeypatch.setattr(sys, "argv", ["consumer", str(tmp_path / "nope.json")])
    with pytest.raises(SystemExit) as ei:
        runpy.run_module("pipeline.consumer", run_name="__main__")
    assert ei.value.code == 1


# ---------------------------------------------------------------- dedup

def test_dedup_richer_record_wins_phonetic_collision():
    idx = dedup.DedupIndex()
    weak = {"record_id": "r1", "source": "s", "name_clean": "桃宝", "source_priority": 1,
            "kind": "new_enterprise"}
    rich = {"record_id": "r2", "source": "s", "name_clean": "淘宝", "source_priority": 5,
            "kind": "famous_brand", "domain": "taobao.com", "industry": "电商"}
    assert idx.add(weak) is weak
    assert idx.add(rich) is rich            # 同音不同字 → 富有者替换
    assert idx.by_phonetic[dedup.phonetic_key("淘宝")] is rich
    assert weak.get("phonetic_dup_of") is None   # 被替换者不打标（新记录占位）


def test_dedup_phonetic_dup_marked_then_reinserted_on_same_rid():
    idx = dedup.DedupIndex()
    base = {"record_id": "b1", "source": "s", "name_clean": "淘宝", "source_priority": 5,
            "kind": "famous_brand", "domain": "taobao.com"}
    dup = {"record_id": "c1", "source": "s", "name_clean": "涛宝", "source_priority": 1,
           "kind": "new_enterprise"}
    assert idx.add(base) is base
    assert idx.add(dup) is base              # 弱者让位
    assert dup["phonetic_dup_of"] == "淘宝"   # 弱者打同音标记

    # 同 record_id 再来一次：精确表里没有「涛宝」→ 补插入并返回自己
    dup2 = {"record_id": "c1", "source": "s", "name_clean": "涛宝", "source_priority": 1,
            "kind": "new_enterprise"}
    assert idx.add(dup2) is dup2
    assert idx.by_exact[dedup.norm_key("涛宝")] is dup2


def test_dedup_lookup_returns_richer_occupier_for_same_rid():
    idx = dedup.DedupIndex()
    a1 = {"record_id": "a1", "source": "s", "name_clean": "甲乙", "source_priority": 1,
          "kind": "new_enterprise"}
    b1 = {"record_id": "b1", "source": "s", "name_clean": "甲乙", "source_priority": 5,
          "kind": "famous_brand", "domain": "jy.com"}
    assert idx.add(a1) is a1
    assert idx.add(b1) is b1                # 同名更富有 → 替换占位
    again = {"record_id": "a1", "source": "s", "name_clean": "甲乙", "source_priority": 1,
             "kind": "new_enterprise"}
    assert idx.add(again) is b1             # 老 rid 回访 → 返回占位者
    assert idx.collision_check("甲乙") == {"type": "exact", "existing": "甲乙"}
    assert idx.collision_check("孑孓") is None


def test_dedup_module_adds_python_root_to_sys_path():
    """独立子进程里 python/ 包根不在 sys.path：dedup 应自举加入（复用 brandgen）。"""
    code = (
        f"import sys; sys.path.insert(0, {str(NAMING_PIPELINE_DIR)!r})\n"
        "import pipeline.dedup as d\n"
        "assert any(p.lower().endswith('nameyoulike/python') or p.lower().endswith('nameyoulike/python/')"
        " for p in sys.path), sys.path\n"
        "print('ok')\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "ok"


def test_dedup_import_inserts_python_root_when_missing(monkeypatch):
    """python/ 包根不在 sys.path 时，import pipeline.dedup 自身把它加回来。"""
    import importlib

    python_root = str(Path(__file__).resolve().parent.parent)
    monkeypatch.delitem(sys.modules, "pipeline.dedup")
    monkeypatch.setattr(sys, "path", [p for p in sys.path if p != python_root])

    mod = importlib.import_module("pipeline.dedup")
    assert python_root in sys.path           # 自举加回
    assert mod.phonetic_key("淘宝")           # 复用 brandgen 的语音键可用


# ---------------------------------------------------------------- clean

def test_clean_short_name_empty_returns_none():
    name, meta = clean_short_name("")
    assert name is None and meta["raw"] == ""


def test_clean_full_name_empty_returns_none():
    name, meta = clean_full_name("")
    assert name is None and meta["region"] is None


def test_region_hints_from_municipality_address():
    # 直辖市注册地址（无「省/自治区」前缀）也能给出区域提示
    assert _parse_region_hints("上海市浦东新区") == ["上海"]
    name, meta = clean_full_name("上海青云科技有限公司", "上海市浦东新区")
    assert name == "青云"
    assert meta["region"] == "上海"


# ---------------------------------------------------------------- features

def test_domain_root_rejects_dotless_and_empty_labels():
    assert domain_root("nodot") is None
    assert domain_root(".com") is None
    assert domain_root("https://a.io/path") == "a"


def test_classify_pinyin_style_no_root_and_short_name():
    out = classify_pinyin_style("青云", "nodot")
    assert out["root"] is None and out["style"] is None      # 无域名根 → 无风格
    out2 = classify_pinyin_style("龙", "long.com")
    assert out2["style"] == "creative"                        # 单字名走创意类


# ---------------------------------------------------------------- stats

def test_weight_from_count_zero_max_returns_zero():
    assert pstats._weight_from_count(3, 0) == 0.0


def test_build_patterns_handles_edge_records():
    recs = [
        # 无汉字名 → 用字循环跳过
        {"record_id": "1", "source": "curated_seed", "kind": "famous_brand",
         "name_clean": "ab"},
        # 单字名 → 拼音统计跳过
        {"record_id": "2", "source": "curated_seed", "kind": "famous_brand",
         "name_clean": "龙"},
        # 无有效域名根 → 拼音风格跳过
        {"record_id": "3", "source": "curated_seed", "kind": "famous_brand",
         "name_clean": "青云", "domain": "nodot"},
    ] + [
        # 3 条同款名 → 「青云」二元组 count>=3 进入 lift/权重统计
        {"record_id": f"g{i}", "source": "curated_seed", "kind": "famous_brand",
         "name_clean": "青云", "domain": "qingyunkeji.com", "industry": "软件"}
        for i in range(3)
    ]
    out = pstats.build_patterns(recs, {"version": "v1", "generated_at": "t",
                                       "run_id": "r1"})
    assert out["char_pair_scores"]["青云"]["count"] == 4
    assert "weight" in out["char_pair_scores"]["青云"]
    assert out["pinyin_style_dist"] == {"full": 1.0} or out["pinyin_style_dist"] == {"partial": 1.0}
    assert out["collision_index"]["phonetic_keys"]


# ---------------------------------------------------------------- store

def test_store_lock_is_kernel_level(tmp_path):
    s = pstore.PipelineStore(str(tmp_path))
    # 陈旧的锁文件不再具有阻止力：flock 只认活着的文件描述符。
    Path(s.lock_path).write_text("old", encoding="utf-8")
    old = time.time() - 2000
    os.utime(s.lock_path, (old, old))

    s.acquire_lock()
    assert Path(s.lock_path).is_file()
    with pytest.raises(pstore.LockError):
        pstore.PipelineStore(str(tmp_path)).acquire_lock()   # 同进程第二个 fd 也互斥

    s.release_lock()
    s.release_lock()                               # 已释放再释放 → 静默容忍
    again = pstore.PipelineStore(str(tmp_path))
    again.acquire_lock()                           # 释放后可重新获取
    again.release_lock()


def test_store_load_corpus_skips_bad_lines(tmp_path):
    s = pstore.PipelineStore(str(tmp_path))
    Path(s.corpus_path).write_text(
        json.dumps({"record_id": "1"}) + "\n\n这不是JSON\n", encoding="utf-8")
    assert s.load_corpus() == [{"record_id": "1"}]
    before = Path(s.corpus_path).read_text(encoding="utf-8")
    s.append_records([])                           # 空列表不落盘
    assert Path(s.corpus_path).read_text(encoding="utf-8") == before


def test_store_save_raw_snapshot_empty_returns_none(tmp_path):
    s = pstore.PipelineStore(str(tmp_path))
    assert s.save_raw_snapshot("src", []) is None
    path = s.save_raw_snapshot("src", [{"record_id": "1"}])
    assert path and Path(path).is_file()
