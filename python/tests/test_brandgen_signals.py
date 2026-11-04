"""brandgen.signals：命名统计文件的自动发现与回退语义。

覆盖：显式文件优先、环境变量 PATTERNS_FILE（旧名 RECO_PATTERNS_FILE 仍兼容）、内置瘦身版兜底、
显式路径不存在时抛错（不静默降级）、管道文件损坏时回退内置版并写 note。

全部离线、确定性。
"""
import json
from pathlib import Path

import pytest

from brandgen import signals
from brandgen.stats import SLIM_SCHEMA

PYTHON_DIR = Path(__file__).resolve().parent.parent


def _slim_file(path: Path, version: str = "2026.test") -> Path:
    path.write_text(json.dumps({
        "schema": SLIM_SCHEMA, "version": version,
        "w_initial": {"c": 1.0}, "w_syllable": {"chi": 1.0},
        "exact_names": [], "phonetic_keys": {},
    }, ensure_ascii=False), encoding="utf-8")
    return path


# ------------------------------------------------------------------ 显式路径

def test_explicit_file_wins(tmp_path):
    """显式指定时只用该文件，不看环境变量与自动发现链。"""
    explicit = _slim_file(tmp_path / "explicit.json", version="2026.explicit")
    stats, note = signals.find_patterns(str(explicit))
    assert stats is not None
    assert stats.version == "2026.explicit"
    assert stats.source == str(explicit)
    assert note is None


def test_explicit_missing_file_raises(tmp_path):
    """显式路径不存在 → 直接报错，不静默降级到其它统计文件。"""
    with pytest.raises(ValueError, match="命名统计文件不存在"):
        signals.find_patterns(str(tmp_path / "missing.json"))


def test_explicit_unparsable_file_raises(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="命名统计文件不可用"):
        signals.find_patterns(str(bad))


# ------------------------------------------------------------- 环境变量优先

def test_env_var_used_when_no_explicit(tmp_path, monkeypatch):
    env_file = _slim_file(tmp_path / "env.json", version="2026.env")
    monkeypatch.setenv("PATTERNS_FILE", str(env_file))
    stats, note = signals.find_patterns()
    assert stats is not None and stats.version == "2026.env"
    assert stats.source == str(env_file)
    assert note is None


def test_legacy_env_var_still_accepted(tmp_path, monkeypatch):
    env_file = _slim_file(tmp_path / "legacy.json", version="2026.legacy")
    monkeypatch.setenv("RECO_PATTERNS_FILE", str(env_file))
    stats, _ = signals.find_patterns()
    assert stats is not None and stats.version == "2026.legacy"


def test_env_var_missing_file_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("PATTERNS_FILE", str(tmp_path / "nope.json"))
    with pytest.raises(ValueError, match="PATTERNS_FILE"):
        signals.find_patterns()


def test_explicit_beats_env_var(tmp_path, monkeypatch):
    explicit = _slim_file(tmp_path / "explicit.json", version="2026.explicit")
    env_file = _slim_file(tmp_path / "env.json", version="2026.env")
    monkeypatch.setenv("PATTERNS_FILE", str(env_file))
    stats, _ = signals.find_patterns(str(explicit))
    assert stats.version == "2026.explicit"


# ------------------------------------------------------------- 自动发现兜底

def test_packaged_slim_used_when_nothing_else(monkeypatch):
    """管道统计不可用时回退到 brandgen 包内置瘦身版。"""
    monkeypatch.delenv("RECO_PATTERNS_FILE", raising=False)
    monkeypatch.setattr(signals, "pipeline_patterns_file", lambda: None)
    stats, note = signals.find_patterns()
    assert stats is not None
    packaged = signals.packaged_patterns_file()
    assert packaged is not None and packaged.is_file()
    assert stats.source == str(packaged)
    assert note is None or "回退" in note


def test_packaged_patterns_file_is_shipped():
    path = signals.packaged_patterns_file()
    assert path is not None and path.is_file()
    assert path.name == "naming_patterns.slim.json"
    assert path.parent.name == "data"


def test_pipeline_file_location():
    """管道统计位于仓库内 naming-pipeline/output/ 下（存在时）。"""
    path = signals.pipeline_patterns_file()
    if path is None:
        pytest.skip("仓库内无管道统计文件")
    assert path.name == "naming_patterns.v1.json"
    assert path.parent.name == "output"


def test_corrupt_pipeline_falls_back_to_packaged(tmp_path, monkeypatch):
    """管道文件被写成半截时回退内置版，note 里说明回退原因。"""
    monkeypatch.delenv("RECO_PATTERNS_FILE", raising=False)
    bad = tmp_path / "naming_patterns.v1.json"
    bad.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(signals, "pipeline_patterns_file", lambda: bad)
    stats, note = signals.find_patterns()
    assert stats is not None
    assert stats.source == str(signals.packaged_patterns_file())
    assert note and "回退" in note


def test_no_stats_found_returns_none_with_note(monkeypatch):
    monkeypatch.delenv("RECO_PATTERNS_FILE", raising=False)
    monkeypatch.setattr(signals, "pipeline_patterns_file", lambda: None)
    monkeypatch.setattr(signals, "packaged_patterns_file", lambda: None)
    stats, note = signals.find_patterns()
    assert stats is None
    assert note and "未找到命名统计文件" in note


# ------------------------------------------------------------ find_patterns_file

def test_find_patterns_file_returns_path(tmp_path):
    explicit = _slim_file(tmp_path / "explicit.json")
    path, note = signals.find_patterns_file(str(explicit))
    assert path == Path(str(explicit))
    assert note is None


def test_find_patterns_file_none_when_absent(monkeypatch):
    monkeypatch.delenv("RECO_PATTERNS_FILE", raising=False)
    monkeypatch.setattr(signals, "pipeline_patterns_file", lambda: None)
    monkeypatch.setattr(signals, "packaged_patterns_file", lambda: None)
    path, note = signals.find_patterns_file()
    assert path is None
    assert note


# ------------------------------------------------------------------ CLI 语义

def test_cli_default_discovers_patterns(tmp_path, monkeypatch, capsys):
    """CLI 不带 --patterns-file 时自动发现统计文件，note 写进输出 JSON。"""
    from brandgen import cli as brandgen_cli

    monkeypatch.delenv("RECO_PATTERNS_FILE", raising=False)
    monkeypatch.setattr(signals, "pipeline_patterns_file", lambda: None)
    out_json = tmp_path / "out.json"
    rc = brandgen_cli.main([
        "--seed", "北斗", "--style", "classic", "--limit", "3",
        "--json", str(out_json),
    ])
    assert rc == 0
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert "note" in payload["patterns"]
    assert payload["patterns"]["source"] == str(signals.packaged_patterns_file())


def test_cli_explicit_missing_file_returns_2(tmp_path, capsys):
    from brandgen import cli as brandgen_cli

    rc = brandgen_cli.main([
        "--seed", "北斗", "--patterns-file", str(tmp_path / "missing.json"),
    ])
    assert rc == 2
    assert "错误:" in capsys.readouterr().err
