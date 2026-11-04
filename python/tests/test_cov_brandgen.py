"""brandgen 包的行为测试（CLI / 统计消费 / 域名核验 / 引擎参数校验）。

覆盖：
- cli.main：统计文件 + 碰撞标注输出（json/md）、在线核验格式化、ValueError 入口、
  `python -m brandgen` 与 `brandgen.cli` 两个 __main__ 入口
- stats：extract_slim 瘦身提取、空音节自然度兜底
- domains：RDAP/DNS 核验各分支、无效 SLD 跳过、并发核验
- engine：参数校验三条红线、域名可用性加成
"""
import json
import runpy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brandgen import BrandEngine, StyleParams  # noqa: E402
from brandgen import cli as brandgen_cli  # noqa: E402
from brandgen import domains as dom  # noqa: E402
from brandgen import engine as eng_mod  # noqa: E402
from brandgen import stats as stats_mod  # noqa: E402
from brandgen.patterns import NamePatterns  # noqa: E402

PYTHON_DIR = Path(__file__).resolve().parent.parent
SLIM_SCHEMA = "brandgen/pattern-stats-slim/v1"


def _name_patterns(name, **over):
    kw = dict(name=name, pinyin=name, pinyin_toned=name, syllables=(name,),
              initials=name[:1], letters=name[:1], dash=name, kebab=name, camel=name)
    kw.update(over)
    return NamePatterns(**kw)


def _slim_patterns_file(tmp_path, phonetic_keys, exact_names=()):
    path = tmp_path / "patterns.json"
    path.write_text(json.dumps({
        "schema": SLIM_SCHEMA, "version": "2026.test",
        "w_initial": {"c": 1.0, "b": 0.5}, "w_syllable": {"chi": 1.0, "tu": 0.8},
        "exact_names": list(exact_names), "phonetic_keys": phonetic_keys,
    }, ensure_ascii=False), encoding="utf-8")
    return path


# ---------------------------------------------------------------- CLI

def _probe_names(limit=200):
    """与 CLI 同参数预生成候选池（生成与统计无关，只有打分/剔除受影响）。"""
    return [c.name for c in BrandEngine(
        StyleParams(style="tech", limit=limit)).generate(["赤兔"])]


def test_cli_with_patterns_outputs_json_and_md(tmp_path, capsys):
    names = _probe_names()
    keyed = {stats_mod.collision_key(n): "既有品牌" for n in names}
    pfile = _slim_patterns_file(tmp_path, keyed, exact_names=names[:1])
    out_json, out_md = tmp_path / "out.json", tmp_path / "out.md"

    rc = brandgen_cli.main([
        "--seed", "赤兔", "--style", "tech", "--limit", "6",
        "--patterns-file", str(pfile), "--json", str(out_json), "--md", str(out_md),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "命名统计" in out and "同音" in out
    assert "JSON 已写入" in out and "Markdown 已写入" in out

    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["seeds"] == ["赤兔"] and payload["style"] == "tech"
    assert payload["patterns"]["version"] == "2026.test"
    assert payload["patterns"]["dropped_exact_collisions"]  # 精确重名剔除进审计
    for c in payload["candidates"]:
        assert c["collision"]["type"] == "phonetic"

    md = out_md.read_text(encoding="utf-8")
    assert "# 品牌名生成结果" in md
    assert "音节自然度 | 碰撞 |" in md            # stats 表头
    assert "⚠ 同音" in md                        # 碰撞标注
    assert "已剔除与现有品牌精确重名的候选" in md  # 剔除审计


def test_cli_live_check_marks_and_hint(tmp_path, monkeypatch, capsys):
    def _fake_check_many(targets, timeout=4.0):
        plan = [("registered", "rdap"), ("likely_available", "dns"), ("unknown", "")]
        for i, t in enumerate(targets):
            t.status, t.method = plan[i % 3]
        return targets

    monkeypatch.setattr(eng_mod, "check_many", _fake_check_many)
    rc = brandgen_cli.main([
        "--seed", "青云", "--style", "neutral", "--limit", "3",
        "--check-domains",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "✗" in out and "✓" in out and "?" in out
    assert "提示: 「疑似可注册」仍需注册商 whois 复核后方可注册。" in out


def test_cli_invalid_patterns_file_returns_2(tmp_path, capsys):
    rc = brandgen_cli.main([
        "--seed", "赤兔", "--patterns-file", str(tmp_path / "missing.json"),
    ])
    assert rc == 2
    assert "错误:" in capsys.readouterr().err


def test_cli_module_entrypoints(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["brandgen", "--seed", "白泽", "--limit", "3"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("brandgen.cli", run_name="__main__")
    assert exc.value.code == 0

    monkeypatch.setattr(sys, "argv", ["brandgen", "--seed", "白泽", "--limit", "3"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("brandgen", run_name="__main__")
    assert exc.value.code == 0


# ---------------------------------------------------------------- stats

def test_extract_slim_from_full_schema(tmp_path):
    src = tmp_path / "full.json"
    src.write_text(json.dumps({
        "schema": "naming-patterns/v1", "version": "2026.01.01-001",
        "recommendation_weights": {"w_initial": {"h": 1.0}, "w_syllable": {"ji": 0.5}},
        "collision_index": {"exact_names": ["淘宝"], "phonetic_keys": {"taobao": "淘宝"}},
    }), encoding="utf-8")
    dst = tmp_path / "slim.json"
    summary = stats_mod.extract_slim(str(src), str(dst))

    slim = json.loads(dst.read_text(encoding="utf-8"))
    assert slim["schema"] == SLIM_SCHEMA
    assert slim["version"] == "2026.01.01-001"
    assert slim["exact_names"] == ["淘宝"]
    assert slim["phonetic_keys"] == {"taobao": "淘宝"}
    assert slim["provenance"]["fields"] == [
        "w_initial", "w_syllable", "exact_names", "phonetic_keys"]
    assert summary == {"version": "2026.01.01-001", "w_initial": 1,
                       "w_syllable": 1, "exact_names": 1, "phonetic_keys": 1}


def test_phonetic_naturalness_empty_syllables_is_zero():
    st = stats_mod.PatternStats(version="v", source="s")
    assert st.phonetic_naturalness(_name_patterns("", syllables=())) == 0.0


# ---------------------------------------------------------------- domains

class _Resp:
    status = 200
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def test_rdap_status_branches(monkeypatch):
    monkeypatch.setattr(dom.urllib.request, "urlopen", lambda req, timeout: _Resp())
    assert dom._rdap_status("a.com") == 200

    def _404(req, timeout):
        raise dom.urllib.error.HTTPError("u", 404, "nope", {}, None)
    monkeypatch.setattr(dom.urllib.request, "urlopen", _404)
    assert dom._rdap_status("b.com") == 404

    def _net_fail(req, timeout):
        raise dom.urllib.error.URLError("offline")
    monkeypatch.setattr(dom.urllib.request, "urlopen", _net_fail)
    assert dom._rdap_status("c.com") is None


def test_dns_resolves_branches(monkeypatch):
    monkeypatch.setattr(dom.socket, "getaddrinfo", lambda *a, **k: [1])
    assert dom._dns_resolves("a.com") is True

    def _nx(*a, **k):
        raise dom.socket.gaierror()
    monkeypatch.setattr(dom.socket, "getaddrinfo", _nx)
    assert dom._dns_resolves("b.com") is False


def test_check_domain_all_status_branches(monkeypatch):
    monkeypatch.setattr(dom, "_rdap_status", lambda d, timeout: 404)
    got = dom.check_domain(dom.DomainSuggestion(domain="a.com", pattern="p", tld="com"))
    assert (got.status, got.method) == ("likely_available", "rdap")

    monkeypatch.setattr(dom, "_rdap_status", lambda d, timeout: 200)
    got = dom.check_domain(dom.DomainSuggestion(domain="b.com", pattern="p", tld="com"))
    assert (got.status, got.method) == ("registered", "rdap")

    monkeypatch.setattr(dom, "_rdap_status", lambda d, timeout: None)
    monkeypatch.setattr(dom, "_dns_resolves", lambda d: True)
    got = dom.check_domain(dom.DomainSuggestion(domain="c.com", pattern="p", tld="com"))
    assert (got.status, got.method) == ("registered", "dns")

    monkeypatch.setattr(dom, "_dns_resolves", lambda d: False)
    got = dom.check_domain(dom.DomainSuggestion(domain="d.com", pattern="p", tld="com"))
    assert (got.status, got.method) == ("likely_available", "dns")


def test_check_many_concurrent(monkeypatch):
    monkeypatch.setattr(dom, "_rdap_status", lambda d, timeout: 200)
    got = dom.check_many([
        dom.DomainSuggestion(domain=f"{i}.com", pattern="p", tld="com") for i in range(4)])
    assert [g.status for g in got] == ["registered"] * 4


def test_generate_forms_skips_invalid_slds():
    p = _name_patterns("X", pinyin="BAD", kebab="Bad-X", initials="",
                       syllables=(), letters="")
    forms = dom.generate_forms(p, tlds=["com"], max_forms=8)
    assert forms == []  # 全部 SLD 非法 → 全部 continue


# ---------------------------------------------------------------- engine 参数校验

def test_engine_rejects_bad_style():
    with pytest.raises(ValueError, match="未知风格"):
        BrandEngine(StyleParams(style="nope"))


def test_engine_rejects_bad_lengths():
    with pytest.raises(ValueError, match="lengths 必须"):
        BrandEngine(StyleParams(lengths=(1,)))


def test_engine_rejects_non_patternstats():
    with pytest.raises(TypeError, match="PatternStats"):
        BrandEngine(stats="not-stats")


def test_availability_bonus_branches():
    def sug(status, tld):
        return dom.DomainSuggestion(domain=f"x.{tld}", pattern="p", tld=tld, status=status)
    assert eng_mod._availability_bonus([]) == 0.0                    # 全 unknown
    assert eng_mod._availability_bonus([sug("unknown", "com")]) == 0.0
    assert eng_mod._availability_bonus([sug("likely_available", "cn")]) == 1.0
    assert eng_mod._availability_bonus([sug("registered", "com")]) == 0.0
    assert eng_mod._availability_bonus([sug("likely_available", "com")]) == 3.0
