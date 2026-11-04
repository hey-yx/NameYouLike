"""pipeline.run 端到端运行入口的行为测试（tmp 目录 + 假数据源，不联网）。

覆盖：reclean_corpus 重清洗、offline 全链路（含 __main__ 守卫）、rebuild-stats
模式、在线模式的源失败/F10 失败处理、_render_run_md 渲染、main() 参数解析。
"""
import json
import runpy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "naming-pipeline"))

from pipeline import run as run_mod  # noqa: E402


def _log_collector():
    lines = []

    def log(msg):
        lines.append(msg)

    return log, lines


# ---------------------------------------------------------------- 重清洗

def test_reclean_corpus_recleans_all_source_kinds():
    log, lines = _log_collector()
    corpus = [
        {"record_id": "1", "source": "wiki_zh_brand", "kind": "famous_brand",
         "name_raw": "青島啤酒", "name_clean": "旧值"},
        {"record_id": "2", "source": "eastmoney_ipo", "kind": "new_enterprise",
         "name_raw": "N通则", "name_clean": "旧值"},
        {"record_id": "3", "source": "cninfo_all_a", "kind": "baseline",
         "name_raw": "赤兔网络", "name_clean": "旧值"},
        {"record_id": "4", "source": "curated_seed", "kind": "famous_brand",
         "name_raw": "阿里巴巴集团", "name_clean": "旧值", "domain": "alibaba.com"},
        {"record_id": "5", "source": "other_x", "kind": "famous_brand",
         "name_raw": "ZZ", "name_clean": "原样保留"},      # 非四类源 → 取现 name_clean
        {"record_id": "6", "source": "wiki_zh_brand", "kind": "famous_brand",
         "name_raw": "AB", "name_clean": "旧值"},          # 重清洗为空 → 丢弃
        {"record_id": "7", "source": "curated_seed", "kind": "famous_brand",
         "name_raw": "阿里巴巴集团", "name_clean": "旧值"},  # 与 4 同名 → 去重压缩
    ]
    kept = run_mod.reclean_corpus(corpus, log=log)
    assert [r["name_clean"] for r in kept] == \
        ["青岛啤酒", "通则", "赤兔网络", "阿里巴巴", "原样保留"]
    assert kept[3]["domain"] == "alibaba.com"     # 补全字段原样保留
    assert any("重清洗 7 -> 6 条有效" in m for m in lines)


# ---------------------------------------------------------------- offline 全链路

def _seeds_file(tmp_path, items):
    p = tmp_path / "seeds.json"
    p.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    return str(p)


def test_run_pipeline_offline_end_to_end(tmp_path):
    seeds = _seeds_file(tmp_path, [
        {"name": "字节跳动", "domain": "bytedance.com"},
        {"name": "字节跳动"},            # 同 record_id → 运行内去重
        {"name": "阿里巴巴集团"},
        {"name": "小满茶饮"},
    ])
    # 预置历史语料：与种子「小满茶饮」精确同名（更富有）→ 新记录被去重
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "corpus.jsonl").write_text(json.dumps({
        "record_id": "pre1", "source": "curated_seed", "source_priority": 5,
        "kind": "famous_brand", "name_raw": "小满茶饮旧", "name_clean": "小满茶饮",
        "domain": "xiaoman.com", "industry": "餐饮",
    }, ensure_ascii=False) + "\n", encoding="utf-8")

    record = run_mod.run_pipeline(
        data_dir=str(data_dir), output_dir=str(tmp_path / "out"),
        seeds_path=seeds, offline=True)

    assert record["validation"]["ok"] is True
    assert record["offline"] is True
    assert record["new_records"] == 2          # 字节跳动 + 阿里巴巴
    assert record["duplicates"] == 2           # 1 个运行内重复 + 1 个历史重复
    assert record["corpus_total"] == 3
    out = tmp_path / "out" / "naming_patterns.v1.json"
    assert out.is_file()
    assert json.loads(out.read_text(encoding="utf-8"))["schema"] == "naming-patterns/v1"
    # 版本化快照 + 状态推进 + 运行记录
    assert any((tmp_path / "out" / "history").glob("*.json"))
    state = json.loads((data_dir / "state.json").read_text(encoding="utf-8"))
    assert state["version_seq"] == 1 and state["runs"]
    run_dirs = list((tmp_path / "runs").glob("run_*"))
    assert len(run_dirs) == 1
    assert (run_dirs[0] / "record.json").is_file()
    assert (run_dirs[0] / "record.md").is_file()


def test_run_pipeline_rebuild_stats_recleans_corpus(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "corpus.jsonl").write_text(
        json.dumps({"record_id": "1", "source": "curated_seed", "kind": "famous_brand",
                    "name_raw": "阿里巴巴集团", "name_clean": "旧值"}, ensure_ascii=False)
        + "\n" + "这不是JSON\n" + "\n", encoding="utf-8")

    record = run_mod.run_pipeline(
        data_dir=str(data_dir), output_dir=str(tmp_path / "out"),
        rebuild_stats=True)

    assert record["rebuild_stats"] is True
    assert record["new_records"] == 0
    assert record["corpus_total"] == 1
    # 语料被按当前清洗逻辑覆写
    lines = (data_dir / "corpus.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0])["name_clean"] == "阿里巴巴"


# ---------------------------------------------------------------- 在线模式（假源）

class FakeIpo:
    def fetch(self, log):
        log("[fake] ipo")
        return [{"record_id": "ipo1", "source": "eastmoney_ipo", "source_priority": 3,
                 "kind": "new_enterprise", "name_raw": "青云科技", "name_clean": "青云科技",
                 "secucode": "688316.SH", "industry": "软件"}]


class FakeWiki:
    def fetch(self, log):
        return [{"record_id": "wiki1", "source": "wiki_zh_brand", "source_priority": 2,
                 "kind": "famous_brand", "name_raw": "青岛啤酒", "name_clean": "青岛啤酒"}]


class FakeCninfoBroken:
    def fetch(self, log):
        raise RuntimeError("cninfo down")


def test_run_pipeline_online_source_and_f10_failures(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod.srcs, "EastmoneyIpoApplySource", FakeIpo)
    monkeypatch.setattr(run_mod.srcs, "CninfoStockListSource", FakeCninfoBroken)
    monkeypatch.setattr(run_mod.srcs, "WikiCategorySource", FakeWiki)

    def bad_f10(records, max_count, log):
        raise RuntimeError("f10 down")

    monkeypatch.setattr(run_mod.srcs, "enrich_with_f10", bad_f10)

    record = run_mod.run_pipeline(
        data_dir=str(tmp_path / "data"), output_dir=str(tmp_path / "out"),
        seeds_path=_seeds_file(tmp_path, [{"name": "字节跳动"}]),
        offline=False, max_f10=5)

    assert record["validation"]["ok"] is True
    assert record["failures"] == ["cninfo_all_a: cninfo down", "eastmoney_f10: f10 down"]
    assert record["sources"]["cninfo_all_a"] == {"error": "cninfo down"}
    assert record["sources"]["eastmoney_ipo"]["count"] == 1
    assert record["f10"] == {"f10_enriched": 0, "f10_failed": 0}
    # 原始抓取快照落盘
    assert list((tmp_path / "data" / "raw").glob("eastmoney_ipo_*.jsonl"))


def test_run_pipeline_online_skips_disabled_sources(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod.srcs, "EastmoneyIpoApplySource", FakeIpo)
    monkeypatch.setattr(run_mod.srcs, "enrich_with_f10",
                        lambda records, max_count, log: {"f10_enriched": len(records),
                                                         "f10_failed": 0})

    record = run_mod.run_pipeline(
        data_dir=str(tmp_path / "data"), output_dir=str(tmp_path / "out"),
        seeds_path=_seeds_file(tmp_path, [{"name": "字节跳动"}]),
        offline=False, use_wiki=False, use_cninfo=False, max_f10=5)

    assert record["f10"] == {"f10_enriched": 1, "f10_failed": 0}
    assert "wiki_zh_brand" not in record["sources"]
    assert "cninfo_all_a" not in record["sources"]


# ---------------------------------------------------------------- 渲染与入口

def _record_for_md():
    return {
        "run_id": "run_x", "version": "v1", "started_utc": "t", "duration_seconds": 1,
        "offline": False, "rebuild_stats": False,
        "sources": {"seed": {"count": 1, "seconds": 0.1}, "wiki_zh_brand": {"skipped": True}},
        "f10": {"f10_enriched": 2, "f10_failed": 0},
        "failures": ["cninfo_all_a: boom"],
        "corpus_total": 1, "new_records": 1, "duplicates": 0,
        "corpus_stats": {"stats_records": 1, "baseline_records": 0,
                         "by_source_counts": {"curated_seed": 1},
                         "with_domain": 1, "with_industry": 1},
        "length_dist": {"2": 1.0}, "pinyin_style_dist": {"full": 1.0},
        "cleaning_examples": [{"full": "北京青云科技有限公司", "trade": "青云",
                               "region": "北京", "industry": "软件",
                               "domain": "qingcloud.com", "ops": []}],
        "validation": {"ok": True, "errors": []},
    }


def _patterns_for_md():
    return {
        "char_scores": {"青": {"count": 1}},
        "pinyin_style_examples": {"full": [{"name": "青云", "domain": "qingcloud.com",
                                            "root": "qingcloud"}]},
        "collision_index": {"exact_names": ["青云"], "phonetic_keys": {"qingyun": "青云"}},
    }


def test_render_run_md_full_sections():
    md = run_mod._render_run_md(_record_for_md(), _patterns_for_md())
    assert "| wiki_zh_brand | 跳过 | - |" in md            # 跳过源
    assert "eastmoney_f10（补全: 全称/区域/行业/域名）" in md
    assert "## 失败源" in md and "- cninfo_all_a: boom" in md
    assert "### 清洗链真实示例（F10 公司全称 → 字号）" in md
    assert "北京青云科技有限公司" in md and "**青云**" in md
    assert "碰撞索引" in md and "精确名称 1 个" in md
    assert "输出 schema 校验: **PASS**" in md
    assert "| seed | 1 | 0.1s |" in md


def test_main_parses_argv_and_maps_exit_code(monkeypatch, tmp_path):
    captured = {}

    def fake_run_pipeline(**kwargs):
        captured.update(kwargs)
        return {"validation": {"ok": True}}

    monkeypatch.setattr(run_mod, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(sys, "argv", ["run", "--offline", "--max-f10", "5",
                                      "--no-wiki", "--no-cninfo", "--no-ipo",
                                      "--rebuild-stats",
                                      "--data-dir", str(tmp_path / "d"),
                                      "--output-dir", str(tmp_path / "o")])
    assert run_mod.main() == 0
    assert captured == {
        "data_dir": str(tmp_path / "d"), "output_dir": str(tmp_path / "o"),
        "offline": True, "max_f10": 5, "use_wiki": False, "use_cninfo": False,
        "use_ipo": False, "use_apps": True, "rebuild_stats": True,
    }

    monkeypatch.setattr(run_mod, "run_pipeline",
                        lambda **kw: {"validation": {"ok": False, "errors": ["x"]}})
    assert run_mod.main() == 1


def test_module_main_guard_runs_offline_pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", [
        "run", "--offline",
        "--data-dir", str(tmp_path / "data"),
        "--output-dir", str(tmp_path / "out"),
        "--max-f10", "0",
    ])
    with pytest.raises(SystemExit) as ei:
        runpy.run_module("pipeline.run", run_name="__main__")
    assert ei.value.code == 0
    assert (tmp_path / "out" / "naming_patterns.v1.json").is_file()
