"""命名统计信号接入：定位命名统计文件（音节自然度 + 品牌碰撞排雷的数据源）。

统计文件来自数据管道（``naming-pipeline``）产出的 ``naming_patterns.v1.json``：
真实品牌语料的音节自然度先验 + 已有品牌碰撞索引。本模块只负责**定位**统计文件，
解析与打分由 :mod:`brandgen.stats` 完成。

发现顺序（第一个可用者胜出）：

1. 显式传入的 ``patterns_file``（不存在 → 立即报错，不静默降级）
2. 环境变量 ``PATTERNS_FILE``（旧名 ``RECO_PATTERNS_FILE`` 仍兼容，同上）
3. 项目内管道完整统计 ``python/naming-pipeline/output/naming_patterns.v1.json``
   （每日增量，最新；解析失败 → 记录原因并回退到内置瘦身版）
4. ``brandgen`` 包内置瘦身统计 ``brandgen/data/naming_patterns.slim.json``
   （随包分发，离线开箱可用）

3 → 4 的自动回退只在「管道文件不可解析」时发生（例如 cron 正在写入的半截
JSON），回退原因写进返回的 ``note``，便于排查，不是静默降级：排雷仍然由
可用的统计文件提供。
"""
from __future__ import annotations

import os
from pathlib import Path

# 相对 python/ 目录（本模块位于 python/brandgen/）。
PIPELINE_RELATIVE = Path("naming-pipeline") / "output" / "naming_patterns.v1.json"

# brandgen 包内置瘦身统计（与本模块同级 data/ 目录）。
PACKAGED_RELATIVE = Path("data") / "naming_patterns.slim.json"


def pipeline_patterns_file() -> Path | None:
    """项目内数据管道的完整统计文件（开发/部署在同一仓库时存在）。"""
    path = Path(__file__).resolve().parent.parent / PIPELINE_RELATIVE
    return path if path.is_file() else None


def packaged_patterns_file() -> Path | None:
    """brandgen 包内置的瘦身统计（随包分发）。"""
    path = Path(__file__).resolve().parent / PACKAGED_RELATIVE
    return path if path.is_file() else None


def _loadable(path: Path):
    """尝试解析统计文件；返回 ``(PatternStats, None)`` 或 ``(None, 错误说明)``。"""
    try:
        from .stats import load_patterns
    except ImportError:  # pragma: no cover - 环境异常
        return None, "brandgen.stats 不可导入"
    try:
        return load_patterns(str(path)), None
    except (ValueError, OSError) as exc:
        return None, str(exc)


def find_patterns(explicit=None):
    """定位**并解析**命名统计文件，返回 ``(PatternStats | None, note)``。

    发现顺序与回退语义同模块 docstring；每个候选只解析一次，调用方可把返回的
    stats 直接交给 :class:`brandgen.BrandEngine`，避免同一文件每请求重复解析。
    """
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise ValueError(f"命名统计文件不存在: {path}")
        stats, err = _loadable(path)
        if stats is None:
            raise ValueError(f"命名统计文件不可用: {path}（{err}）")
        return stats, None

    env = os.environ.get("PATTERNS_FILE") or os.environ.get("RECO_PATTERNS_FILE")
    if env:
        path = Path(env).expanduser()
        if not path.is_file():
            raise ValueError(f"PATTERNS_FILE 指向的文件不存在: {path}")
        stats, err = _loadable(path)
        if stats is None:
            raise ValueError(f"PATTERNS_FILE 指向的文件不可用: {path}（{err}）")
        return stats, None

    note: list[str] = []
    for label, candidate in (("管道统计", pipeline_patterns_file()),
                             ("内置统计", packaged_patterns_file())):
        if not candidate:
            continue
        stats, err = _loadable(candidate)
        if stats is not None:
            if note:
                note.append(f"已回退到{label}: {candidate}")
            return stats, "；".join(note) or None
        note.append(f"{label}不可用({candidate}): {err}")
    return None, "；".join(note) or "未找到命名统计文件，自然度与碰撞排雷未启用"


def find_patterns_file(explicit=None) -> tuple[Path | None, str | None]:
    """定位命名统计文件，返回 ``(path, note)``；找不到时 ``path`` 为 None。

    只需要路径时用本函数；需要消费统计内容请用 :func:`find_patterns`
    （返回已解析对象，不重复解析）。``note`` 只在自动选择发生回退/缺失时给出。
    """
    stats, note = find_patterns(explicit)
    return (Path(stats.source) if stats is not None else None), note
