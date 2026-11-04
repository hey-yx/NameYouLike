"""域名 seam 测试：形式生成（离线）+ 可用性状态语义。"""
import pytest

from brandgen.domains import (
    STATUS_LABEL,
    DomainSuggestion,
    check_domain,
    generate_forms,
)
from brandgen.patterns import build


def test_forms_cover_all_pattern_families():
    forms = generate_forms(build("赤兔"), tlds=["com", "cn", "io"], max_forms=12)
    domains = [f.domain for f in forms]
    assert "chitu.com" in domains       # 全拼形式
    assert "chi-tu.com" in domains      # 破折号/短横线形式
    assert "cht.com" in domains         # 声母简拼形式
    assert "cht.io" in domains


def test_forms_unique_and_wellformed():
    forms = generate_forms(build("赤兔飞跃"), tlds=["com", "cn"], max_forms=20)
    seen = set()
    for f in forms:
        assert f.domain not in seen
        seen.add(f.domain)
        sld, tld = f.domain.rsplit(".", 1)
        assert sld and tld.isalpha()
        assert len(sld) <= 63
        assert sld == sld.lower()
        assert not sld.startswith("-") and not sld.endswith("-")
        assert f.pattern in ("pinyin", "kebab", "initials")


def test_single_letter_initials_form_excluded():
    """单字名的简拼只有 1 个字母（如 跃 → y），不作域名形式（过短易撞车）。"""
    forms = generate_forms(build("跃"), tlds=["com"], max_forms=10)
    assert all(f.pattern != "initials" for f in forms)


def test_offline_forms_status_unknown():
    forms = generate_forms(build("赤兔"), tlds=["com"], max_forms=5)
    assert all(f.status == "unknown" for f in forms)
    assert all(f.method == "" for f in forms)


def test_status_labels_are_honest():
    """三类状态都必须有中文说明，且『疑似可注册』必须提示复核。"""
    assert set(STATUS_LABEL) == {"registered", "likely_available", "unknown"}
    assert "复核" in STATUS_LABEL["likely_available"]


def _mk(domain="chitu.com"):
    return DomainSuggestion(domain=domain, pattern="pinyin", tld="com")


def test_check_domain_rdap_404_means_likely_available(monkeypatch):
    monkeypatch.setattr("brandgen.domains._rdap_status", lambda d, t=4.0: 404)
    s = check_domain(_mk())
    assert s.status == "likely_available"
    assert s.method == "rdap"


def test_check_domain_rdap_200_means_registered(monkeypatch):
    monkeypatch.setattr("brandgen.domains._rdap_status", lambda d, t=4.0: 200)
    s = check_domain(_mk())
    assert s.status == "registered"
    assert s.method == "rdap"


def test_check_domain_falls_back_to_dns(monkeypatch):
    monkeypatch.setattr("brandgen.domains._rdap_status", lambda d, t=4.0: None)  # RDAP 不可达
    monkeypatch.setattr("brandgen.domains._dns_resolves", lambda d: False)       # NXDOMAIN
    s = check_domain(_mk())
    assert s.status == "likely_available"
    assert s.method == "dns"


def test_check_domain_dns_resolves_means_registered(monkeypatch):
    monkeypatch.setattr("brandgen.domains._rdap_status", lambda d, t=4.0: None)
    monkeypatch.setattr("brandgen.domains._dns_resolves", lambda d: True)
    s = check_domain(_mk())
    assert s.status == "registered"
    assert s.method == "dns"
