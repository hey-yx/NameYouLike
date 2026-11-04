"""命令行入口。

用法示例：
    python -m brandgen --seed 赤兔 --seed 飞跃 --style tech --limit 12 \
        --check-domains --json out.json --md out.md
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from .domains import STATUS_LABEL
from .engine import BrandCandidate, BrandEngine, StyleParams
from .lexicon import AFFIXES
from .signals import find_patterns
from .stats import PatternStats

_EPILOG = """\
示例:
  %(prog)s --seed 赤兔 --style tech --limit 12
  %(prog)s --seed 麒麟 --style classic --extra-vocab 鲲 --extra-vocab 鹏
  %(prog)s --seed 赤兔 --style tech --check-domains --json result.json

注意: 「疑似可注册」来自 RDAP 404 / DNS NXDOMAIN，不代表一定可注册，
注册前请在注册商处复核 whois。\
"""


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="brandgen",
        description="品牌名生成引擎：中文词 × 风格 → 拼音/声母简拼/破折号变体 + 域名建议",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--seed",
        action="append",
        required=True,
        metavar="词",
        help="种子词（纯汉字，可多次提供）",
    )
    ap.add_argument(
        "--style",
        default="neutral",
        choices=list(AFFIXES),
        help="风格参数（默认 neutral）",
    )
    ap.add_argument("--limit", type=int, default=20, help="输出候选数（默认 20）")
    ap.add_argument(
        "--lengths",
        default="2,3,4",
        metavar="N,N",
        help="允许的名字长度（字），逗号分隔（默认 2,3,4）",
    )
    ap.add_argument(
        "--tlds",
        default=None,
        metavar="com,cn",
        help="域名 TLD 池，逗号分隔（默认 com,cn,com.cn,io,ai,tech,app,net）",
    )
    ap.add_argument(
        "--extra-vocab",
        action="append",
        default=[],
        metavar="词",
        help="注入词汇（如 鲲/麟，可多次提供）",
    )
    ap.add_argument(
        "--check-domains",
        action="store_true",
        help="在线核验域名可用性（RDAP 优先，DNS 兜底）",
    )
    ap.add_argument(
        "--live-per-name",
        type=int,
        default=3,
        metavar="N",
        help="每个候选在线核验的域名形式数（默认 3）",
    )
    ap.add_argument(
        "--max-domains",
        type=int,
        default=8,
        metavar="N",
        help="每个候选生成的域名形式数（默认 8）",
    )
    ap.add_argument(
        "--patterns-file",
        default=None,
        metavar="PATH",
        help=(
            "命名模式统计文件（数据管道 naming_patterns.v1.json 或引擎内置瘦身版），"
            "启用音节自然度权重与品牌碰撞排雷；不指定则自动发现"
            "（环境变量 PATTERNS_FILE → 仓库内管道统计 → 内置瘦身版）"
        ),
    )
    ap.add_argument("--json", metavar="PATH", help="将结果写入 JSON 文件")
    ap.add_argument("--md", metavar="PATH", help="将结果写入 Markdown 文件")
    return ap


def _format_candidate(idx: int, c: BrandCandidate, live: bool) -> str:
    p = c.patterns
    lines = [
        f"{idx:>2}. {c.name}  （{p.pinyin_toned}）  评分 {c.score}",
        f"    变体  全拼: {p.pinyin} | 声母简拼: {p.initials} | "
        f"破折号: {p.dash} | 驼峰: {p.camel} | 短横线: {p.kebab} | 首字母: {p.letters}",
        f"    构词  {c.origin}",
    ]
    if c.phonetic is not None:
        coll = ""
        if c.collision and c.collision["type"] == "phonetic":
            coll = f"｜⚠ 同音已有品牌『{c.collision['existing']}』（已强降权）"
        lines.append(
            f"    读音  音节自然度 {c.phonetic:.2f}（真实品牌语料先验）{coll}"
        )
    dom_parts = []
    for d in c.domains:
        if live:
            mark = {"registered": "✗", "likely_available": "✓", "unknown": "?"}[d.status]
            tag = f"{mark} {STATUS_LABEL[d.status]}" + (f" · {d.method}" if d.method else "")
        else:
            tag = STATUS_LABEL["unknown"]
        dom_parts.append(f"{d.domain} [{tag}]")
    lines.append(f"    域名  {' | '.join(dom_parts)}")
    return "\n".join(lines)


def _to_markdown(
    cands: list[BrandCandidate],
    params: StyleParams,
    seeds: list[str],
    engine: BrandEngine | None = None,
) -> str:
    stats: PatternStats | None = engine.stats if engine else None
    rows = [
        "# 品牌名生成结果",
        "",
        f"- 生成时间: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- 种子词: {'、'.join(seeds)}",
        f"- 风格: {params.style}｜在线核验: {'是' if params.live_check else '否'}",
    ]
    if stats:
        rows.append(
            f"- 命名统计: {stats.source}（版本 {stats.version}）｜"
            f"音节自然度加权 + 碰撞排雷（精确重名剔除 {len(engine.last_dropped)} 个，"
            f"同音强降权）"
        )
    rows.append("")
    header = (
        "| # | 名字 | 拼音全拼 | 声母简拼 | 破折号 | 驼峰 | 短横线 | 评分 | 构词 | 域名建议 |"
    )
    if stats:
        header = header[:-1] + "| 音节自然度 | 碰撞 |"
    header += "\n|---|------|---------|---------|--------|------|--------|------|------|----------|"
    if stats:
        header += "-----------|------|"
    rows.append(header)
    for i, c in enumerate(cands, 1):
        p = c.patterns
        doms = "<br>".join(
            f"{d.domain}（{STATUS_LABEL[d.status]}）" for d in c.domains
        )
        row = (
            f"| {i} | {c.name} | {p.pinyin} | {p.initials} | {p.dash} | {p.camel} "
            f"| {p.kebab} | {c.score} | {c.origin} | {doms} |"
        )
        if stats:
            coll = "—"
            if c.collision and c.collision["type"] == "phonetic":
                coll = f"⚠ 同音『{c.collision['existing']}』"
            row += f" {c.phonetic:.2f} | {coll} |"
        rows.append(row)
    if stats and engine and engine.last_dropped:
        names = "、".join(d["name"] for d in engine.last_dropped[:10])
        more = "" if len(engine.last_dropped) <= 10 else " 等"
        rows += ["", f"> 已剔除与现有品牌精确重名的候选：{names}{more}。"]
    rows += [
        "",
        "> 「疑似可注册」= RDAP 404 / DNS NXDOMAIN，注册前请在注册商处复核 whois。",
        "",
    ]
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        lengths = tuple(int(x) for x in args.lengths.split(",") if x.strip())
        # 统计文件解析：显式指定 → 直接用（不存在即报错，不静默降级）；
        # 未指定 → 自动发现（环境变量 → 仓库内管道统计 → 内置瘦身版）。
        stats, note = find_patterns(args.patterns_file)
        params = StyleParams(
            style=args.style,
            lengths=lengths,
            limit=args.limit,
            tlds=args.tlds.split(",") if args.tlds else None,
            live_check=args.check_domains,
            live_per_name=args.live_per_name,
            max_domains=args.max_domains,
            extra_vocab=args.extra_vocab,
        )
        engine = BrandEngine(params, stats=stats)
        candidates = engine.generate(args.seed)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 2

    print(
        f"种子词: {'、'.join(args.seed)}｜风格: {params.style}｜"
        f"候选 {len(candidates)} 个｜域名核验: {'在线' if params.live_check else '未核验（仅形式生成）'}"
    )
    if engine.stats:
        print(
            f"命名统计: {engine.stats.source}（版本 {engine.stats.version}）｜"
            f"精确重名剔除 {len(engine.last_dropped)} 个｜同音碰撞强降权"
        )
    if note:
        print(f"统计说明: {note}")
    print("=" * 72)
    for i, c in enumerate(candidates, 1):
        print(_format_candidate(i, c, params.live_check))
        print("-" * 72)
    if params.live_check:
        print("提示: 「疑似可注册」仍需注册商 whois 复核后方可注册。")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seeds": args.seed,
        "style": params.style,
        "live_check": params.live_check,
        "candidates": [c.as_dict() for c in candidates],
    }
    patterns_payload: dict[str, object] = {"note": note}
    if engine.stats:
        patterns_payload.update({
            "source": engine.stats.source,
            "version": engine.stats.version,
            "exact_names_indexed": len(engine.stats.exact_names),
            "phonetic_keys_indexed": len(engine.stats.phonetic_keys),
            "dropped_exact_collisions": engine.last_dropped,
        })
    payload["patterns"] = patterns_payload
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"JSON 已写入: {args.json}")
    if args.md:
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(_to_markdown(candidates, params, args.seed, engine))
        print(f"Markdown 已写入: {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
