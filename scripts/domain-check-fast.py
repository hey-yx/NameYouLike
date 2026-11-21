#!/usr/bin/env python3
"""域名与品牌商标初筛查询：
- 域名可用性：三段式（DoH NS 预筛 → 权威 RDAP → WHOIS 兜底）
- 离线品牌库（--brand-only / --full）：国际科技品牌 + 8000+ 国内品牌与上市公司字号/拼音碰撞
- 全量联查（--full）：域名 + npm + GitHub + 本地品牌库 + Wikidata 实体 + App Store 美/中区在营软件

用法：
  python3 scripts/domain-check-fast.py example.com example.dev
  python3 scripts/domain-check-fast.py --variants linkpeel,bareclip
  python3 scripts/domain-check-fast.py --variants linkpeel,bareclip --full --json out.json
  python3 scripts/domain-check-fast.py --variants stripe,taobao,linkpeel --brand-only --json out.json
"""
from __future__ import annotations

import argparse
import json
import re
import socket as socket_module
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

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
DOH_URLS = (
    "https://dns.google/resolve?name={name}&type=NS",
    "https://cloudflare-dns.com/dns-query?name={name}&type=NS",
)

STATUS_LABEL = {
    "available": "可注册",
    "registered": "已注册",
    "reserved": "保留",
    "premium": "溢价",
    "unknown": "未确认",
    "error": "查询出错",
}

FRIENDLY_PREFIXES = (
    "get", "try", "use", "hey", "hi", "meet", "go", "join", "ask",
    "pick", "run", "with", "onmy", "one", "ohmy", "hello",
)

WIKIDATA_KEYWORDS = (
    "software", "trademark", "brand", "company", "business", "application",
    "service", "platform", "corporation", "enterprise", "product", "library",
    "framework", "tool", "app", "website", "startup", "organization", "developer",
)


def http_get(url: str, accept: str, timeout: float = 12.0) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={
            "accept": accept,
            "user-agent": "NameYouLike/1.0 (https://github.com/hey-yx/NameYouLike)",
        },
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


def socket_create_connection(host: str, timeout: float):
    return socket_module.create_connection((host, 43), timeout=timeout)


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


def check_one(domain: str) -> dict:
    tld = domain.rsplit(".", 1)[-1]
    ns_state, ns_source = doh_ns(domain)
    if ns_state == "ns":
        return {"domain": domain, "tld": tld, "status": "registered", "source": ns_source}
    result = rdap_check(domain, tld)
    return {
        "domain": domain,
        "tld": tld,
        "status": result["status"],
        "source": result["source"],
        "detail": result.get("detail"),
    }


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ch_a in enumerate(a, 1):
        curr = [i]
        for j, ch_b in enumerate(b, 1):
            cost = 0 if ch_a == ch_b else 1
            curr.append(min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def _normalize_latin(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _strip_friendly_prefix(flat: str) -> str:
    for prefix in FRIENDLY_PREFIXES:
        if flat.startswith(prefix) and len(flat) > len(prefix) + 2:
            return flat[len(prefix) :]
    return flat


def load_local_brand_db() -> dict:
    """加载仓库内置的国际品牌列表 + 国内 8000+ 品牌/上市公司字号及拼音索引。"""
    global_brands: list[str] = []
    brands_ts = REPO_ROOT / "lib" / "naming" / "brands.ts"
    if brands_ts.is_file():
        text = brands_ts.read_text(encoding="utf-8")
        arr_match = re.search(r"export const KNOWN_BRANDS = \[(.*?)\];", text, re.S)
        if arr_match:
            seen: set[str] = set()
            for token in re.findall(r'"([a-z0-9]+)"', arr_match.group(1)):
                if token not in seen:
                    seen.add(token)
                    global_brands.append(token)

    cn_exact: dict[str, str] = {}
    cn_phonetic: dict[str, str] = {}
    full_stats = REPO_ROOT / "python" / "naming-pipeline" / "output" / "naming_patterns.v1.json"
    slim_stats = REPO_ROOT / "python" / "brandgen" / "data" / "naming_patterns.slim.json"
    for candidate_path in (full_stats, slim_stats):
        if not candidate_path.is_file():
            continue
        try:
            data = json.loads(candidate_path.read_text(encoding="utf-8"))
            if "collision_index" in data:
                coll = data.get("collision_index") or {}
                exact_list = coll.get("exact_names") or []
                phonetic_map = coll.get("phonetic_keys") or {}
            else:
                exact_list = data.get("exact_names") or []
                phonetic_map = data.get("phonetic_keys") or {}
            for item in exact_list:
                if item:
                    cn_exact[str(item).lower()] = str(item)
            for k, v in phonetic_map.items():
                if k and v:
                    cn_phonetic[str(k).lower()] = str(v)
            break
        except Exception:
            continue

    seeds_path = REPO_ROOT / "python" / "naming-pipeline" / "seeds" / "brand_domains.json"
    if seeds_path.is_file():
        try:
            seeds = json.loads(seeds_path.read_text(encoding="utf-8"))
            for item in seeds:
                name = str(item.get("name") or "").strip()
                domain = str(item.get("domain") or "").strip().lower()
                if name:
                    cn_exact.setdefault(name.lower(), name)
                if "." in domain:
                    sld = _normalize_latin(domain.split(".", 1)[0])
                    if sld and name:
                        cn_phonetic.setdefault(sld, name)
        except Exception:
            pass

    return {
        "global_brands": global_brands,
        "global_set": set(global_brands),
        "cn_exact": cn_exact,
        "cn_phonetic": cn_phonetic,
    }


def match_local_brands(name: str, db: dict) -> tuple[str | None, str | None]:
    """返回 (localGlobalHit, localCnHit)。"""
    raw_lower = name.strip().lower()
    flat = _normalize_latin(name)
    stem = _strip_friendly_prefix(flat)
    forms = [flat] if stem == flat else [flat, stem]

    global_hit = None
    global_set: set[str] = db["global_set"]
    global_list: list[str] = db["global_brands"]
    for form in forms:
        if not form:
            continue
        if form in global_set:
            global_hit = form
            break
        if len(form) >= 5:
            for brand in global_list:
                if len(brand) >= 5 and _levenshtein(form, brand) <= 1:
                    global_hit = f"{brand}（拼写近似 {form}）"
                    break
        if global_hit:
            break

    cn_hit = None
    cn_exact: dict[str, str] = db["cn_exact"]
    cn_phonetic: dict[str, str] = db["cn_phonetic"]
    if raw_lower in cn_exact:
        cn_hit = cn_exact[raw_lower]
    else:
        for form in forms:
            if form in cn_phonetic:
                cn_hit = f"{cn_phonetic[form]}（拼音/域名字根 {form}）"
                break
            if form in cn_exact:
                cn_hit = cn_exact[form]
                break

    return global_hit, cn_hit


def check_npm(pkg: str) -> dict:
    url = f"https://registry.npmjs.org/{urllib.parse.quote(pkg, safe='')}"
    code, _ = http_get(url, "application/json", timeout=10.0)
    if code == 404:
        return {"status": "available", "code": 404}
    if code == 200:
        return {"status": "taken", "code": 200}
    return {"status": "unknown", "code": code}


def check_github(pkg: str) -> dict:
    user_url = f"https://github.com/{urllib.parse.quote(pkg, safe='')}"
    user_code, _ = http_get(user_url, "text/html", timeout=10.0)
    user_status = "available" if user_code == 404 else "taken" if user_code == 200 else "unknown"

    q = urllib.parse.quote(f"{pkg} in:name")
    search_url = f"https://api.github.com/search/repositories?q={q}&sort=stars&per_page=3"
    search_code, body = http_get(search_url, "application/vnd.github+json", timeout=10.0)
    repo_count: int | None = None
    top_repo: str | None = None
    top_stars: int | None = None
    if search_code == 200:
        try:
            data = json.loads(body)
            repo_count = data.get("total_count")
            items = data.get("items") or []
            if items:
                top_repo = items[0].get("full_name")
                top_stars = items[0].get("stargazers_count")
        except json.JSONDecodeError:
            pass
    return {
        "userStatus": user_status,
        "userCode": user_code,
        "repoCount": repo_count,
        "topRepo": top_repo,
        "topStars": top_stars,
        "searchCode": search_code,
    }


def check_wikidata(name: str) -> tuple[list[dict], bool]:
    """检索 Wikidata 中同名商标/品牌/软件实体，返回 (hits, reachable)。"""
    target = _normalize_latin(name)
    query = name.replace("-", " ")
    url = (
        "https://www.wikidata.org/w/api.php"
        f"?action=wbsearchentities&search={urllib.parse.quote(query)}"
        "&language=en&format=json&limit=5"
    )
    code, body = http_get(url, "application/json", timeout=10.0)
    if code != 200:
        return [], False
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return [], False

    hits: list[dict] = []
    for item in data.get("search") or []:
        label = str(item.get("label") or "")
        desc = str(item.get("description") or "")
        if _normalize_latin(label) != target:
            continue
        desc_lower = desc.lower()
        if any(kw in desc_lower for kw in WIKIDATA_KEYWORDS):
            hits.append(
                {
                    "id": item.get("id"),
                    "label": label,
                    "description": desc,
                }
            )
    return hits, True


def check_appstore(name: str, country: str) -> tuple[list[dict], bool]:
    """检索 Apple App Store 美/中区在营软件（第 9/42 类实务碰撞），返回 (hits, reachable)。"""
    target = _normalize_latin(name)
    query = name.replace("-", " ")
    url = (
        "https://itunes.apple.com/search"
        f"?term={urllib.parse.quote(query)}&country={country}&entity=software&limit=5"
    )
    code, body = http_get(url, "application/json", timeout=10.0)
    if code != 200:
        return [], False
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return [], False

    hits: list[dict] = []
    for item in data.get("results") or []:
        track_name = str(item.get("trackName") or "")
        main_title = re.split(r"[-—–:：·|（(]", track_name, maxsplit=1)[0]
        if _normalize_latin(main_title) == target:
            hits.append(
                {
                    "trackName": track_name,
                    "sellerName": item.get("sellerName"),
                    "trackId": item.get("trackId"),
                }
            )
    return hits, True


def run_brand_check(name: str, db: dict, online: bool) -> dict:
    local_global, local_cn = match_local_brands(name, db)
    if not online:
        conflicts = [x for x in (local_global, local_cn) if x]
        status = "conflict" if conflicts else "clean"
        summary = (
            f"命中本地品牌库：{'、'.join(conflicts)}"
            if conflicts
            else "本地 8200+ 中外品牌与字号库未见碰撞"
        )
        return {
            "name": name,
            "npm": None,
            "github": None,
            "trademark": {
                "status": status,
                "localGlobalHit": local_global,
                "localCnHit": local_cn,
                "wikidataHits": [],
                "appStoreUsHits": [],
                "appStoreCnHits": [],
                "summary": summary,
            },
        }

    npm_res = check_npm(name)
    gh_res = check_github(name)
    wd_hits, wd_ok = check_wikidata(name)
    us_hits, us_ok = check_appstore(name, "us")
    cn_hits, cn_ok = check_appstore(name, "cn")

    has_conflict = bool(local_global or local_cn or wd_hits or us_hits or cn_hits)
    all_ok = wd_ok and us_ok and cn_ok
    if has_conflict:
        tm_status = "conflict"
        parts = []
        if local_global:
            parts.append(f"国际品牌库({local_global})")
        if local_cn:
            parts.append(f"国内品牌库({local_cn})")
        if wd_hits:
            parts.append(f"Wikidata({len(wd_hits)}条)")
        if us_hits:
            parts.append(f"AppStore美区({us_hits[0]['trackName']})")
        if cn_hits:
            parts.append(f"AppStore国区({cn_hits[0]['trackName']})")
        summary = "存在品牌或软件碰撞：" + "、".join(parts)
    elif all_ok:
        tm_status = "clean"
        summary = "多源商标与品牌初筛未见冲突（本地8200+中外品牌库、Wikidata、App Store美/中区软件类均无同名记录）"
    else:
        tm_status = "partial"
        missing = []
        if not wd_ok:
            missing.append("Wikidata")
        if not us_ok:
            missing.append("AppStore美区")
        if not cn_ok:
            missing.append("AppStore国区")
        summary = f"本地库无碰撞；外部源未完全连通（{','.join(missing)} 未返回）"

    return {
        "name": name,
        "npm": npm_res,
        "github": gh_res,
        "trademark": {
            "status": tm_status,
            "localGlobalHit": local_global,
            "localCnHit": local_cn,
            "wikidataHits": wd_hits,
            "appStoreUsHits": us_hits,
            "appStoreCnHits": cn_hits,
            "summary": summary,
        },
    }


def _extract_bare_names(raw_args: list[str], variants_arg: str) -> list[str]:
    names: list[str] = []
    if variants_arg:
        for item in variants_arg.split(","):
            item = item.strip().lower()
            if item:
                names.append(item)
    for raw in raw_args:
        for part in raw.split(","):
            part = part.strip().lower()
            if not part:
                continue
            bare = part.split(".", 1)[0] if "." in part else part
            if bare:
                names.append(bare)
    return list(dict.fromkeys(names))


def main() -> int:
    parser = argparse.ArgumentParser(description="三段式域名与多源品牌/商标初筛查询")
    parser.add_argument("domains", nargs="*")
    parser.add_argument("--variants", default="", help="逗号分隔的裸名，自动配 com/net/io/ai/dev/app")
    parser.add_argument("--json", dest="json_out", default="")
    parser.add_argument("--no-doh", action="store_true", help="跳过 DNS 预筛，全部直查 RDAP")
    parser.add_argument(
        "--full",
        action="store_true",
        help="同时核验 npm、GitHub、本地品牌库、Wikidata 实体与 App Store 美/中区在营软件",
    )
    parser.add_argument(
        "--brand-only",
        action="store_true",
        help="仅执行离线本地 8200+ 中外品牌与字号碰撞检查（不联网）",
    )
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
    bare_names = _extract_bare_names(args.domains, args.variants)

    if not domains and not bare_names:
        parser.print_help()
        return 0

    results: list[dict] = []
    if not args.brand_only and domains:
        slow = [d for d in domains if d.rsplit(".", 1)[-1] in SLOW_TLDS]
        fast = [d for d in domains if d not in slow]

        if args.no_doh:
            results = [
                rdap_check(d, d.rsplit(".", 1)[-1]) | {"domain": d, "tld": d.rsplit(".", 1)[-1]}
                for d in domains
            ]
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
    if results:
        print("\n合计", len(results), counts)

    brand_checks: list[dict] = []
    if (args.full or args.brand_only) and bare_names:
        db = load_local_brand_db()
        online = args.full and not args.brand_only
        print("\n品牌、包名与多源商标初筛：")
        for bare in bare_names:
            item = run_brand_check(bare, db, online=online)
            brand_checks.append(item)
            tm = item["trademark"]
            if online:
                npm_s = item["npm"]["status"]
                gh_u = item["github"]["userStatus"]
                gh_r = item["github"]["repoCount"]
                print(
                    f"  {bare:<18} npm={npm_s:<9} gh_user={gh_u:<9} gh_repos={str(gh_r):<6} tm={tm['status']} | {tm['summary']}"
                )
            else:
                print(f"  {bare:<18} tm={tm['status']} | {tm['summary']}")

    if args.json_out:
        payload: dict = {"checkedAt": time.strftime("%Y-%m-%dT%H:%M:%S"), "results": results}
        if brand_checks:
            payload["brandChecks"] = brand_checks
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        print("已写入", args.json_out)

    unresolved = sum(counts.get(key, 0) for key in ("unknown", "error"))
    return 1 if unresolved else 0


if __name__ == "__main__":
    sys.exit(main())
