"""端到端运行入口。

用法:
  .venv/bin/python -m pipeline.run                      # 全源在线运行（真实抓取 + 增量更新）
  .venv/bin/python -m pipeline.run --offline            # 仅种子语料（离线冒烟/CI）
  .venv/bin/python -m pipeline.run --max-f10 300       # F10 补全数量
  .venv/bin/python -m pipeline.run --no-wiki           # 跳过维基源

输出:
  output/naming_patterns.v1.json   当前统计文件（推荐引擎消费入口）
  output/history/<version>.json    版本化存档
  runs/run_<ts>/record.{json,md}  端到端运行记录
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

from . import sources as srcs
from .clean import clean_short_name
from .consumer import validate_output
from .dedup import DedupIndex
from .stats import build_patterns
from .store import PipelineStore

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HISTORY_KEEP = 30


def _prune_history(hist_dir: str, keep: int = HISTORY_KEEP) -> int:
    """历史快照只保留最近 keep 份（文件名即版本号，字典序=时间序），返回删除数。"""
    snapshots = sorted(name for name in os.listdir(hist_dir) if name.endswith(".json"))
    stale = snapshots[:-keep] if keep > 0 else snapshots
    for name in stale:
        os.remove(os.path.join(hist_dir, name))
    return len(stale)


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def reclean_corpus(corpus: list[dict], log=None) -> list[dict]:
    """按当前清洗逻辑对全量语料重清洗（幂等），并重新去重压缩。

    语料持久化的是 name_raw（各源原始名），清洗逻辑升级后可用此函数重建 name_clean。
    F10 等补全字段（全称/域名/行业）不可从 raw 重导，原样保留。
    """
    from .sources import clean_wiki_title
    recleaned = []
    for rec in corpus:
        src = rec.get("source", "")
        raw = rec.get("name_raw") or ""
        name = rec.get("name_clean")
        if src == "wiki_zh_brand":
            name = clean_wiki_title(raw)
        elif src in ("eastmoney_ipo", "cninfo_all_a", "curated_seed"):
            name, _ = clean_short_name(raw)
        if not name:
            continue
        rec = dict(rec)
        rec["name_clean"] = name
        recleaned.append(rec)
    index = DedupIndex()
    kept = []
    for rec in recleaned:
        if index.add(rec) is rec and not rec.get("phonetic_dup_of"):
            kept.append(rec)
    if log:
        log(f"[rebuild] 重清洗 {len(corpus)} -> {len(recleaned)} 条有效，压缩去重后 {len(kept)} 条")
    return kept


def run_pipeline(data_dir: str = None, output_dir: str = None, seeds_path: str = None,
                 offline: bool = False, max_f10: int = 300, use_wiki: bool = True,
                 use_cninfo: bool = True, use_ipo: bool = True, use_apps: bool = True,
                 rebuild_stats: bool = False) -> dict:
    data_dir = data_dir or os.path.join(BASE, "data")
    output_dir = output_dir or os.path.join(BASE, "output")
    runs_dir = os.path.join(os.path.dirname(os.path.abspath(data_dir)), "runs")
    seeds_path = seeds_path or srcs.default_seeds_path()
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(runs_dir, exist_ok=True)
    store = PipelineStore(data_dir)

    run_id = "run_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    log_lines: list[str] = []

    def log(msg: str) -> None:
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        log_lines.append(line)
        print(line, flush=True)

    started = time.time()
    store.acquire_lock()
    try:
        state = store.load_state()
        version_seq = state.get("version_seq", 0) + 1
        log(f"=== {run_id} 开始（version_seq={version_seq}, offline={offline}）===")

        # ---------- 1) 采集（rebuild 模式跳过抓取，改为全量重清洗） ----------
        fetched: list[dict] = []
        source_stats: dict[str, dict] = {}
        failures: list[str] = []
        raw_snapshots = {}
        f10_stats = {"f10_enriched": 0, "f10_failed": 0}

        if rebuild_stats:
            corpus = store.load_corpus()
            full_corpus = reclean_corpus(corpus, log)
            import json as _json
            tmp_corpus = store.corpus_path + ".tmp"
            with open(tmp_corpus, "w", encoding="utf-8") as f:
                for rec in full_corpus:
                    f.write(_json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
                os.fsync(f.fileno())
            # 读回校验后再替换：中途异常不会把语料截断成半截。
            with open(tmp_corpus, encoding="utf-8") as check:
                for line in check:
                    if line.strip():
                        _json.loads(line)
            os.replace(tmp_corpus, store.corpus_path)
            new_records = []
            dup_in_run = len(corpus) - len(full_corpus)
            log(f"rebuild 模式: 语料重清洗压缩 {len(corpus)} -> {len(full_corpus)} 条")
        else:
            def _fetch(name, fn):
                t0 = time.time()
                try:
                    recs = fn(log)
                    fetched.extend(recs)
                    raw_snapshots[name] = store.save_raw_snapshot(name, recs)
                    source_stats[name] = {"count": len(recs), "seconds": round(time.time() - t0, 1)}
                except Exception as exc:  # noqa: BLE001
                    failures.append(f"{name}: {exc}")
                    log(f"[{name}] FAILED: {exc}")
                    source_stats[name] = {"error": str(exc)}

            _fetch("seed", lambda l: srcs.SeedCorpusSource(seeds_path).fetch(l))
            if not offline:
                if use_ipo:
                    _fetch("eastmoney_ipo", lambda l: srcs.EastmoneyIpoApplySource().fetch(l))
                if use_cninfo:
                    _fetch("cninfo_all_a", lambda l: srcs.CninfoStockListSource().fetch(l))
                if use_apps:
                    _fetch("itunes_apps", lambda l: srcs.ItunesAppSource().fetch(l))
                if use_wiki:
                    _fetch("wiki_zh_brand", lambda l: srcs.WikiCategorySource().fetch(l))

            # F10 补全（依赖 IPO 源记录）
            if not offline and use_ipo and max_f10 > 0:
                ipo_records = [r for r in fetched if r["source"] == "eastmoney_ipo"]
                try:
                    f10_stats = srcs.enrich_with_f10(ipo_records, max_f10, log)
                except Exception as exc:  # noqa: BLE001
                    failures.append(f"eastmoney_f10: {exc}")
                    log(f"[f10] batch failed: {exc}")

            log(f"采集合计: {len(fetched)} 条（源: {list(source_stats)}）")

            # ---------- 2) 增量去重（对全量累积语料） ----------
            corpus = store.load_corpus()
            index = DedupIndex()
            for rec in corpus:
                index.add(rec)
            new_records = []
            dup_in_run = 0
            seen_in_run: set[str] = set()
            for rec in fetched:
                rid = rec["record_id"]
                if rid in seen_in_run:
                    dup_in_run += 1
                    continue
                kept = index.add(rec)
                if kept is rec:
                    seen_in_run.add(rid)
                    if not rec.get("phonetic_dup_of"):
                        new_records.append(rec)
                else:
                    dup_in_run += 1
            log(f"去重: 新增 {len(new_records)}，重复 {dup_in_run}（历史语料 {len(corpus)} 条）")
            # ---------- 3) 追加语料 ----------
            store.append_records(new_records)
            full_corpus = corpus + new_records
        version = time.strftime("%Y.%m.%d") + f"-{version_seq:03d}"
        run_meta = {
            "version": version,
            "generated_at": _now_utc(),
            "run_id": run_id,
            "provenance": {
                "sources": source_stats,
                "raw_snapshots": {k: v for k, v in raw_snapshots.items() if v},
                "f10": f10_stats,
                "offline_mode": offline,
            },
            "quality": {
                "new_records": len(new_records),
                "duplicates_skipped": dup_in_run,
                "corpus_before": len(corpus),
                "failures": failures,
            },
        }
        patterns = build_patterns(full_corpus, run_meta)

        # ---------- 4) 写输出 + 自校验 ----------
        # 先写临时文件并校验，通过后才原子替换：失败时上一份有效统计仍然可用，
        # 也不会让 Web 进程读到半截 JSON。
        out_path = os.path.join(output_dir, "naming_patterns.v1.json")
        tmp_out = out_path + ".tmp"
        with open(tmp_out, "w", encoding="utf-8") as f:
            json.dump(patterns, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())
        validation = validate_output(tmp_out)
        if validation["ok"]:
            os.replace(tmp_out, out_path)
        else:
            os.remove(tmp_out)
        hist_dir = os.path.join(output_dir, "history")
        os.makedirs(hist_dir, exist_ok=True)
        if validation["ok"]:
            hist_path = os.path.join(hist_dir, f"{version}.json")
            tmp_hist = hist_path + ".tmp"
            with open(tmp_hist, "w", encoding="utf-8") as f:
                json.dump(patterns, f, ensure_ascii=False, indent=1)
            os.replace(tmp_hist, hist_path)
        if not validation["ok"]:
            # 校验失败不发布：保留上一份有效统计与全部旧快照，让调度看到非零退出。
            raise RuntimeError(f"schema 校验未通过，已保留上一份输出: {validation['errors']}")
        pruned = _prune_history(hist_dir)
        log(f"输出: {out_path}（{os.path.getsize(out_path) // 1024} KB）；schema 校验: PASS"
            + (f"；历史快照清理 {pruned} 份（保留最近 {HISTORY_KEEP} 份）" if pruned else ""))

        # ---------- 5) 运行记录 ----------
        duration = round(time.time() - started, 1)
        f10_samples = [
            {
                "full": r.get("company_full_name"),
                "trade": r.get("trade_name"),
                "region": r.get("region"),
                "domain": r.get("domain"),
                "industry": r.get("industry"),
                "ops": r.get("clean_ops"),
            }
            for r in full_corpus if r.get("f10")
        ][:10]
        record = {
            "run_id": run_id, "version": version, "started_utc": run_meta["generated_at"],
            "duration_seconds": duration, "offline": offline, "rebuild_stats": rebuild_stats,
            "sources": source_stats, "f10": f10_stats, "failures": failures,
            "fetched": len(fetched), "new_records": len(new_records), "duplicates": dup_in_run,
            "corpus_total": len(full_corpus),
            "corpus_stats": patterns["corpus"],
            "length_dist": patterns["length_dist"],
            "pinyin_style_dist": patterns["pinyin_style_dist"],
            "cleaning_examples": f10_samples,
            "validation": validation,
            "log": log_lines,
        }
        run_dir = os.path.join(runs_dir, run_id)
        os.makedirs(run_dir, exist_ok=True)
        with open(os.path.join(run_dir, "record.json"), "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=1)
        with open(os.path.join(run_dir, "record.md"), "w", encoding="utf-8") as f:
            f.write(_render_run_md(record, patterns))

        # ---------- 6) 状态推进（增量水位） ----------
        state["version_seq"] = version_seq
        state["last_run_at"] = run_meta["generated_at"]
        state["last_version"] = version
        watermarks = state.setdefault("watermarks", {})
        for name, st in source_stats.items():
            if st.get("count"):
                watermarks[name] = {"last_count": st["count"], "at": run_meta["generated_at"]}
        state.setdefault("runs", []).append({
            "run_id": run_id, "version": version, "new_records": len(new_records),
            "corpus_total": len(full_corpus), "at": run_meta["generated_at"],
        })
        store.save_state(state)

        log(f"=== 完成: 语料 {len(full_corpus)} 条, 新增 {len(new_records)}, 用时 {duration}s ===")
        return record
    finally:
        store.release_lock()


def _render_run_md(record: dict, patterns: dict) -> str:
    lines = [
        f"# 端到端运行记录 — {record['run_id']}",
        "",
        f"- 版本: **{record['version']}**  时间: {record['started_utc']}  用时: {record['duration_seconds']}s",
        f"- 模式: {'重建统计（全量重清洗，无抓取）' if record.get('rebuild_stats') else ('离线（种子语料）' if record['offline'] else '在线（真实抓取）')}",
        f"- 语料总量: {record['corpus_total']} 条（本次新增 {record['new_records']}，去重/跳过 {record['duplicates']}）",
        "",
        "## 数据源",
        "",
        "| 源 | 记录数 | 耗时 |",
        "|---|---|---|",
    ]
    for name, st in record["sources"].items():
        if st.get("skipped"):
            lines.append(f"| {name} | 跳过 | - |")
        else:
            lines.append(f"| {name} | {st.get('count', 'ERR')} | {st.get('seconds', '-')}s |")
    if record.get("f10", {}).get("f10_enriched"):
        lines.append(f"| eastmoney_f10（补全: 全称/区域/行业/域名） | {record['f10']['f10_enriched']} | - |")
    if record["failures"]:
        lines += ["", "## 失败源", ""] + [f"- {f}" for f in record["failures"]]
    lines += [
        "",
        "## 统计语料构成",
        "",
        f"- 统计口径: {record['corpus_stats']['stats_records']} 条（新企业 + 知名品牌）；"
        f"存量基线 {record['corpus_stats']['baseline_records']} 条仅入碰撞索引",
        f"- 按源: " + ", ".join(f"{k}={v}" for k, v in record['corpus_stats']['by_source_counts'].items()),
        f"- 含域名: {record['corpus_stats']['with_domain']} 条；含行业: {record['corpus_stats']['with_industry']} 条",
        "",
        "## 关键统计（节选）",
        "",
        "### 长度分布（音节数）",
        "",
        "| 长度 | 占比 |",
        "|---|---|",
    ]
    for k, v in record["length_dist"].items():
        lines.append(f"| {k} 字 | {_fmt_pct(v)} |")
    lines += ["", "### 拼音风格分布（知名品牌 中文 <-> 域名）", "", "| 风格 | 占比 |", "|---|---|"]
    for k, v in record["pinyin_style_dist"].items():
        lines.append(f"| {k} | {_fmt_pct(v)} |")
    top_chars = list(patterns["char_scores"].items())[:15]
    lines += ["", "### 高频用字 Top15",
              "", "```", ", ".join(f"{ch}({v['count']})" for ch, v in top_chars), "```"]
    if patterns["pinyin_style_examples"]:
        lines += ["", "### 拼音风格示例", ""]
        for style, exs in patterns["pinyin_style_examples"].items():
            sample = "、".join(f"{e['name']}→{e['domain']}" for e in exs[:5])
            lines.append(f"- **{style}**: {sample}")
    if record.get("cleaning_examples"):
        lines += ["", "### 清洗链真实示例（F10 公司全称 → 字号）", "",
                  "| 公司全称 | → 字号 | 区域 | 行业 | 官网 |", "|---|---|---|---|---|"]
        for ex in record["cleaning_examples"]:
            lines.append(f"| {ex['full']} | **{ex['trade']}** | {ex['region'] or '-'} "
                         f"| {ex['industry'] or '-'} | {ex['domain'] or '-'} |")
    coll = patterns["collision_index"]
    lines += [
        "",
        "## 碰撞索引",
        "",
        f"- 精确名称 {len(coll['exact_names'])} 个；语音键 {len(coll['phonetic_keys'])} 个（推荐引擎用于候选去撞）",
        "",
        "## 校验",
        "",
        f"- 输出 schema 校验: {'**PASS**' if record['validation']['ok'] else '**FAIL** ' + str(record['validation']['errors'])}",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="品牌命名持续学习管道")
    ap.add_argument("--offline", action="store_true", help="仅使用本地种子语料（不联网）")
    ap.add_argument("--max-f10", type=int, default=300, help="F10 补全的最大记录数")
    ap.add_argument("--no-wiki", action="store_true")
    ap.add_argument("--no-cninfo", action="store_true")
    ap.add_argument("--no-ipo", action="store_true")
    ap.add_argument("--no-apps", action="store_true", help="跳过 App Store 榜单源")
    ap.add_argument("--rebuild-stats", action="store_true",
                    help="不抓取：按当前清洗逻辑重清洗全量语料并重算统计（清洗逻辑升级后用）")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args()
    record = run_pipeline(
        data_dir=args.data_dir, output_dir=args.output_dir, offline=args.offline,
        max_f10=args.max_f10, use_wiki=not args.no_wiki, use_cninfo=not args.no_cninfo,
        use_ipo=not args.no_ipo, use_apps=not args.no_apps, rebuild_stats=args.rebuild_stats,
    )
    return 0 if record["validation"]["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
