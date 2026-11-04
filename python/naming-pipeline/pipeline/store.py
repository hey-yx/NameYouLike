"""增量状态与语料存储。

- corpus.jsonl: 追加式清洗后语料（全量事实源；统计每次全量重算，避免增量漂移）
- state.json:   版本号 / 水位 / 运行历史
- .lock:        互斥锁（cron 场景防止并发跑）
"""
from __future__ import annotations

import fcntl
import json
import os
import time
from typing import IO, Optional


class LockError(RuntimeError):
    pass


class PipelineStore:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.corpus_path = os.path.join(data_dir, "corpus.jsonl")
        self.state_path = os.path.join(data_dir, "state.json")
        self.lock_path = os.path.join(data_dir, ".lock")
        self.raw_dir = os.path.join(data_dir, "raw")
        self._lock_file: Optional[IO[str]] = None
        os.makedirs(self.raw_dir, exist_ok=True)

    # ---- 锁：内核级 flock，拿不到 fd 才算冲突 -----------
    # 旧实现「检查 exists → 删陈锁 → 创建文件」有两个窗口：两个进程同时
    # 通过检查会双双持锁；按 mtime 偷锁还会删掉活着的锁。flock 绑定 fd，
    # 进程退出即释放，锁文件本身不必删除（删除反而制造新的竞态）。
    def acquire_lock(self) -> None:
        if self._lock_file is not None:
            return
        handle = open(self.lock_path, "a+", encoding="utf-8")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            handle.close()
            raise LockError(f"另一管道实例正在运行: {self.lock_path}") from exc
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps({"pid": os.getpid(), "at": time.time()}))
        handle.flush()
        self._lock_file = handle

    def release_lock(self) -> None:
        handle = self._lock_file
        if handle is None:
            return
        self._lock_file = None
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

    # ---- state
    def load_state(self) -> dict:
        if not os.path.exists(self.state_path):
            return {"schema": 1, "version_seq": 0, "runs": [], "watermarks": {}}
        with open(self.state_path, encoding="utf-8") as f:
            return json.load(f)

    def save_state(self, state: dict) -> None:
        state["runs"] = state.get("runs", [])[-30:]
        tmp = self.state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.state_path)

    # ---- corpus
    def load_corpus(self) -> list[dict]:
        if not os.path.exists(self.corpus_path):
            return []
        out = []
        with open(self.corpus_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return out

    def append_records(self, records: list[dict]) -> None:
        if not records:
            return
        with open(self.corpus_path, "a", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def save_raw_snapshot(self, source: str, records: list[dict]) -> Optional[str]:
        """每次运行保存原始抓取快照（审计用，按 源-日期 命名）。"""
        if not records:
            return None
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.raw_dir, f"{source}_{ts}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return path
