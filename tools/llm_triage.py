import os
import json
import pathlib
import sys
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTI = ROOT / "artifacts"
CONTRACT = ROOT / "backend" / "api_contract.md"

PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()  # "openai" or "anthropic"
MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")  # override in CI if desired


def read_file(p: str) -> str:
    try:
        return pathlib.Path(p).read_text(encoding="utf-8")
    except Exception:
        return ""


def prompt_message() -> str:
    contract = read_file(CONTRACT)

    # Read artifacts used in the prompt (limit shown content with slicing below)
    http_trace = read_file(ARTI / "http_trace.jsonl")
    backend_logs = read_file(ARTI / "backend_logs.txt")

    # Optional context (kept if you want to expand the prompt later)
    _sysinfo = {
        "api_base": os.getenv("API_BASE", ""),
        "sha": os.getenv("GITHUB_SHA", ""),
    }

    return f"""
You are a senior backend+tests engineer. Diagnose failing tests for a cricket scoring API and propose a minimal patch.

# API CONTRACT (must remain true)
{contract}

# FAILURE BUNDLE
- http_trace.jsonl (client->server traces):
{http_trace[:6000]}

- backend_logs.txt:
{backend_logs[:6000]}

# TASKS
1) Identify the root cause (schema mismatch, innings state, finalize endpoint, etc.).
2) Propose a minimal patch **as a unified diff** against the repository (modify tests or small backend handler if obvious).
3) Keep the API contract intact. If you add a finalize endpoint route, document it in api_contract.md and update tests accordingly.
4) Provide a short summary.md explaining the change and why it fixes the failure.

Return strictly this JSON:
{{
  "summary_md": "<markdown>",
  "diff": "<unified diff patch>"
}}
""".strip()


def call_openai(prompt: str):
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content


def call_anthropic(prompt: str):
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model=os.getenv("LLM_MODEL", "claude-3-sonnet-20240229"),
        max_tokens=4000,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def parse_json_block(text: str):
    # naive parse for a single JSON object in the reply
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError("LLM did not return JSON")
    return json.loads(text[start : end + 1])


def apply_patch(diff_text: str):
    patch = ARTI / "patch.diff"
    patch.write_text(diff_text, encoding="utf-8")
    # Apply patch
    p = subprocess.run(["git", "apply", "--whitespace=fix", str(patch)], cwd=str(ROOT))
    return p.returncode == 0


if __name__ == "__main__":
    prompt = prompt_message()
    if PROVIDER == "openai":
        raw = call_openai(prompt)
    else:
        raw = call_anthropic(prompt)

    out = parse_json_block(raw)
    (ARTI / "summary.md").write_text(out.get("summary_md", ""), encoding="utf-8")
    diff = out.get("diff", "")
    ok = False
    if diff.strip():
        ok = apply_patch(diff)

    # If patch applied, leave modified files staged for the PR step.
    if ok:
        print("Patch applied. Ready to create PR.")
        sys.exit(0)
    else:
        print("No patch applied (diff empty or failed).")
        sys.exit(0)  # don’t fail the job; we still want logs & comments