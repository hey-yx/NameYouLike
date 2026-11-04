"""管道输出的 schema 守门：校验统计文件结构完整性（run.py 出口必经）。

真实引擎消费统计走 brandgen.stats.load_patterns（完整/瘦身两种 schema 通吃），
本模块只负责守门，不提供第二份解析。

  .venv/bin/python -m pipeline.consumer output/naming_patterns.v1.json --validate-only
"""
from __future__ import annotations

import argparse
import json
import sys

_REQUIRED_TOP_KEYS = (
    "schema", "version", "generated_at", "corpus", "length_dist", "char_scores",
    "char_pair_scores", "industry_char_affinity", "pinyin_initial_dist",
    "pinyin_style_dist", "collision_index", "recommendation_weights",
)


def validate_output(path: str) -> dict:
    """校验统计文件的结构完整性（推荐引擎接入前可先跑一遍）。"""
    errors = []
    ok = True
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "errors": [f"无法读取/解析: {exc}"]}
    if not isinstance(data, dict):
        return {"ok": False, "errors": ["顶层不是对象"]}
    for key in _REQUIRED_TOP_KEYS:
        if key not in data:
            errors.append(f"缺少顶层字段 {key}")
    if data.get("schema") != "naming-patterns/v1":
        errors.append(f"schema 版本不符: {data.get('schema')}")
    for dist_key in ("length_dist", "pinyin_style_dist"):
        dist = data.get(dist_key)
        if isinstance(dist, dict) and dist:
            total = sum(dist.values())
            if abs(total - 1.0) > 0.02:
                errors.append(f"{dist_key} 概率和 {total:.3f} != 1.0")
    rw = data.get("recommendation_weights")
    if not isinstance(rw, dict) or "w_char" not in rw or "scoring" not in rw:
        errors.append("recommendation_weights 结构不完整")
    w_char = (rw or {}).get("w_char") or {}
    bad_w = [w for w in list(w_char)[:50] if not (0 <= w_char[w] <= 1)]
    if bad_w:
        errors.append(f"w_char 存在越界权重: {bad_w[:5]}")
    coll = data.get("collision_index") or {}
    if not coll.get("exact_names") or not coll.get("phonetic_keys"):
        errors.append("collision_index 为空")
    if errors:
        ok = False
    return {"ok": ok, "errors": errors,
            "stats_records": (data.get("corpus") or {}).get("stats_records", 0)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("patterns_file")
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()

    v = validate_output(args.patterns_file)
    print(f"schema 校验: {'PASS' if v['ok'] else 'FAIL ' + str(v['errors'])}")
    return 0 if v["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
