#!/usr/bin/env python3
"""域名可用性查询：三段式（DoH NS 预筛 → 权威 RDAP → WHOIS 兜底）。

为什么分段：
  1) DoH NS 预筛：DNS 不过问注册局，没有限流。查到 NS 记录说明域名已被委派，
     直接判已注册，不用再打扰注册局。查到 NXDOMAIN 只说明「该名字在区里没有委派」，
     不能直接说可注册（已注册但未委派也长这样），必须回权威 RDAP 确认。
  2) 权威 RDAP：每个后缀只有一个权威源，用错源会拿到假的「可注册」。
     Google Registry（.dev/.app）限流很硬（实测并发 6 稳、12 开始 429、24 全 429），
     所以 .dev/.app 单独串行 400ms，其他后缀并发 2。429 按 0.8s/2s/4s 退避重试。
  3) WHOIS 兜底：只对有权威 WHOIS 且 RDAP 拿不到结论的后缀使用；
     .dev/.app 的 WHOIS 对任何域名都回空串，已实测，不做回退。

用法：
  python3 scripts/domain-check-fast.py example.com example.dev
  python3 scripts/domain-check-fast.py --variants link-parse,direct-fetch
  python3 scripts/domain-check-fast.py --json out.json example.com
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

# 权威 RDAP 基址：每个后缀只认自己的注册局。
RDAP_BASE = {
    "com": "https://rdap.verisign.com/com/v1/",
    "net": "https://rdap.verisign.com/net/v1/",
    "io": "https://rdap.identitydigital.services/rdap/",
    "ai": "https://rdap.identitydigital.services/rdap/",
    "sh": "https://rdap.identitydigital.services/rdap/",
    "xyz": "https://rdap.centralnic.com/xyz/",
    "dev": "https://pubapi.registry.google/rdap/",
    "app": "https://pubapi.registry.google/rdap/",
}

# WHOIS 兜底：host + 未注册文本特征。只在有权威 WHOIS 的后缀上用。
WHOIS = {
    "com": ("whois.verisign-grs.com", "no match for"),
    "net": ("whois.verisign-grs.com", "no match for"),
    "io": ("whois.nic.io", "domain not found"),
    "ai": ("whois.nic.ai", "domain not found"),
    "me": ("whois.nic.me", "domain not found"),
    "sh": ("whois.nic.sh", "domain not found"),
    "so": ("whois.nic.so", "no object found"),
}

# Google Registry 后缀单独串行，因为限流最硬。
SLOW_TLDS = {"dev", "app"}
SLOW_GAP_S = 0.4
FAST_CONCURRENCY = 2
DOH_URLS = (
    "https://dns.google/resolve?name={name}&type=NS",
    "https://cloudflare-dns.com/dns-query?name={name}&type=NS",
)

STATUS_LABEL = {
    "available": "可注册",
    "registered": "已注册",
    "reserved": "保留",
    "unknown": "未确认",
    "error": "查询出错",
}


def http_get(url: str, accept: str, timeout: float = 12.0) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={"accept": accept, "user-agent": "nameyoulike-domain-check/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except Exception as exc:  # 网络层异常统一当失败处理
        return 0, str(exc)


def doh_ns(domain: str) -> tuple[str | None, str]:
    """返回 ('ns' | 'nxdomain' | None, 来源说明)。"""
    for template in DOH_URLS:
        code, body = http_get(template.format(name=domain), "application/dns-json")
        if code != 200:
            continue
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            continue
        status = data.get("Status")
        if status == 0:
            return "ns", "doh-ns"
        if status == 3:
            return "nxdomain", "doh-nxdomain"
        return None, f"doh-status-{status}"
    return None, "doh-failed"


def rdap_check(domain: str, tld: str) -> dict:
    base = RDAP_BASE.get(tld)
    if not base:
        return {"status": "unknown", "source": "none", "detail": "该后缀无权威 RDAP 配置"}
    url = f"{base}domain/{domain}"
    detail = ""
    for attempt in range(3):
        code, body = http_get(url, "application/rdap+json")
        if code == 404:
            return {"status": "available", "source": "rdap"}
        if code == 200:
            lowered = body.lower()
            if "premium" in lowered or "reserved" in lowered:
                kind = "reserved" if "reserved" in lowered else "premium"
                return {"status": kind, "source": "rdap"}
            return {"status": "registered", "source": "rdap"}
        if code == 429:
            detail = "RDAP 限流"
        elif code == 0:
            detail = "RDAP 请求失败"
        else:
            detail = f"RDAP 返回 {code}"
        if attempt < 2:
            time.sleep(0.8 * (2**attempt))
    # RDAP 没结论，再试权威 WHOIS。
    if tld in WHOIS:
        host, needle = WHOIS[tld]
        try:
            with socket_create_connection(host, timeout=10) as sock:
                sock.sendall(f"{domain}\r\n".encode())
                chunks = []
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
            text = b"".join(chunks).decode("utf-8", "replace")
            if not text.strip():
                return {"status": "unknown", "source": "whois", "detail": "WHOIS 响应为空"}
            if needle in text.lower():
                return {"status": "available", "source": "whois"}
            return {"status": "registered", "source": "whois"}
        except Exception as exc:
            return {"status": "unknown", "source": "whois", "detail": f"WHOIS 失败：{exc}"}
    return {"status": "unknown", "source": "rdap", "detail": detail or "RDAP 无结论"}


def socket_create_connection(host: str, timeout: float):
    import socket as socket_module

    return socket_module.create_connection((host, 43), timeout=timeout)


def check_one(domain: str) -> dict:
    tld = domain.rsplit(".", 1)[-1]
    ns_state, ns_source = doh_ns(domain)
    if ns_state == "ns":
        return {"domain": domain, "tld": tld, "status": "registered", "source": ns_source}
    result = rdap_check(domain, tld)
    return {"domain": domain, "tld": tld, "status": result["status"], "source": result["source"], "detail": result.get("detail")}


def main() -> int:
    parser = argparse.ArgumentParser(description="三段式域名可用性查询")
    parser.add_argument("domains", nargs="*")
    parser.add_argument("--variants", default="", help="逗号分隔的裸名，自动配 com/net/io/ai/dev/app")
    parser.add_argument("--json", dest="json_out", default="")
    parser.add_argument("--no-doh", action="store_true", help="跳过 DNS 预筛，全部直查 RDAP")
    args = parser.parse_args()

    domains: list[str] = []
    for raw in args.domains:
        domains.extend(part.strip() for part in raw.split(",") if part.strip())
    if args.variants:
        for name in args.variants.split(","):
            name = name.strip()
            if not name:
                continue
            for tld in ("com", "net", "io", "ai", "dev", "app"):
                domains.append(f"{name}.{tld}")
    domains = list(dict.fromkeys(domains))
    if not domains:
        parser.print_help()
        return 0

    results: list[dict] = []
    slow = [d for d in domains if d.rsplit(".", 1)[-1] in SLOW_TLDS]
    fast = [d for d in domains if d not in slow]

    if args.no_doh:
        results = [rdap_check(d, d.rsplit(".", 1)[-1]) | {"domain": d, "tld": d.rsplit(".", 1)[-1]} for d in domains]
    else:
        # 慢后缀（.dev/.app）不并行，先并行查完其他后缀，再单独串行查慢后缀，
        # 避免并发把 Google Registry 打到 429。
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(check_one, fast))
        for domain in slow:
            tld = domain.rsplit(".", 1)[-1]
            time.sleep(SLOW_GAP_S)
            ns_state, ns_source = doh_ns(domain)
            if ns_state == "ns":
                results.append({"domain": domain, "tld": tld, "status": "registered", "source": ns_source})
                continue
            fresh = rdap_check(domain, tld)
            results.append(
                {
                    "domain": domain,
                    "tld": tld,
                    "status": fresh["status"],
                    "source": fresh["source"],
                    "detail": fresh.get("detail"),
                }
            )

    order = {d: i for i, d in enumerate(domains)}
    results.sort(key=lambda r: order[r["domain"]])

    for row in results:
        label = STATUS_LABEL.get(row["status"], row["status"])
        extra = f": {row['detail']}" if row.get("detail") else ""
        print(f"{row['domain']:<30} {label:<6} ({row['source']}{extra})")

    counts: dict[str, int] = {}
    for row in results:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    print("\n合计", len(results), counts)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump({"checkedAt": time.strftime("%Y-%m-%dT%H:%M:%S"), "results": results}, handle, ensure_ascii=False, indent=2)
        print("已写入", args.json_out)
    unresolved = sum(counts.get(key, 0) for key in ("unknown", "error"))
    return 1 if unresolved else 0


if __name__ == "__main__":
    sys.exit(main())
