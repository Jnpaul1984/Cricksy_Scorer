# From the repo root (Cricksy_Scorer)

import json, time, os, pathlib, httpx
from urllib.parse import urlsplit

_USE_INPROC = os.getenv("CRICKSY_IN_MEMORY_DB") == "1"
if _USE_INPROC:
    from fastapi.testclient import TestClient
    import backend.main as main

    _local_client = TestClient(main.fastapi_app)

# artifacts folder at repo root: Cricksy_Scorer/artifacts
ARTI_DIR = pathlib.Path(__file__).resolve().parents[2] / "artifacts"
ARTI_DIR.mkdir(parents=True, exist_ok=True)
TRACE_FILE = ARTI_DIR / "http_trace.jsonl"

def traced_request(method: str, url: str, **kw) -> httpx.Response:
    """
    Wrapper around httpx.request that logs request/response into artifacts/http_trace.jsonl
    """
    t0 = time.time()
    timeout = kw.pop("timeout", 15)

    if _USE_INPROC:
        parsed = urlsplit(url)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        resp = _local_client.request(method, path, timeout=timeout, **kw)
    else:
        resp = httpx.request(method, url, timeout=timeout, **kw)
    t1 = time.time()

    try:
        body = kw.get("json", None)
        rec = {
            "ts": t0,
            "dur_ms": int((t1 - t0) * 1000),
            "method": method,
            "url": url,
            "status": resp.status_code,
            "req_json": body,
            "resp_text": (resp.text or "")[:2000],
        }
        with TRACE_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        # never break tests because of tracing
        pass

    return resp



