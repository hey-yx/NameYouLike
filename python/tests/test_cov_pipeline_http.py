"""pipeline.http 访问层的行为测试（假会话，不联网）。

覆盖：惰性会话构建（UA 注入）、限速、429 长等待重试、非 200 与异常退避、
耗尽重试后的 RuntimeError、sleep_between。
"""
import sys
import time
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "naming-pipeline"))

from pipeline import http as http_mod  # noqa: E402


class FakeResp:
    def __init__(self, status=200, text="{}", json_data=None):
        self.url = "https://example.com"
        self.status_code = status
        self.text = text
        self._json = json_data if json_data is not None else {}

    def iter_content(self, chunk_size):
        yield self.text.encode("utf-8")

    def close(self):
        pass


class FakeSession:
    """按序返回预置响应；记录每次调用的 (url, params)。"""

    def __init__(self, responses=None, error=None):
        self.responses = list(responses or [])
        self.error = error
        self.calls = []
        self.headers = {}

    def get(self, url, params=None, timeout=None, stream=True):
        self.calls.append((url, params))
        if self.error is not None:
            raise self.error
        return self.responses.pop(0)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """测试不真睡；记录 sleep 时长供断言。"""
    slept = []
    monkeypatch.setattr(http_mod.time, "sleep", lambda s: slept.append(s))
    monkeypatch.setattr(http_mod, "_last_call_ts", 0.0)
    return slept


def test_get_session_lazy_builds_session_with_ua(monkeypatch):
    built = []

    class _Sess:
        def __init__(self):
            self.headers = {}
            built.append(self)

    fake_requests = types.ModuleType("requests")
    fake_requests.Session = _Sess
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    monkeypatch.setattr(http_mod, "_session", None)

    s1 = http_mod._get_session()
    assert built == [s1]
    assert s1.headers["User-Agent"] == http_mod.UA
    assert "application/json" in s1.headers["Accept"]
    # 二次调用复用缓存会话
    assert http_mod._get_session() is s1
    assert len(built) == 1


def test_get_json_success_returns_parsed(monkeypatch):
    session = FakeSession(responses=[FakeResp(200, '{"a": 1}', {"a": 1})])
    monkeypatch.setattr(http_mod, "_get_session", lambda: session)

    out = http_mod.get_json("https://example.com/x", params={"q": "1"})
    assert out == {"a": 1}
    assert session.calls == [("https://example.com/x", {"q": "1"})]


def test_throttle_sleeps_only_when_too_fast(no_sleep):
    http_mod._last_call_ts = time.time()
    http_mod._throttle(0.5)
    assert len(no_sleep) == 1 and 0 < no_sleep[0] <= 0.5

    no_sleep.clear()
    http_mod._throttle(0)  # 间隔要求为 0 → 不睡
    assert no_sleep == []


def test_get_json_429_waits_long_then_succeeds(monkeypatch, no_sleep):
    session = FakeSession(responses=[
        FakeResp(429, "rate"),
        FakeResp(200, '{"ok": 1}', {"ok": 1}),
    ])
    monkeypatch.setattr(http_mod, "_get_session", lambda: session)

    out = http_mod.get_json("https://example.com/r", retries=2, wait_429=15.0)
    assert out == {"ok": 1}
    assert 15.0 in no_sleep  # 429 走长等待


def test_get_json_non_200_retries_with_backoff_then_raises(monkeypatch, no_sleep):
    session = FakeSession(responses=[FakeResp(500, "boom"), FakeResp(502, "bad")])
    monkeypatch.setattr(http_mod, "_get_session", lambda: session)

    with pytest.raises(RuntimeError) as ei:
        http_mod.get_json("https://example.com/e", retries=2, backoff=3.0)
    msg = str(ei.value)
    assert "GET failed after 2 tries" in msg
    assert "HTTP 502" in msg and "body_len=3" in msg
    assert 3.0 in no_sleep  # i=0 的退避


def test_get_json_transport_exception_retries(monkeypatch):
    session = FakeSession(error=OSError("net down"))
    monkeypatch.setattr(http_mod, "_get_session", lambda: session)

    with pytest.raises(RuntimeError) as ei:
        http_mod.get_json("https://example.com/x", retries=1)
    assert "net down" in str(ei.value)
    assert len(session.calls) == 1


def test_get_json_empty_body_treated_as_failure(monkeypatch):
    session = FakeSession(responses=[FakeResp(200, "   ")])
    monkeypatch.setattr(http_mod, "_get_session", lambda: session)

    with pytest.raises(RuntimeError) as ei:
        http_mod.get_json("https://example.com/x", retries=1)
    assert "HTTP 200" in str(ei.value)


def test_sleep_between(monkeypatch, no_sleep):
    http_mod.sleep_between(0.25)
    assert no_sleep == [0.25]
