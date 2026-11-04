"""数据源回归：出站主机必须 HTTPS（明文上游会污染长期碰撞索引），
以及 App 榜单源的清洗/去重（唯一未被既有用例覆盖的抓取路径）。
"""
import inspect
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "naming-pipeline"))
from pipeline import http as http_mod  # noqa: E402
from pipeline import sources as srcs  # noqa: E402


@pytest.fixture
def log_lines():
    lines = []

    def log(msg):
        lines.append(msg)

    return log, lines


def _url_constants():
    for name, value in vars(srcs).items():
        if isinstance(value, str) and ("URL" in name or "API" in name) and "://" in value:
            yield name, value


def test_every_source_url_constant_is_https():
    found = dict(_url_constants())
    assert found, "sources 模块里应存在出站 URL 常量"
    assert [f"{k}={v}" for k, v in found.items() if not v.startswith("https://")] == []


def test_cninfo_fetch_uses_https(monkeypatch):
    seen = {}

    def fake_get_json(url, params=None, **kw):
        seen["url"] = url
        return {"stockList": [{"category": "主板", "zwjc": "青云科技", "code": "1"}]}

    monkeypatch.setattr(http_mod, "get_json", fake_get_json)
    recs = srcs.CninfoStockListSource(limit=1).fetch(lambda m: None)
    assert recs and seen["url"].startswith("https://www.cninfo.com.cn/")


def test_source_modules_contain_no_plaintext_http_urls():
    text = inspect.getsource(srcs)
    assert "http://" not in text


# ---------------------------------------------------------------- App 榜单源（HTTPS + 清洗）

def test_clean_app_name_strips_marketing_and_category():
    assert srcs.clean_app_name("高德地图") == "高德"
    assert srcs.clean_app_name("抖音商城-下单返积分、退货包运费") == "抖音"
    assert srcs.clean_app_name("小米WiFi") == "小米"
    assert srcs.clean_app_name("OPPO 互联") is None      # 拉丁前缀丢弃
    assert srcs.clean_app_name("铁路12306") is None      # 机构头丢弃
    assert srcs.clean_app_name("A") is None
    assert srcs.clean_app_name("App") is None            # 剥完为空
    assert srcs.clean_app_name("中国") is None            # 非品牌形态


def test_itunes_fetch_uses_https_and_dedupes(monkeypatch, log_lines):
    log, lines = log_lines
    seen_urls = []

    def fake_get_json(url, params=None, **kw):
        seen_urls.append(url)
        if "genre=1001" in url:
            raise RuntimeError("feed down")
        return {"feed": {"entry": [
            {"im:name": {"label": "高德地图"}},
            {"im:name": {"label": "高德地图"}},           # 同名去重
            {"im:name": {"label": "OPPO 互联"}},          # 清洗拒绝
        ]}}

    monkeypatch.setattr(http_mod, "get_json", fake_get_json)
    recs = srcs.ItunesAppSource(genres=[1001], interval=0).fetch(log)

    assert all(url.startswith("https://") for url in seen_urls)
    assert any("genre=1001" in url for url in seen_urls)   # 品类 feed 也走模板
    assert [r["name_clean"] for r in recs] == ["高德"]
    assert recs[0]["kind"] == "product_app"
    assert any("feed down" in m for m in lines)


def test_wiki_title_region_fallback_keeps_brand_form():
    # 区域剥离把字号剥到 3 字以下时回退到只剥组织后缀
    assert srcs.clean_wiki_title("北京啤酒股份有限公司") == "北京啤酒"


def test_seed_corpus_rejects_uncleanable_names(tmp_path, log_lines):
    log, _lines = log_lines
    seeds = tmp_path / "seeds.json"
    seeds.write_text(json.dumps([{"name": "AB"}, {"name": "赤兔"}], ensure_ascii=False),
                     encoding="utf-8")
    recs = srcs.SeedCorpusSource(str(seeds)).fetch(log)
    assert [r["name_clean"] for r in recs] == ["赤兔"]
