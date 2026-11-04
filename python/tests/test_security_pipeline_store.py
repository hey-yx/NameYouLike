"""PipelineStore：跨进程 flock 互斥、状态原子写。"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

NP_DIR = Path(__file__).resolve().parent.parent / "naming-pipeline"
sys.path.insert(0, str(NP_DIR))

from pipeline.store import LockError, PipelineStore  # noqa: E402

HOLDER = """
import sys, time
sys.path.insert(0, {np_dir!r})
from pipeline.store import PipelineStore
store = PipelineStore({data!r})
store.acquire_lock()
print("locked", flush=True)
time.sleep(30)
"""


def test_lock_is_held_across_processes(tmp_path):
    data = tmp_path / "data"
    code = HOLDER.format(np_dir=str(NP_DIR), data=str(data))
    holder = subprocess.Popen([sys.executable, "-c", code],
                              stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "locked"
        with pytest.raises(LockError):
            PipelineStore(str(data)).acquire_lock()
    finally:
        holder.kill()
        holder.wait(timeout=10)

    # 持锁进程退出后锁自动释放（不依赖删除锁文件）
    store = PipelineStore(str(data))
    store.acquire_lock()
    store.release_lock()


def test_lock_metadata_records_pid(tmp_path):
    data = tmp_path / "data"
    store = PipelineStore(str(data))
    store.acquire_lock()
    try:
        meta = json.loads(Path(store.lock_path).read_text(encoding="utf-8"))
        assert meta["pid"] > 0
    finally:
        store.release_lock()
    assert Path(store.lock_path).exists()      # 锁文件保留，flock 已释放


def test_state_write_keeps_previous_file_on_serialization_error(tmp_path):
    data = tmp_path / "data"
    store = PipelineStore(str(data))
    store.save_state({"schema": 1, "version_seq": 2, "runs": []})
    before = Path(store.state_path).read_text(encoding="utf-8")
    with pytest.raises(TypeError):
        store.save_state({"schema": 1, "bad": object()})
    assert Path(store.state_path).read_text(encoding="utf-8") == before


def test_state_trims_run_history(tmp_path):
    data = tmp_path / "data"
    store = PipelineStore(str(data))
    store.save_state({"schema": 1, "runs": [{"n": i} for i in range(50)]})
    assert len(json.loads(Path(store.state_path).read_text())["runs"]) == 30


def test_append_records_is_newline_terminated(tmp_path):
    data = tmp_path / "data"
    store = PipelineStore(str(data))
    store.append_records([{"record_id": "1"}, {"record_id": "2"}])
    text = Path(store.corpus_path).read_text(encoding="utf-8")
    assert text == '{"record_id": "1"}\n{"record_id": "2"}\n'
    assert [r["record_id"] for r in store.load_corpus()] == ["1", "2"]


def test_acquire_lock_is_idempotent(tmp_path):
    store = PipelineStore(str(tmp_path))
    store.acquire_lock()
    store.acquire_lock()                       # 已持锁：直接返回
    store.release_lock()
    store.release_lock()


def test_load_state_reads_existing_file(tmp_path):
    store = PipelineStore(str(tmp_path))
    Path(store.state_path).write_text('{"schema": 1, "version_seq": 7}', encoding="utf-8")
    assert store.load_state()["version_seq"] == 7
    assert store.load_state.__self__ is store
