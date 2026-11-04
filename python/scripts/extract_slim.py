"""从数据管道的完整统计文件提取引擎内置瘦身数据。

瘦身提取的**唯一命令行入口**（实现只有 brandgen.stats.extract_slim 一处；
naming-pipeline/scheduled_run.sh 也调用本脚本刷新内置数据）。

用法（在 python/ 目录下）：
    .venv/bin/python scripts/extract_slim.py <naming_patterns.v1.json 路径> [输出路径]

默认输出 brandgen/data/naming_patterns.slim.json（引擎内置，随包分发）。
管道统计更新后重跑本脚本即可刷新内置数据（provenance 会记录来源版本）。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brandgen.stats import extract_slim, load_patterns  # noqa: E402

DEFAULT_OUT = (
    Path(__file__).resolve().parent.parent / "brandgen" / "data" / "naming_patterns.slim.json"
)


def _discard(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else str(DEFAULT_OUT)
    # 只依赖 brandgen（核心安装即含）；pipeline 包不在核心分发包里。
    tmp = dst + ".tmp"
    try:
        summary = extract_slim(src, tmp)
        slim = load_patterns(tmp)       # 发布前回读校验：坏文件不进引擎内置数据
        if not (slim.exact_names and slim.phonetic_keys and slim.w_syllable):
            raise ValueError("提取结果缺少碰撞索引或音节权重（统计文件不完整）")
    except ValueError as exc:
        _discard(tmp)
        print(f"拒绝导出：{src} 未通过 schema 校验：{exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - 磁盘/IO 故障：保留上一份
        _discard(tmp)
        print(f"导出失败（{type(exc).__name__}），已保留上一份数据: {exc}", file=sys.stderr)
        return 1
    os.replace(tmp, dst)
    size_kb = Path(dst).stat().st_size / 1024
    print(json.dumps(summary, ensure_ascii=False))
    print(f"已写入: {dst}（{size_kb:.0f} KB）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
