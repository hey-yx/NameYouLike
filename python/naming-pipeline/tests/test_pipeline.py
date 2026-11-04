"""管道测试：清洗 / 去重 / 拼音风格 / 统计 / 增量 / 消费者。"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.clean import clean_full_name, clean_short_name  # noqa: E402
from pipeline.consumer import validate_output  # noqa: E402
from pipeline.dedup import DedupIndex, phonetic_key, record_id  # noqa: E402
from pipeline.features import classify_pinyin_style, domain_root, name_features  # noqa: E402
from pipeline.stats import build_patterns  # noqa: E402


# ---------------------------------------------------------------- 清洗

class TestClean:
    def test_full_name_decomposition(self):
        # 区域提示来自注册地址（能覆盖长尾城市）
        name, meta = clean_full_name("芜湖莫森泰克汽车科技股份有限公司", "安徽省芜湖市")
        assert name == "莫森泰克"
        assert meta["region"] == "芜湖"

    def test_full_name_known_region_list(self):
        name, _ = clean_full_name("广州通则康威科技股份有限公司")
        assert name == "通则康威"

    def test_full_name_region_ambiguity(self):
        # 宁德时代全称中的「宁德」是行政区划（法定字号为「时代」）；
        # 有注册地址提示时应剥离为法定字号。
        name, meta = clean_full_name("宁德时代新能源科技股份有限公司", "福建省宁德市")
        assert name == "时代"
        assert meta["region"] == "宁德"
        # 品牌形态由简称保留（管道主字段 name_clean 取自简称）
        assert clean_short_name("宁德时代")[0] == "宁德时代"

    def test_full_name_parenthetical(self):
        name, _ = clean_full_name("北京某某（集团）股份有限公司")
        assert name == "某某"

    def test_moutai(self):
        name, _ = clean_full_name("贵州茅台酒股份有限公司", "贵州省仁怀市")
        assert name == "茅台"

    def test_too_short_returns_none(self):
        name, _ = clean_full_name("公司")
        assert name is None

    def test_short_name_market_marks(self):
        assert clean_short_name("N通则")[0] == "通则"
        assert clean_short_name("*ST慧辰")[0] == "慧辰"
        assert clean_short_name("万科A")[0] == "万科"
        assert clean_short_name("退市海润")[0] == "海润"

    def test_short_name_keeps_two_char(self):
        # 两字简称不应被市场标记规则破坏
        assert clean_short_name("南宁")[0] == "南宁"

    def test_short_name_org_form(self):
        assert clean_short_name("安达股份")[0] == "安达"
        assert clean_short_name("蚂蚁集团")[0] == "蚂蚁"
        assert clean_short_name("洛轴股份")[0] == "洛轴"

    def test_short_name_rejects_non_cjk(self):
        assert clean_short_name("TCL")[0] is None
        assert clean_short_name("  ")[0] is None


# ---------------------------------------------------------------- 去重

class TestDedup:
    def test_exact_dedup_cross_source(self):
        idx = DedupIndex()
        a = {"record_id": record_id("s1", "淘宝"), "source": "s1", "name_clean": "淘宝"}
        b = {"record_id": record_id("s2", "淘宝"), "source": "s2", "name_clean": "淘宝"}
        idx.add(a)
        kept = idx.add(b)
        assert kept is a

    def test_richer_record_wins(self):
        idx = DedupIndex()
        a = {"record_id": record_id("s1", "淘宝"), "source": "s1", "name_clean": "淘宝"}
        b = {"record_id": record_id("s2", "淘宝"), "source": "s2", "name_clean": "淘宝",
             "domain": "taobao.com", "industry": "电商"}
        idx.add(a)
        kept = idx.add(b)
        assert kept is b

    def test_phonetic_dedup(self):
        idx = DedupIndex()
        a = {"record_id": record_id("s1", "淘宝"), "source": "s1", "name_clean": "淘宝",
             "domain": "taobao.com"}
        b = {"record_id": record_id("s2", "桃宝"), "source": "s2", "name_clean": "桃宝"}
        idx.add(a)
        kept = idx.add(b)
        assert kept is a  # 富有者保留
        assert idx.collision_check("逃宝")["type"] == "phonetic"

    def test_collision_check(self):
        idx = DedupIndex()
        idx.add({"record_id": "x", "source": "s", "name_clean": "京东"})
        assert idx.collision_check("京东")["type"] == "exact"
        assert idx.collision_check("汾酒") is None

    def test_phonetic_key(self):
        assert phonetic_key("宁德时代") == "ningdeshidai"
        assert phonetic_key("TCL科技") is None  # 含非 CJK


# ---------------------------------------------------------------- 拼音风格

class TestPinyinStyle:
    def test_domain_root(self):
        assert domain_root("www.moutaichina.com") == "moutaichina"
        assert domain_root("weixin.qq.com") == "weixin"
        assert domain_root("163.com") == "163"
        assert domain_root("sina.com.cn") == "sina"
        assert domain_root("https://www.zte.com.cn/about") == "zte"
        assert domain_root("ele.me") == "ele"
        assert domain_root("") is None

    def test_classify(self):
        assert classify_pinyin_style("淘宝", "taobao.com")["style"] == "full"
        assert classify_pinyin_style("京东", "jd.com")["style"] == "abbr"
        assert classify_pinyin_style("小米", "mi.com")["style"] == "partial"
        assert classify_pinyin_style("网易", "163.com")["style"] == "numeric"
        assert classify_pinyin_style("携程", "ctrip.com")["style"] == "creative"
        assert classify_pinyin_style("小鹏", "xpeng.com")["style"] == "hybrid"
        assert classify_pinyin_style("极兔", "jtexpress.com")["style"] == "abbr_compound"
        assert classify_pinyin_style("三只松鼠", "3songshu.com")["style"] == "partial"

    def test_hyphen_detection(self):
        res = classify_pinyin_style("顺丰", "sf-express.com")
        assert res["style"] == "abbr_compound"
        assert res["has_hyphen"] is True

    def test_name_features(self):
        f = name_features("赤兔")
        assert f["length"] == 2
        assert f["initials"] == "ct"
        assert f["syllables"] == ["chi", "tu"]


# ---------------------------------------------------------------- 统计 + 消费者（微型语料）

@pytest.fixture()
def patterns_file(tmp_path):
    recs = [
        {"record_id": "1", "source": "t", "kind": "new_enterprise", "name_clean": "云图",
         "industry": "软件", "domain": "yuntu.com"},
        {"record_id": "2", "source": "t", "kind": "new_enterprise", "name_clean": "云海",
         "industry": "软件"},
        {"record_id": "3", "source": "t", "kind": "new_enterprise", "name_clean": "星澜科技",
         "industry": "软件"},
        {"record_id": "4", "source": "t", "kind": "new_enterprise", "name_clean": "星河",
         "industry": "食品"},
        {"record_id": "5", "source": "t", "kind": "new_enterprise", "name_clean": "麦浪",
         "industry": "食品"},
        {"record_id": "6", "source": "t", "kind": "new_enterprise", "name_clean": "麦芽堂",
         "industry": "食品"},
        {"record_id": "7", "source": "t", "kind": "new_enterprise", "name_clean": "光启",
         "industry": "食品"},
        {"record_id": "8", "source": "t", "kind": "new_enterprise", "name_clean": "光合社",
         "industry": "食品"},
        {"record_id": "9", "source": "t", "kind": "famous_brand", "name_clean": "淘宝",
         "domain": "taobao.com"},
        {"record_id": "10", "source": "t", "kind": "famous_brand", "name_clean": "京东",
         "domain": "jd.com"},
        {"record_id": "11", "source": "t", "kind": "famous_brand", "name_clean": "饿了么",
         "domain": "ele.me"},
        {"record_id": "12", "source": "t", "kind": "baseline", "name_clean": "万科"},
        {"record_id": "13", "source": "t", "kind": "baseline", "name_clean": "平安银行"},
    ]
    patterns = build_patterns(recs, {"version": "test-001", "generated_at": "now",
                                     "run_id": "run_test", "provenance": {}, "quality": {}})
    # 行业样本 < 8 -> 不应产出行业关联（防碎样本）
    assert patterns["industry_char_affinity"] == {}
    assert patterns["length_dist"]
    assert abs(sum(patterns["length_dist"].values()) - 1.0) < 0.01
    assert patterns["collision_index"]["exact_names"]
    assert "万科" in patterns["collision_index"]["exact_names"]  # 基线进入碰撞索引
    assert patterns["pinyin_style_dist"]["full"] > 0  # 淘宝
    path = tmp_path / "patterns.json"
    path.write_text(json.dumps(patterns, ensure_ascii=False), encoding="utf-8")
    return str(path)


class TestConsumer:
    def test_validate_pass(self, patterns_file):
        v = validate_output(patterns_file)
        assert v["ok"], v["errors"]
        assert v["stats_records"] > 0

    def test_validate_bad_file(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"schema": "naming-patterns/v1"}), encoding="utf-8")
        v = validate_output(str(bad))
        assert not v["ok"]
        assert any("缺少顶层字段" in e for e in v["errors"])

    def test_engine_parse_via_brandgen(self, patterns_file):
        # 解析统一走 brandgen.stats.load_patterns（与引擎同一份实现），
        # 管道侧不再维护第二份解析器；sys.path 复用模式同 pipeline/dedup.py。
        import sys as _sys
        from pathlib import Path as _Path

        python_root = str(_Path(__file__).resolve().parents[2])
        if python_root not in _sys.path:
            _sys.path.insert(0, python_root)
        from brandgen.stats import load_patterns  # noqa: E402  # pyright: ignore[reportMissingImports]

        stats = load_patterns(patterns_file)
        assert stats.exact_names, "完整版 schema 应加载出碰撞索引"
        assert "淘宝" in stats.exact_names
        assert stats.collision("淘宝") == {"type": "exact", "existing": "淘宝"}
        assert stats.collision("云舟") is None


# ---------------------------------------------------------------- 维基标题清洗（供测试与 rebuild 复用）

class TestWikiTitleClean:
    def test_full_company_name(self):
        from pipeline.sources import clean_wiki_title
        assert clean_wiki_title("泸州老窖股份有限公司") == "泸州老窖"
        assert clean_wiki_title("北京百度网讯科技有限公司") == "百度网讯"

    def test_brand_title_kept(self):
        from pipeline.sources import clean_wiki_title
        assert clean_wiki_title("青岛啤酒") == "青岛啤酒"   # 品牌形态不动
        assert clean_wiki_title("老干妈") == "老干妈"
        assert clean_wiki_title("哔哩哔哩（公司）") == "哔哩哔哩"

    def test_traditional_title(self):
        from pipeline.sources import clean_wiki_title
        assert clean_wiki_title("青島啤酒股份有限公司") in ("青岛啤酒", "啤酒")
        assert clean_wiki_title("王守義十三香") == "王守义十三香"

    def test_invalid(self):
        from pipeline.sources import clean_wiki_title
        assert clean_wiki_title("A") is None


# ---------------------------------------------------------------- 增量机制（离线管道两连跑）

class TestIncremental:
    def test_two_offline_runs(self, tmp_path):
        from pipeline.run import run_pipeline
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        d1 = run_pipeline(data_dir=str(tmp_path / "data"), output_dir=str(tmp_path / "out"),
                          seeds_path=os.path.join(base, "seeds", "brand_domains.json"),
                          offline=True)
        assert d1["new_records"] > 0
        total1 = d1["corpus_total"]
        v1 = d1["version"]
        d2 = run_pipeline(data_dir=str(tmp_path / "data"), output_dir=str(tmp_path / "out"),
                          seeds_path=os.path.join(base, "seeds", "brand_domains.json"),
                          offline=True)
        assert d2["new_records"] == 0          # 种子语料未变 -> 无新增
        assert d2["corpus_total"] == total1    # 语料不膨胀
        assert d2["version"] != v1             # 版本推进
        # 两次输出统计一致（无新数据时统计稳定）
        p1 = json.loads((tmp_path / "out" / "history" / (v1 + ".json")).read_text(encoding="utf-8"))
        p2 = json.loads((tmp_path / "out" / "naming_patterns.v1.json").read_text(encoding="utf-8"))
        assert p1["char_scores"] == p2["char_scores"]
        assert p1["length_dist"] == p2["length_dist"]

    def test_new_data_arrives(self, tmp_path, monkeypatch):
        from pipeline import run as run_mod
        extra = [{"record_id": "zz1", "source": "future", "source_priority": 1,
                  "kind": "new_enterprise", "name_clean": "量子跃迁"}]
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        seeds = os.path.join(base, "seeds", "brand_domains.json")

        orig_fetch = run_mod.srcs.SeedCorpusSource.fetch

        def fetch_with_extra(self, log):
            recs = orig_fetch(self, log)
            return recs + extra

        monkeypatch.setattr(run_mod.srcs.SeedCorpusSource, "fetch", fetch_with_extra)
        d1 = run_mod.run_pipeline(data_dir=str(tmp_path / "data"),
                                 output_dir=str(tmp_path / "out"), offline=True,
                                 seeds_path=seeds)
        assert d1["corpus_total"] == d1["new_records"]
        extra.append({"record_id": "zz2", "source": "future", "source_priority": 1,
                      "kind": "new_enterprise", "name_clean": "比特视界"})
        d2 = run_mod.run_pipeline(data_dir=str(tmp_path / "data"),
                                  output_dir=str(tmp_path / "out"), offline=True,
                                  seeds_path=seeds)
        assert d2["new_records"] == 1
        assert d2["corpus_total"] == d1["corpus_total"] + 1

    def test_lock_prevents_concurrent(self, tmp_path):
        from pipeline.run import run_pipeline
        from pipeline.store import LockError, PipelineStore
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        store = PipelineStore(str(tmp_path / "data"))
        store.acquire_lock()
        with pytest.raises(LockError):
            run_pipeline(data_dir=str(tmp_path / "data"),
                         output_dir=str(tmp_path / "out"), offline=True,
                         seeds_path=os.path.join(base, "seeds", "brand_domains.json"))
        store.release_lock()


# ---------------------------------------------------------------- 历史快照保留策略

class TestHistoryRetention:
    def test_prune_keeps_newest(self, tmp_path):
        from pipeline.run import _prune_history
        for i in range(1, 41):
            (tmp_path / f"2026.10.22-{i:03d}.json").write_text("{}", encoding="utf-8")
        removed = _prune_history(str(tmp_path), keep=30)
        assert removed == 10
        left = sorted(p.name for p in tmp_path.glob("*.json"))
        assert len(left) == 30
        assert left[0] == "2026.10.22-011.json"      # 最旧的 10 份被清掉
        assert left[-1] == "2026.10.22-040.json"

    def test_prune_noop_under_limit(self, tmp_path):
        from pipeline.run import _prune_history
        (tmp_path / "2026.10.22-001.json").write_text("{}", encoding="utf-8")
        assert _prune_history(str(tmp_path), keep=30) == 0
        assert len(list(tmp_path.glob("*.json"))) == 1


# ---------------------------------------------------------------- 生成端词库

class TestLexicon:
    def test_morpheme_bank_excludes_category_chars(self):
        from pipeline.lexicon import build_lexicon
        names = ["青云", "青云", "青云", "云海", "星河", "星河", "麦浪", "麦浪", "麦浪"]
        out = build_lexicon(names, min_char=2, min_bigram=2)
        bank = out["morpheme_bank"]
        assert "云" in bank and "青" in bank
        # 品类/机构字不进词根表
        assert not (set(bank) & set("科技电汽车店行厂"))

    def test_imagery_classification(self):
        from pipeline.lexicon import classify_imagery
        assert "动物" in classify_imagery("白鹿")
        assert "自然" in classify_imagery("云海")
        assert "植物" in classify_imagery("兰亭")
        assert classify_imagery("钶锐锶") == []
