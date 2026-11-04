"""pipeline.sources 各数据源的行为测试（假 HTTP，不联网）。

覆盖：IPO 申报列表（分页/日期过滤/清洗拒绝）、F10 补全（成功/跳过/失败）、
巨潮存量列表（类别过滤/limit）、维基分类树（分页/黑名单/去重/子类/连败放弃）、
种子语料、default_seeds_path、opencc 缺失时的繁简降级。
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "naming-pipeline"))

from pipeline import http as http_mod  # noqa: E402
from pipeline import sources as srcs  # noqa: E402
from pipeline.dedup import record_id  # noqa: E402


@pytest.fixture
def log_lines():
    lines = []

    def log(msg):
        lines.append(msg)

    return log, lines


def _patch_get_json(monkeypatch, fake):
    monkeypatch.setattr(http_mod, "get_json", fake)


# ---------------------------------------------------------------- IPO 申报

def test_ipo_source_fetch_filters_and_cleans(monkeypatch, log_lines):
    log, lines = log_lines
    pages = {
        1: {"result": {"data": [
            {"SECURITY_NAME": "青云科技", "SECUCODE": "688316.SH",
             "APPLY_DATE": "2025-03-01 00:00:00", "LISTING_DATE": "2025-04-01 00:00:00",
             "MARKET_TYPE_NEW": "科创板", "INDUSTRY_NAME": "软件"},
            {"SECURITY_NAME": "老股科技", "SECUCODE": "000001.SZ",
             "APPLY_DATE": "2023-01-01 00:00:00"},          # 早于 min_date → 跳过
            {"SECURITY_NAME": "AB", "SECUCODE": "300001.SZ",
             "APPLY_DATE": "2025-03-02 00:00:00"},          # 清洗后为空 → 拒绝
            {"SECURITY_NAME": "赤兔网络", "APPLY_DATE": None},  # 无日期/无代码
        ]}},
        2: {"result": {"data": []}},                          # 空页 → 结束
    }

    def fake_get_json(url, params=None, **kw):
        assert url.startswith("https://datacenter-web.eastmoney.com")
        return pages[params["pageNumber"]]

    _patch_get_json(monkeypatch, fake_get_json)
    recs = srcs.EastmoneyIpoApplySource(pages=3, min_date="2024-01-01").fetch(log)

    assert [r["name_clean"] for r in recs] == ["青云科技", "赤兔网络"]
    assert recs[0]["record_id"] == record_id("eastmoney_ipo", "688316.SH")
    assert recs[0]["apply_date"] == "2025-03-01"
    assert recs[0]["listing_date"] == "2025-04-01"
    assert recs[0]["market"] == "科创板"
    assert recs[0]["industry"] == "软件"
    assert recs[1]["apply_date"] is None and recs[1]["listing_date"] is None
    # 无 SECUCODE 时 record_id 退回 SECURITY_NAME
    assert recs[1]["record_id"] == record_id("eastmoney_ipo", "赤兔网络")
    assert any("accepted=2 rejected=1" in m for m in lines)


def test_enrich_with_f10_success_skip_and_fail(monkeypatch, log_lines):
    log, lines = log_lines
    records = [
        {"secucode": "688316.SH"},   # 成功补全
        {"secucode": "NOCODE"},      # 无点号 → 跳过
        {"secucode": "000002.SZ"},   # 拉取失败
        {"secucode": "300001.SZ"},   # 无 ORG_NAME / 无域名 / 无行业横线
    ]
    responses = {
        "SH688316": {"jbzl": [{
            "ORG_NAME": "北京青云科技股份有限公司",
            "REG_ADDRESS": "北京市海淀区",
            "ORG_WEB": "www.qingcloud.com",
            "EM2016": "软件和信息技术服务业-软件开发",
        }]},
        "SZ300001": {"jbzl": [{"ORG_WEB": "nodot", "EM2016": "无横线行业"}]},
    }

    def fake_get_json(url, params=None, **kw):
        code = params["code"]
        if code == "SZ000002":
            raise RuntimeError("boom")
        return responses[code]

    _patch_get_json(monkeypatch, fake_get_json)
    stats = srcs.enrich_with_f10(records, max_count=10, log=log)

    assert stats == {"f10_enriched": 2, "f10_failed": 1}
    r = records[0]
    assert r["company_full_name"] == "北京青云科技股份有限公司"
    assert r["trade_name"] == "青云"
    assert r["region"] == "北京"
    assert r["domain"] == "www.qingcloud.com"
    assert r["industry"] == "软件和信息技术服务业"
    assert r["industry_raw"] == "软件和信息技术服务业-软件开发"
    assert r["f10"] is True
    r2 = records[3]
    assert r2["f10"] is True
    assert "company_full_name" not in r2       # 无 ORG_NAME 不写全称字段
    assert "domain" not in r2                  # 无点号字符串不当域名
    assert any("failed: boom" in m for m in lines)


def test_enrich_with_f10_respects_max_count(monkeypatch, log_lines):
    log, _lines = log_lines
    calls = []

    def fake_get_json(url, params=None, **kw):
        calls.append(params["code"])
        return {"jbzl": [{}]}

    _patch_get_json(monkeypatch, fake_get_json)
    stats = srcs.enrich_with_f10([{"secucode": "000001.SZ"}, {"secucode": "000002.SZ"}],
                                 max_count=1, log=log)
    assert calls == ["SZ000001"]
    assert stats["f10_enriched"] == 1


# ---------------------------------------------------------------- 巨潮存量

def test_cninfo_source_filters_categories_and_limits(monkeypatch, log_lines):
    log, lines = log_lines

    def fake_get_json(url, params=None, **kw):
        assert "cninfo.com.cn" in url
        return {"stockList": [
            {"category": "B股", "zwjc": "某某B股", "code": "1"},
            {"category": "主板", "zwjc": "青云科技", "code": "688316"},
            {"category": "创业板", "zwjc": "AB", "code": "2"},     # 清洗为空 → 拒绝
            {"category": "主板", "zwjc": "赤兔网络", "code": "3"},
            {"category": "主板", "zwjc": "小满文化", "code": "4"},  # 超 limit 不取
        ]}

    _patch_get_json(monkeypatch, fake_get_json)
    recs = srcs.CninfoStockListSource(limit=2).fetch(log)

    assert [r["name_clean"] for r in recs] == ["青云科技", "赤兔网络"]
    assert recs[0]["kind"] == "baseline" and recs[0]["source"] == "cninfo_all_a"
    assert any("accepted=2 rejected=1" in m for m in lines)


# ---------------------------------------------------------------- 维基分类

def test_wiki_source_pages_blacklist_dedup_subcats(monkeypatch, log_lines):
    log, lines = log_lines
    calls = []

    def fake_get_json(url, params=None, **kw):
        calls.append(dict(params))
        cat, cmtype = params["cmtitle"], params["cmtype"]
        if cmtype == "page":
            if cat == "Category:中国品牌" and "cmcontinue" not in params:
                return {"query": {"categorymembers": [
                    {"title": "泸州老窖股份有限公司"},
                    {"title": "青島啤酒"},                 # 繁体品牌名 → t2s 归一
                    {"title": "列表之最"},                # 黑名单
                    {"title": "AB"},                     # 清洗后为空
                ]}, "continue": {"cmcontinue": "cont-1"}}
            if cat == "Category:中国品牌":
                return {"query": {"categorymembers": [{"title": "青岛啤酒"}]}}  # 重复
            if cat in ("Category:中国品牌", "Category:中国商标"):
                return {"query": {"categorymembers": [{"title": "安达"}]}}
            return {"query": {"categorymembers": []}}   # 第三个父类（老字号）没有页
        # subcat：两个父类都返回同一子类（覆盖 visited 去重）
        return {"query": {"categorymembers": [{"title": "Category:中国白酒"}]}}

    _patch_get_json(monkeypatch, fake_get_json)
    recs = srcs.WikiCategorySource(depth=1).fetch(log)

    assert [r["name_clean"] for r in recs] == ["泸州老窖", "青岛啤酒", "安达"]
    assert all(r["kind"] == "famous_brand" for r in recs)
    # 分页续查带 cmcontinue
    assert any("cmcontinue" in c for c in calls)
    # 三个父类都排过子类（重复子类被 visited 跳过）
    assert sum(1 for c in calls if c["cmtype"] == "subcat") == 3
    assert any("accepted=3" in m for m in lines)


def test_wiki_max_pages_stops_traversal(monkeypatch, log_lines):
    log, _lines = log_lines
    calls = []

    def fake_get_json(url, params=None, **kw):
        calls.append(params["cmtitle"])
        return {"query": {"categorymembers": [
            {"title": "安达"}, {"title": "小满"}, {"title": "赤兔"},
        ]}}

    _patch_get_json(monkeypatch, fake_get_json)
    monkeypatch.setattr(srcs.WikiCategorySource, "MAX_PAGES", 2)
    recs = srcs.WikiCategorySource(depth=1).fetch(log)
    assert [r["name_clean"] for r in recs] == ["安达", "小满", "赤兔"]
    assert calls == ["Category:中国品牌"]   # 满额后不再访问后续分类


def test_wiki_subcat_failure_is_ignored(monkeypatch, log_lines):
    log, _lines = log_lines

    def fake_get_json(url, params=None, **kw):
        if params["cmtype"] == "subcat":
            raise RuntimeError("subcat down")
        return {"query": {"categorymembers": [{"title": "安达"}]}}

    _patch_get_json(monkeypatch, fake_get_json)
    recs = srcs.WikiCategorySource(depth=1).fetch(log)
    assert [r["name_clean"] for r in recs] == ["安达"]


def test_wiki_consecutive_failures_abort_source(monkeypatch, log_lines):
    log, lines = log_lines

    def fake_get_json(url, params=None, **kw):
        raise RuntimeError("429 雪崩")

    _patch_get_json(monkeypatch, fake_get_json)
    monkeypatch.setattr(srcs.WikiCategorySource, "BASE_CATS",
                        ["中国品牌", "中国商标", "中国老字号"])
    with pytest.raises(RuntimeError, match="连续 3 个分类失败"):
        srcs.WikiCategorySource(depth=0).fetch(log)
    assert sum(1 for m in lines if "failed (" in m) == 3


# ---------------------------------------------------------------- 种子语料

def test_seed_corpus_source_cleans_and_skips(tmp_path, log_lines):
    log, lines = log_lines
    seeds = tmp_path / "seeds.json"
    seeds.write_text(json.dumps([
        {"name": "字节跳动", "domain": "bytedance.com", "industry": "科技"},
        {"name": "阿里巴巴集团"},        # 剥离组织尾词 → 阿里巴巴
        {"name": "AB"},                  # 不足 2 个汉字 → 跳过
        {"name": " 赤兔 "},
    ], ensure_ascii=False), encoding="utf-8")

    recs = srcs.SeedCorpusSource(str(seeds)).fetch(log)

    assert [r["name_clean"] for r in recs] == ["字节跳动", "阿里巴巴", "赤兔"]
    assert recs[0]["domain"] == "bytedance.com"
    assert recs[0]["industry"] == "科技"
    assert recs[0]["kind"] == "famous_brand" and recs[0]["source_priority"] == 5
    assert any("accepted=3" in m for m in lines)


def test_default_seeds_path_points_at_repo_seeds():
    path = srcs.default_seeds_path()
    assert path.endswith(str(Path("seeds") / "brand_domains.json"))
    assert Path(path).is_file()


# ---------------------------------------------------------------- 繁简降级

def test_clean_wiki_title_falls_back_without_opencc(monkeypatch):
    monkeypatch.setitem(sys.modules, "opencc", None)   # import opencc 必失败
    assert srcs.clean_wiki_title("青島啤酒") == "青島啤酒"   # 原样返回
