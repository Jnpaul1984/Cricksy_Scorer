import json
import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTI = ROOT / "artifacts"
ARTI.mkdir(exist_ok=True)


def write_env():
    env = {
        k: v
        for k, v in os.environ.items()
        if k in ("API_BASE", "GITHUB_SHA", "GITHUB_REF", "GITHUB_RUN_ID")
    }
    (ARTI / "env.json").write_text(json.dumps(env, indent=2), encoding="utf-8")


def copy_trace():
    src = ROOT / "artifacts" / "http_trace.jsonl"
    if src.exists():
        # already in place (tests wrote here)
        return
    # If tests didn't write trace, create placeholder
    src.write_text("", encoding="utf-8")


def docker_logs():
    # Optional: if docker available and service name is 'api'
    try:
        out = subprocess.check_output(["docker", "compose", "logs", "api"], text=True)
        (ARTI / "backend_logs.txt").write_text(out, encoding="utf-8")
    except Exception:
        pass


if __name__ == "__main__":
    write_env()
    copy_trace()
    docker_logs()
    print("Artifacts collected into ./artifacts")
