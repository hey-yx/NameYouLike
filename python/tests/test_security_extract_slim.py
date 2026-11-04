"""extract_slim：守门 + 原子发布，失败不得破坏引擎内置瘦身数据。"""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PYTHON_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PYTHON_ROOT / "scripts" / "extract_slim.py"
sys.path.insert(0, str(PYTHON_ROOT))
sys.path.insert(0, str(PYTHON_ROOT / "naming-pipeline"))

from pipeline import stats as pstats  # noqa: E402


@pytest.fixture(scope="module")
def full_stats(tmp_path_factory):
    path = tmp_path_factory.mktemp("stats") / "naming_patterns.v1.json"
    patterns = pstats.build_patterns(
        [{"record_id": "1", "source": "curated_seed", "kind": "famous_brand",
          "name_clean": "青云", "domain": "qingcloud.com"},
         {"record_id": "2", "source": "curated_seed", "kind": "famous_brand",
          "name_clean": "淘宝", "domain": "taobao.com"}],
        {"version": "v-test", "generated_at": "t", "run_id": "r"})
    path.write_text(json.dumps(patterns, ensure_ascii=False), encoding="utf-8")
    return path


def _run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, cwd=str(PYTHON_ROOT))


def test_invalid_source_is_refused_and_destination_untouched(tmp_path, full_stats):
    dst = tmp_path / "slim.json"
    dst.write_text('{"schema": "previous"}', encoding="utf-8")
    bad = tmp_path / "bad.json"
    bad.write_text('{"schema": "naming-patterns/v1"}', encoding="utf-8")

    proc = _run(str(bad), str(dst))
    assert proc.returncode == 1
    assert "拒绝导出" in proc.stderr
    assert dst.read_text(encoding="utf-8") == '{"schema": "previous"}'
    assert not list(tmp_path.glob("*.tmp"))


def test_success_publishes_and_leaves_no_temp(tmp_path, full_stats):
    dst = tmp_path / "slim.json"
    proc = _run(str(full_stats), str(dst))
    assert proc.returncode == 0, proc.stderr
    data = json.loads(dst.read_text(encoding="utf-8"))
    assert data["schema"] == "brandgen/pattern-stats-slim/v1"
    assert data["exact_names"] and data["phonetic_keys"]
    assert not list(tmp_path.glob("*.tmp"))


def test_failure_mid_extraction_keeps_previous_destination(tmp_path, full_stats):
    dst = tmp_path / "slim.json"
    dst.write_text('{"schema": "previous"}', encoding="utf-8")

    spec = importlib.util.spec_from_file_location("extract_slim_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    def explode(src, out):
        Path(out).write_text('{"schema": "half', encoding="utf-8")
        raise RuntimeError("disk full")

    mod.extract_slim = explode
    argv = sys.argv
    sys.argv = ["extract_slim", str(full_stats), str(dst)]
    try:
        rc = mod.main()
    finally:
        sys.argv = argv
    assert rc == 1
    assert dst.read_text(encoding="utf-8") == '{"schema": "previous"}'
    assert not list(tmp_path.glob("*.tmp"))


def test_script_does_not_import_pipeline_package():
    """核心安装不含 pipeline 包；导出脚本只依赖 brandgen。"""
    code = (
        f"import runpy, sys; runpy.run_path({str(SCRIPT)!r});"
        "print(sorted(m for m in sys.modules if m.split('.')[0] == 'pipeline'))"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                          text=True, cwd=str(PYTHON_ROOT))
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "[]"
