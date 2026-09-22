import datetime as dt
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pandas as pd
import pytest

from algobot.openalgo_bridge import OpenAlgoClient, OpenAlgoError, fetch_history_range, load_env

KEY = "secret-key-123"

SAMPLE = {"status": "success", "data": [
    {"timestamp": 1743480300, "open": 766.50, "high": 774.00, "low": 763.20, "close": 772.50, "volume": 318625, "oi": 0},
    {"timestamp": 1743480600, "open": 772.45, "high": 774.95, "low": 772.10, "close": 773.20, "volume": 197189, "oi": 0},
    {"timestamp": 1743480900, "open": 773.20, "high": 775.60, "low": 772.60, "close": 775.15, "volume": 227544, "oi": 0},
]}


class Fake:
    """A stand-in for the network. Records every request; answers by path."""

    def __init__(self, responses=None):
        self.calls = []
        self.responses = responses or {}

    def __call__(self, url, body, timeout):
        path = "/" + url.split("/", 3)[3]
        self.calls.append((path, body))
        answer = self.responses.get(path)
        if callable(answer):
            return answer(body)
        return answer if answer is not None else {"status": "success", "data": []}


def client(fake):
    return OpenAlgoClient(api_key=KEY, host="http://localhost:5000", transport=fake)


# ------------------------------------------------------------------ history
def test_history_request_uses_exactly_the_documented_fields():
    fake = Fake({"/api/v1/history": SAMPLE})
    client(fake).history("SBIN", "NSE", "5m", "2025-04-01", "2025-04-08")
    path, body = fake.calls[0]
    assert path == "/api/v1/history"
    # OpenAlgo rejects any other field with HTTP 400, so the request must contain exactly these.
    assert set(body) == {"apikey", "symbol", "exchange", "interval", "start_date", "end_date"}
    assert body["apikey"] == KEY and body["start_date"] == "2025-04-01"


def test_db_source_is_sent_only_when_asked_and_broker_is_refused():
    fake = Fake({"/api/v1/history": SAMPLE})
    c = client(fake)
    c.history("SBIN", "NSE", "5m", "2025-04-01", "2025-04-08", source="db")
    assert fake.calls[0][1]["source"] == "db"
    with pytest.raises(OpenAlgoError, match="source"):
        c.history("SBIN", "NSE", "5m", "2025-04-01", "2025-04-08", source="broker")


def test_history_converts_epoch_seconds_to_india_time_in_our_format():
    df = client(Fake({"/api/v1/history": SAMPLE})).history("SBIN", "NSE", "5m", "2025-04-01", "2025-04-08")
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]     # oi dropped
    assert df.index[0] == pd.Timestamp("2025-04-01 09:35:00") and df.index.tz is None
    assert df.index[1] - df.index[0] == pd.Timedelta(minutes=5)
    assert df["volume"].dtype == float and df.index.name == "datetime"


def test_history_sorts_and_removes_duplicate_candles():
    rows = [SAMPLE["data"][2], SAMPLE["data"][0], SAMPLE["data"][0], SAMPLE["data"][1]]
    df = client(Fake({"/api/v1/history": {"status": "success", "data": rows}})).history(
        "SBIN", "NSE", "5m", "2025-04-01", "2025-04-08")
    assert len(df) == 3 and df.index.is_monotonic_increasing


def test_daily_candles_are_dated_by_day_whatever_the_time_of_day():
    rows = [{"timestamp": 1743445800, "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 5, "oi": 0},   # 00:00 IST
            {"timestamp": 1743532200 + 3600, "open": 10, "high": 12, "low": 9, "close": 11, "volume": 5, "oi": 0}]  # 01:00 IST
    df = client(Fake({"/api/v1/history": {"status": "success", "data": rows}})).history(
        "SBIN", "NSE", "D", "2025-04-01", "2025-04-03")
    assert list(df.index) == [pd.Timestamp("2025-04-01"), pd.Timestamp("2025-04-02")]


def test_bad_arguments_are_refused_before_anything_is_sent():
    fake = Fake()
    c = client(fake)
    with pytest.raises(OpenAlgoError, match="interval"):
        c.history("SBIN", "NSE", "7m", "2025-04-01", "2025-04-08")
    with pytest.raises(OpenAlgoError, match="start date"):
        c.history("SBIN", "NSE", "5m", "01-04-2025", "2025-04-08")
    assert fake.calls == []


def test_openalgo_error_answers_become_readable_errors():
    fake = Fake({"/api/v1/history": {"status": "error", "message": "Download data first using Historify"}})
    with pytest.raises(OpenAlgoError, match="Download data first using Historify"):
        client(fake).history("SBIN", "NSE", "5m", "2025-04-01", "2025-04-08", source="db")


def test_prices_that_fail_the_checks_are_refused():
    bad = {"status": "success", "data": [{"timestamp": 1743480300, "open": 10, "high": 9, "low": 11, "close": 10, "volume": 1, "oi": 0}]}
    with pytest.raises(OpenAlgoError, match="failed the checks"):
        client(Fake({"/api/v1/history": bad})).history("X", "NSE", "5m", "2025-04-01", "2025-04-01")


def test_the_api_key_is_never_shown_in_an_error():
    def leaky(url, body, timeout):
        raise OpenAlgoError(f"Invalid apikey {KEY} for this user")
    c = OpenAlgoClient(api_key=KEY, host="http://localhost:5000", transport=leaky)
    with pytest.raises(OpenAlgoError) as err:
        c.history("SBIN", "NSE", "5m", "2025-04-01", "2025-04-08")
    assert KEY not in str(err.value) and "***" in str(err.value)
    fake = Fake({"/api/v1/symbol": {"status": "error", "message": f"key {KEY} unknown"}})
    with pytest.raises(OpenAlgoError) as err2:
        client(fake).symbol_info("NIFTY", "NSE_INDEX")
    assert KEY not in str(err2.value)


def test_a_missing_key_is_explained(monkeypatch):
    monkeypatch.delenv("OPENALGO_API_KEY", raising=False)
    with pytest.raises(OpenAlgoError, match=".env"):
        OpenAlgoClient(transport=Fake())


# ------------------------------------------------------------------ chunking
def test_long_ranges_are_fetched_in_pieces_and_stitched(monkeypatch):
    def answer(body):
        start = pd.Timestamp(body["start_date"])
        ts = int((start + pd.Timedelta(hours=4)).timestamp())           # one candle per requested window
        return {"status": "success", "data": [{"timestamp": ts, "open": 1, "high": 2, "low": 1, "close": 1.5, "volume": 1, "oi": 0}]}
    fake = Fake({"/api/v1/history": answer})
    pauses = []
    df = fetch_history_range(client(fake), "NIFTY", "NSE_INDEX", "5m", "2026-08-01", "2026-08-25", chunk_days=10,
                             sleep=pauses.append)
    windows = [(b["start_date"], b["end_date"]) for _, b in fake.calls]
    assert windows == [("2026-08-01", "2026-08-10"), ("2026-08-11", "2026-08-20"), ("2026-08-21", "2026-08-25")]
    assert len(pauses) == 2 and len(df) == 3 and df.index.is_monotonic_increasing


def test_default_piece_size_depends_on_the_interval():
    fake = Fake({"/api/v1/history": SAMPLE})
    fetch_history_range(client(fake), "NIFTY", "NSE_INDEX", "5m", "2026-01-01", "2026-03-01", sleep=lambda s: None)
    first = fake.calls[0][1]
    assert dt.date.fromisoformat(first["end_date"]) - dt.date.fromisoformat(first["start_date"]) == dt.timedelta(days=24)
    fake2 = Fake({"/api/v1/history": SAMPLE})
    fetch_history_range(client(fake2), "NIFTY", "NSE_INDEX", "D", "2025-01-01", "2026-03-01", sleep=lambda s: None)
    assert len(fake2.calls) == 2                                          # 365-day pieces


def test_empty_answer_explains_the_history_limit_and_bad_ranges_are_refused():
    with pytest.raises(OpenAlgoError, match="30 to 90 days"):
        fetch_history_range(client(Fake()), "NIFTY", "NSE_INDEX", "5m", "2026-01-01", "2026-01-05", sleep=lambda s: None)
    with pytest.raises(OpenAlgoError, match="before the start"):
        fetch_history_range(client(Fake()), "NIFTY", "NSE_INDEX", "5m", "2026-02-01", "2026-01-05")


# ------------------------------------------------------ symbol and notifications
def test_lot_size_comes_from_openalgo_and_the_request_is_exact():
    fake = Fake({"/api/v1/symbol": {"status": "success", "data": {"symbol": "NIFTY30DEC25FUT", "lotsize": 65}}})
    assert client(fake).lot_size("NIFTY30DEC25FUT", "NFO") == 65
    assert set(fake.calls[0][1]) == {"apikey", "symbol", "exchange"}
    bad = Fake({"/api/v1/symbol": {"status": "success", "data": {"symbol": "X"}}})
    with pytest.raises(OpenAlgoError, match="lot size"):
        client(bad).lot_size("X", "NFO")


def test_telegram_notify_sends_the_documented_fields_and_needs_both_arguments():
    fake = Fake({"/api/v1/telegram/notify": {"status": "success", "message": "queued"}})
    c = client(fake)
    c.telegram_notify("brother", "hello")
    path, body = fake.calls[0]
    assert path == "/api/v1/telegram/notify"
    assert body == {"apikey": KEY, "username": "brother", "message": "hello", "wait_for_delivery": False}
    with pytest.raises(OpenAlgoError):
        c.telegram_notify("", "hello")


def test_the_client_has_no_way_to_place_an_order():
    names = [n for n in dir(OpenAlgoClient) if not n.startswith("_")]
    assert not any(word in n.lower() for n in names for word in ("order", "buy", "sell", "place", "cancel", "modify"))


# -------------------------------------------------------- .env handling
def test_env_file_is_loaded_without_overriding_real_environment(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text('# comment\nOPENALGO_HOST="http://10.0.0.5:5000"\nOPENALGO_API_KEY=abc\n\nBROKEN LINE\n')
    monkeypatch.delenv("OPENALGO_HOST", raising=False)
    monkeypatch.setenv("OPENALGO_API_KEY", "already-set")
    load_env(str(env))
    import os
    assert os.environ["OPENALGO_HOST"] == "http://10.0.0.5:5000" and os.environ["OPENALGO_API_KEY"] == "already-set"
    load_env(str(tmp_path / "missing.env"))                                # a missing file is fine


# --------------------------------- the real network path, against a local fake OpenAlgo
class _Handler(BaseHTTPRequestHandler):
    seen = []

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _Handler.seen.append((self.path, self.headers.get("Content-Type"), body))
        if body.get("apikey") != KEY:
            code, payload = 403, {"status": "error", "message": "Invalid openalgo apikey"}
        elif self.path == "/api/v1/history":
            code, payload = 200, SAMPLE
        else:
            code, payload = 404, {"status": "error", "message": "no such endpoint"}
        raw = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        pass


@pytest.fixture()
def fake_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _Handler.seen.clear()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_real_http_round_trip(fake_server):
    df = OpenAlgoClient(api_key=KEY, host=fake_server).history("SBIN", "NSE", "5m", "2025-04-01", "2025-04-08")
    assert len(df) == 3
    path, content_type, body = _Handler.seen[0]
    assert path == "/api/v1/history" and content_type == "application/json" and body["symbol"] == "SBIN"


def test_real_http_errors_are_friendly_and_do_not_leak_the_key(fake_server):
    with pytest.raises(OpenAlgoError, match="HTTP 403.*Invalid openalgo apikey"):
        OpenAlgoClient(api_key="wrong-key", host=fake_server).history("SBIN", "NSE", "5m", "2025-04-01", "2025-04-08")
    with pytest.raises(OpenAlgoError, match="HTTP 404"):
        OpenAlgoClient(api_key=KEY, host=fake_server).symbol_info("NIFTY", "NSE_INDEX")


def test_openalgo_not_running_is_explained():
    with pytest.raises(OpenAlgoError, match="Is OpenAlgo running"):
        OpenAlgoClient(api_key=KEY, host="http://127.0.0.1:9").history("SBIN", "NSE", "5m", "2025-04-01", "2025-04-08")
