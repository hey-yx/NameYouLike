"""scheduled_run.sh：管道失败必须跳过导出，并保留原始退出码。"""
import os
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "naming-pipeline" / "scheduled_run.sh"

SHIM = """#!/bin/sh
case "$*" in
  *extract_slim*)
    echo "slim $*" >> "{log}"
    exit "$(cat {slim_rc})"
    ;;
  *)
    echo "pipeline $*" >> "{log}"
    exit "$(cat {pipeline_rc})"
    ;;
esac
"""


@pytest.fixture
def harness(tmp_path):
    pipeline_dir = tmp_path / "naming-pipeline"
    (pipeline_dir / "output").mkdir(parents=True)
    bin_dir = pipeline_dir / ".venv" / "bin"
    bin_dir.mkdir(parents=True)
    (pipeline_dir / "pipeline_rc").write_text("0")
    (pipeline_dir / "slim_rc").write_text("0")
    log = tmp_path / "calls.log"
    log.write_text("")
    shim = bin_dir / "python"
    shim.write_text(SHIM.format(log=log, pipeline_rc=pipeline_dir / "pipeline_rc",
                                slim_rc=pipeline_dir / "slim_rc"))
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    script = pipeline_dir / "scheduled_run.sh"
    script.write_bytes(SCRIPT.read_bytes())
    script.chmod(0o755)

    def run(pipeline_rc, slim_rc):
        (pipeline_dir / "pipeline_rc").write_text(str(pipeline_rc))
        (pipeline_dir / "slim_rc").write_text(str(slim_rc))
        proc = subprocess.run(["/bin/zsh", str(script)], capture_output=True,
                              text=True, cwd=str(tmp_path), timeout=60)
        return proc, (pipeline_dir / "cron.log").read_text(), log.read_text()

    return run


def test_pipeline_failure_skips_export_and_keeps_exit_code(harness):
    proc, cron, calls = harness(9, 0)
    assert proc.returncode == 9
    assert "pipeline -m pipeline.run" in calls
    assert "extract_slim" not in calls
    assert "跳过导出" in cron


@pytest.mark.parametrize("pipeline_rc", [1, 2, 127])
def test_each_pipeline_failure_code_is_propagated(harness, pipeline_rc):
    proc, _cron, calls = harness(pipeline_rc, 0)
    assert proc.returncode == pipeline_rc
    assert "extract_slim" not in calls


def test_success_runs_export_then_exits_zero(harness):
    proc, cron, calls = harness(0, 0)
    assert proc.returncode == 0
    lines = calls.strip().splitlines()
    assert lines[0].startswith("pipeline") and lines[1].startswith("slim")
    assert "pipeline_rc=0 slim_rc=0" in cron


def test_export_failure_is_reported(harness):
    proc, cron, calls = harness(0, 3)
    assert proc.returncode == 3
    assert "extract_slim" in calls
    assert "slim_rc=3" in cron
