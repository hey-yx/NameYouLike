"""统一 HTTP 访问层：UA、礼貌限速、重试退避。所有外部抓取必须走这里。

``requests`` 为惰性依赖：只在真正联网抓取时才需要安装。``--offline`` /
``--rebuild-stats`` 等离线子命令与测试在没装 requests 的环境也能导入本模块。
"""
from __future__ import annotations

import signal
import threading
import time
from contextlib import contextmanager
from typing import Any, Optional

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)

_session = None
_last_call_ts = 0.0
MIN_INTERVAL = 0.35  # 两次请求之间的最小间隔（秒），避免触发限流
MAX_RESPONSE_BYTES = 8 * 1024 * 1024  # 单个响应上限：连抓取带解析都不该吃这么多
DEFAULT_TOTAL_TIMEOUT = 180.0  # 一次 get_json 的总时长预算（含重试与退避）

_CHUNK = 64 * 1024


def _get_session():
    """惰性构建 requests 会话（首次联网时才导入 requests）。"""
    global _session
    if _session is None:
        import requests
        _session = requests.Session()
        _session.headers.update({"User-Agent": UA, "Accept": "application/json,text/plain,*/*"})
    return _session


def _throttle(interval: float) -> None:
    global _last_call_ts
    wait = _last_call_ts + interval - time.time()
    if wait > 0:
        time.sleep(wait)
    _last_call_ts = time.time()


def _declared_length(resp: Any) -> Optional[int]:
    headers = getattr(resp, "headers", None)
    if not headers:
        return None
    try:
        raw = headers.get("content-length")
    except AttributeError:
        return None
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _read_body(resp: Any) -> str:
    """按块读响应体并在超限时立即中止，避免把超大响应整个读进内存。"""
    declared = _declared_length(resp)
    if declared is not None and declared > MAX_RESPONSE_BYTES:
        raise RuntimeError(f"响应过大（Content-Length {declared}）")
    chunks, size = [], 0
    for chunk in resp.iter_content(_CHUNK):
        if not chunk:
            continue
        size += len(chunk)
        if size > MAX_RESPONSE_BYTES:
            raise RuntimeError(f"响应过大（超过 {MAX_RESPONSE_BYTES} 字节）")
        chunks.append(chunk)
    return b"".join(chunks).decode("utf-8", "replace")


class _BudgetExpired(Exception):
    pass


@contextmanager
def _total_budget(seconds: float):
    """POSIX 主线程硬期限，覆盖慢速分块读取、DNS、重试等待及 JSON 解析。

    此管道只串行运行；非主线程或已有计时器时拒绝启动请求，避免留下失控工作。
    不使用超时线程：线程超时不会取消底层请求。
    """
    if seconds <= 0:
        raise _BudgetExpired()
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("HTTP 总时长预算只能在主线程使用（信号计时器）")
    if signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0):
        raise RuntimeError("HTTP 总时长预算不能覆盖已有计时器")
    previous = signal.getsignal(signal.SIGALRM)

    def expire(signum, frame):
        raise _BudgetExpired()

    signal.signal(signal.SIGALRM, expire)
    try:
        signal.setitimer(signal.ITIMER_REAL, seconds)
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def get_json(url: str, params: Optional[dict] = None, timeout: float = 25,
             retries: int = 3, backoff: float = 3.0, interval: float = MIN_INTERVAL,
             wait_429: float = 20.0, total_timeout: float = DEFAULT_TOTAL_TIMEOUT) -> Any:
    """串行 CLI 的有界 GET；包含读取与退避的总期限，失败抛 RuntimeError。"""
    try:
        with _total_budget(total_timeout):
            return _get_json(url, params, timeout, retries, backoff, interval, wait_429, total_timeout)
    except _BudgetExpired as exc:
        raise RuntimeError(f"超出总时长预算 {total_timeout}s") from exc


def _get_json(url: str, params: Optional[dict] = None, timeout: float = 25,
             retries: int = 3, backoff: float = 3.0, interval: float = MIN_INTERVAL,
             wait_429: float = 20.0, total_timeout: float = DEFAULT_TOTAL_TIMEOUT) -> Any:
    """GET 并解析 JSON；带限速、退避重试、响应体积上限与总时长预算。失败抛 RuntimeError。"""
    import json as _json

    deadline = time.monotonic() + total_timeout
    last_err: Exception = RuntimeError("no attempt")
    for i in range(retries):
        if time.monotonic() >= deadline:
            last_err = RuntimeError(f"超出总时长预算 {total_timeout}s")
            break
        _throttle(interval)
        resp = None
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise _BudgetExpired()
            resp = _get_session().get(url, params=params, timeout=min(timeout, remaining), stream=True)
            final_url = resp.url
            if url.startswith("https:") and final_url.startswith("http:"):
                raise RuntimeError("上游把 HTTPS 降级成了 HTTP，已拒绝")
            body = _read_body(resp)
            if resp.status_code == 200 and body.strip():
                return _json.loads(body)
            last_err = (
                RuntimeError("HTTP 429 rate-limited") if resp.status_code == 429
                else RuntimeError(f"HTTP {resp.status_code}, body_len={len(body)}")
            )
            if resp.status_code == 429:
                time.sleep(wait_429 * (i + 1))
                continue
        except _BudgetExpired:
            raise
        except Exception as exc:  # noqa: BLE001
            last_err = exc
        finally:
            if resp is not None:
                resp.close()
        if i < retries - 1:
            time.sleep(backoff * (i + 1))
    raise RuntimeError(f"GET failed after {retries} tries: {url} :: {last_err}")


def sleep_between(seconds: float) -> None:
    time.sleep(seconds)
