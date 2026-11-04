"""HTTP security regressions: boundary responses only, never network."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "naming-pipeline"))
from pipeline import http


class Response:
    status_code = 200
    headers = {}
    url = "https://example.invalid"

    def __init__(self, chunks=(b'{}',), status=200):
        self.chunks = chunks
        self.status_code = status
        self.closed = False

    def iter_content(self, chunk_size):
        yield from self.chunks

    def close(self):
        self.closed = True


@pytest.fixture
def use_response(monkeypatch):
    def use(resp):
        class Session:
            def get(self, url, **kwargs):
                return resp
        monkeypatch.setattr(http, "_get_session", Session)
        return resp
    return use


@pytest.mark.parametrize("chunks,status,raises", [
    ((b'{}',), 200, False),
    ((b'bad json',), 200, True),
    ((b'error',), 500, True),
    ((b'x' * 9,), 200, True),
])
def test_response_is_closed_on_every_exit(monkeypatch, use_response, chunks, status, raises):
    monkeypatch.setattr(http, "MAX_RESPONSE_BYTES", 8)
    resp = use_response(Response(chunks, status))
    if raises:
        with pytest.raises(RuntimeError):
            http.get_json(resp.url, retries=1, interval=0)
    else:
        assert http.get_json(resp.url, retries=1, interval=0) == {}
    assert resp.closed


def test_type_error_does_not_issue_duplicate_request(monkeypatch):
    calls = []
    class Session:
        def get(self, url, **kwargs):
            calls.append(kwargs)
            raise TypeError("transport bug")
    monkeypatch.setattr(http, "_get_session", Session)
    with pytest.raises(RuntimeError, match="transport bug"):
        http.get_json("https://example.invalid", retries=1, interval=0)
    assert len(calls) == 1


@pytest.mark.parametrize("phase", ["request", "body", "throttle", "backoff", "429", "parse"])
def test_total_budget_interrupts_each_blocking_phase(monkeypatch, phase):
    import json
    import time
    duration = 0.8
    budget = 0.15
    resp = Response(status=429 if phase == "429" else 500 if phase == "backoff" else 200)
    class Session:
        def get(self, url, **kwargs):
            if phase == "request":
                time.sleep(duration)
            return resp
    if phase == "body":
        def slow_body(chunk_size):
            time.sleep(duration)
            yield b'{}'
        resp.iter_content = slow_body
    if phase == "parse":
        original = json.loads
        def slow_parse(body):
            time.sleep(duration)
            return original(body)
        monkeypatch.setattr(json, "loads", slow_parse)
    monkeypatch.setattr(http, "_get_session", Session)
    monkeypatch.setattr(http, "_last_call_ts", time.time())
    start = time.monotonic()
    with pytest.raises(RuntimeError, match="总时长预算"):
        http.get_json(resp.url, retries=2, interval=duration if phase == "throttle" else 0,
                      backoff=duration, wait_429=duration, total_timeout=budget)
    elapsed = time.monotonic() - start
    assert elapsed < duration / 2, elapsed
    if phase not in ("request", "throttle"):
        assert resp.closed



def test_declared_length_over_limit_rejected_before_reading(monkeypatch, use_response):
    resp = Response()
    resp.headers = {"content-length": str(http.MAX_RESPONSE_BYTES + 1)}
    use_response(resp)
    with pytest.raises(RuntimeError, match="Content-Length"):
        http.get_json(resp.url, retries=1, interval=0)
    assert resp.closed


def test_content_length_header_edge_values(monkeypatch):
    assert http._declared_length(Response()) is None                    # 无 header
    assert http._declared_length(type("R", (), {"headers": object()})()) is None  # 不支持 get
    assert http._declared_length(type("R", (), {"headers": {"content-length": "x"}})()) is None


def test_empty_chunks_are_skipped(monkeypatch, use_response):
    resp = use_response(Response((b"", b'{"a": 1}')))
    assert http.get_json(resp.url, retries=1, interval=0) == {"a": 1}


def test_https_to_http_downgrade_is_rejected(monkeypatch, use_response):
    resp = use_response(Response())
    resp.url = "http://example.invalid/downgraded"
    with pytest.raises(RuntimeError, match="降级"):
        http.get_json("https://example.invalid", retries=1, interval=0)


def test_existing_alarm_blocks_budget(monkeypatch):
    import signal
    signal.setitimer(signal.ITIMER_REAL, 5)
    try:
        with pytest.raises(RuntimeError, match="不能覆盖已有计时器"):
            http.get_json("https://example.invalid", retries=1, interval=0, total_timeout=1)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def test_expired_deadline_at_loop_head_stops_before_request(monkeypatch):
    calls = []
    class Session:
        def get(self, url, **kwargs):
            calls.append(url)
            return Response()
    monkeypatch.setattr(http, "_get_session", Session)
    with pytest.raises(RuntimeError, match="总时长预算"):
        http._get_json("https://example.invalid", retries=2, interval=0, total_timeout=-1)
    assert calls == []


def test_zero_or_negative_budget_raises_immediately(monkeypatch):
    with pytest.raises(RuntimeError, match="总时长预算"):
        http.get_json("https://example.invalid", retries=1, interval=0, total_timeout=0)


def test_budget_exhausted_between_throttle_and_request(monkeypatch):
    ticks = iter([0.0, 0.0, 10.0])          # deadline → 循环头 → 计算剩余时间
    monkeypatch.setattr(http.time, "monotonic", lambda: next(ticks))
    calls = []
    class Session:
        def get(self, url, **kwargs):
            calls.append(url)
            return Response()
    monkeypatch.setattr(http, "_get_session", Session)
    with pytest.raises(RuntimeError, match="总时长预算"):
        http.get_json("https://example.invalid", retries=1, interval=0, total_timeout=5)
    assert calls == []


def test_budget_rejects_non_main_thread(monkeypatch):
    import threading
    errors = []

    def worker():
        try:
            http.get_json("https://example.invalid", retries=1, interval=0, total_timeout=1)
        except RuntimeError as exc:
            errors.append(str(exc))

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout=10)
    assert errors and "主线程" in errors[0]
