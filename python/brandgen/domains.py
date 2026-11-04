"""域名形式生成与可用性校验。

形式来源三种模式：拼音全拼 / 全拼短横线 / 声母简拼（≥2 字母）。
域名大小写不敏感，驼峰形式与全拼在域名上等价，故不单独生成。

可用性语义（务必如实标注，不做超出证据的断言）：
- registered       : RDAP 200（注册局有记录）或 DNS 有解析 → 已注册/使用中
- likely_available : RDAP 404（注册局无记录）或 DNS NXDOMAIN → 疑似可注册，注册前必须复核 whois
- unknown          : 网络失败 / RDAP 与 DNS 均不可用 → 未能验证
"""
from __future__ import annotations

import socket
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone

from .patterns import NamePatterns

DEFAULT_TLDS = ("com", "cn", "com.cn", "io", "ai", "tech", "app", "net")

# 各风格的 TLD 优先级（同一池内重排）
STYLE_TLD_ORDER: dict[str, tuple[str, ...]] = {
    "tech": ("com", "ai", "io", "tech", "cn", "app", "com.cn", "net"),
    "classic": ("com", "cn", "com.cn", "net", "io", "app", "tech", "ai"),
    "international": ("com", "io", "ai", "tech", "app", "cn", "com.cn", "net"),
    "playful": ("com", "cn", "app", "io", "ai", "tech", "com.cn", "net"),
    "neutral": DEFAULT_TLDS,
}

STATUS_LABEL: dict[str, str] = {
    "registered": "已注册/占用",
    "likely_available": "疑似可注册（注册前请复核 whois）",
    "unknown": "未能验证",
}


@dataclass
class DomainSuggestion:
    """一条域名形式建议。status/method/note 由可用性核验填充。"""

    domain: str
    pattern: str  # pinyin / kebab / initials
    tld: str
    status: str = "unknown"
    method: str = ""  # rdap / dns / ''
    note: str = ""
    checked_at: str = ""


def _ordered_tlds(tlds: list[str] | tuple[str, ...] | None, style: str) -> tuple[str, ...]:
    pool = tuple(tlds) if tlds else DEFAULT_TLDS
    order = STYLE_TLD_ORDER.get(style, DEFAULT_TLDS)
    ordered = [t for t in order if t in pool]
    ordered += [t for t in pool if t not in ordered]
    return tuple(ordered)


def _valid_sld(sld: str) -> bool:
    return (
        bool(sld)
        and len(sld) <= 63
        and sld == sld.lower()
        and not sld.startswith("-")
        and not sld.endswith("-")
        and all(ch.isascii() and (ch.isalnum() or ch == "-") for ch in sld)
    )


def generate_forms(
    p: NamePatterns,
    tlds: list[str] | tuple[str, ...] | None = None,
    style: str = "neutral",
    max_forms: int = 8,
) -> list[DomainSuggestion]:
    """为一个品牌名生成域名形式（不做网络请求，离线可用）。"""
    slds: list[tuple[str, str]] = [(p.pinyin, "pinyin"), (p.kebab, "kebab")]
    if len(p.initials) >= 2:  # 单字母 SLD 极易撞车，不生成
        slds.append((p.initials, "initials"))

    forms: list[DomainSuggestion] = []
    seen: set[str] = set()
    for tld in _ordered_tlds(tlds, style):
        for sld, pat in slds:
            if len(forms) >= max_forms:
                return forms
            if not _valid_sld(sld):
                continue
            domain = f"{sld}.{tld}"
            if domain in seen:
                continue
            seen.add(domain)
            forms.append(DomainSuggestion(domain=domain, pattern=pat, tld=tld))
    return forms


def _rdap_status(domain: str, timeout: float = 4.0) -> int | None:
    """通过 rdap.org（IANA bootstrap 重定向）查询注册局 RDAP。

    返回 HTTP 状态码：200=已注册，404=注册局无记录；网络失败返回 None。
    """
    req = urllib.request.Request(
        f"https://rdap.org/domain/{domain}",
        headers={
            "Accept": "application/rdap+json",
            "User-Agent": "brandgen/0.1 (brand-name-engine)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def _dns_resolves(domain: str) -> bool:
    """弱信号兜底：有 A/AAAA 记录说明在用；NXDOMAIN 不代表一定可注册。"""
    try:
        socket.getaddrinfo(domain, None)
        return True
    except socket.gaierror:
        return False


def check_domain(d: DomainSuggestion, timeout: float = 4.0) -> DomainSuggestion:
    """就地核验一条域名建议（RDAP 优先，DNS 兜底），返回同一对象。"""
    d.checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    code = _rdap_status(d.domain, timeout)
    if code == 404:
        d.status, d.method, d.note = "likely_available", "rdap", "RDAP 404：注册局无记录"
    elif code is not None and 200 <= code < 300:
        d.status, d.method, d.note = "registered", "rdap", f"RDAP {code}：注册局有记录"
    else:
        if _dns_resolves(d.domain):
            d.status, d.method, d.note = "registered", "dns", "DNS 有解析记录"
        else:
            d.status, d.method, d.note = (
                "likely_available",
                "dns",
                "DNS NXDOMAIN（弱信号，务必 whois 复核）",
            )
    return d


def check_many(
    suggestions: list[DomainSuggestion], timeout: float = 4.0, workers: int = 8
) -> list[DomainSuggestion]:
    """并发核验（对外仍为同步调用）。"""
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(lambda s: check_domain(s, timeout), suggestions))
