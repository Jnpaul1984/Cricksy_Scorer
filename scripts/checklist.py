#!/usr/bin/env python3
"""
Cricksy Scorer MCP Checklist CLI

Usage:
  python scripts/checklist.py status [--week N]
  python scripts/checklist.py next [--count N]
  python scripts/checklist.py start <id>
  python scripts/checklist.py done <id> --by "<name>" --files "<comma-list>"
  python scripts/checklist.py verify <id>

Examples:
  python scripts/checklist.py status
  python scripts/checklist.py status --week 5
  python scripts/checklist.py next --count 5
  python scripts/checklist.py start week5-ai-win-probability
  python scripts/checklist.py done week5-ai-win-probability \
    --by "copilot" --files "backend/routes/ai.py"
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, UTC
from typing import Any
import subprocess

# Paths
REPO_ROOT = Path(__file__).parent.parent
MCP_DIR = REPO_ROOT / ".mcp"
CHECKLIST_YAML = MCP_DIR / "checklist.yaml"
VERIFICATION_JSON = MCP_DIR / "verification.json"


def load_yaml_simple(path: Path) -> list[dict[str, Any]]:
    """
    Simple YAML parser (not using pyyaml to avoid dependency).
    Returns list of checklist items.
    """
    import re

    content = path.read_text(encoding="utf-8")
    items = []
    current_item = None
    in_list = False
    list_key = None

    for line in content.split("\n"):
        # Item start (- id: ...)
        if line.startswith("- id:"):
            if current_item:
                items.append(current_item)
            current_item = {}
            in_list = False
            match = re.match(r"\s*-\s+id:\s+(.+)", line)
            if match:
                current_item["id"] = match.group(1).strip()

        elif current_item is not None:
            # Simple key-value (indented)
            if line.strip() and not line.startswith("  - "):
                match = re.match(r"\s+(\w+):\s*(.+)", line)
                if match:
                    key = match.group(1).strip()
                    value = match.group(2).strip()

                    # Handle booleans, nulls, numbers
                    if value.lower() == "true":
                        value = True
                    elif value.lower() == "false":
                        value = False
                    elif value.lower() == "null":
                        value = None
                    elif value.isdigit():
                        value = int(value)

                    current_item[key] = value
                    in_list = False
                    list_key = None

            # List items (  - )
            elif line.startswith("  - "):
                if not in_list:
                    # Start new list
                    list_content = line.strip()[2:].strip()
                    # Detect list key from context
                    # (acceptance_criteria, verification_commands, etc.)
                    # Look back in current_item
                    for k in [
                        "acceptance_criteria",
                        "verification_commands",
                        "manual_checks",
                        "files_touched",
                    ]:
                        if k not in current_item:
                            list_key = k
                            current_item[list_key] = []
                            break
                    in_list = True

                if list_key:
                    list_content = line.strip()[2:].strip()
                    current_item[list_key].append(list_content)

    if current_item:
        items.append(current_item)

    return items


def load_verification() -> dict[str, dict[str, Any]]:
    """Load verification.json if exists."""
    if VERIFICATION_JSON.exists():
        return json.loads(VERIFICATION_JSON.read_text())
    return {}


def save_verification(data: dict[str, dict[str, Any]]):
    """Save verification.json."""
    VERIFICATION_JSON.write_text(json.dumps(data, indent=2))


def cmd_status(week: int | None = None):
    """Print checklist status summary."""
    items = load_yaml_simple(CHECKLIST_YAML)

    if week:
        items = [i for i in items if i.get("week") == week]

    total = len(items)
    done = len([i for i in items if i.get("status") == "done"])
    in_progress = len([i for i in items if i.get("status") == "in_progress"])
    todo = len([i for i in items if i.get("status") == "todo"])
    blocked = len([i for i in items if i.get("status") == "blocked"])

    pct = (done / total * 100) if total > 0 else 0

    print("\n" + "=" * 60)
    print(f"{'Checklist Status':^60}")
    print("=" * 60)

    if week:
        print(f"\nWeek {week}:")
    else:
        print("\nOverall:")

    print(f"  Total:        {total}")
    print(f"  Done:         {done} ✅")
    print(f"  In Progress:  {in_progress} 🟡")
    print(f"  Blocked:      {blocked} 🔴")
    print(f"  Todo:         {todo}")
    print(f"  Progress:     {pct:.1f}%")
    print("\n" + "=" * 60)


def cmd_next(count: int = 3):
    """Suggest next items to work on."""
    items = load_yaml_simple(CHECKLIST_YAML)

    # Sort: todo first, then by week
    todo_items = [i for i in items if i.get("status") == "todo"]
    todo_items.sort(key=lambda x: (x.get("week", 999), x.get("id", "")))

    print(f"\n📋 Next {count} items to work on:")
    print("=" * 60)

    for i, item in enumerate(todo_items[:count], 1):
        item_id = item.get("id", "?")
        week = item.get("week", "?")
        title = item.get("title", "?")
        risk = item.get("risk_level", "UNKNOWN").upper()

        print(f"\n{i}. [{item_id}] Week {week}")
        print(f"   Title:  {title}")
        print(f"   Risk:   {risk}")
        print(f"   Start:  python scripts/checklist.py start {item_id}")

    print("\n" + "=" * 60)


def cmd_start(item_id: str):
    """Start working on an item."""
    items = load_yaml_simple(CHECKLIST_YAML)

    # Find and update
    for item in items:
        if item.get("id") == item_id:
            old_status = item.get("status")
            item["status"] = "in_progress"
            print(f"\n✅ Started: {item_id}")
            print(f"   Status:  {old_status} → in_progress")
            print(f"   Title:   {item.get('title')}")
            print("\n   Acceptance criteria:")
            for criterion in item.get("acceptance_criteria", []):
                print(f"     ☐ {criterion}")
            print("\n   Verification commands:")
            for cmd in item.get("verification_commands", []):
                print(f"     {cmd}")
            return

    print(f"❌ Item not found: {item_id}")
    sys.exit(1)


def cmd_done(item_id: str, agent_name: str, files_str: str):
    """Mark item as done."""
    items = load_yaml_simple(CHECKLIST_YAML)
    verifications = load_verification()

    # Check if verification was run recently
    if item_id not in verifications:
        print(f"❌ ERROR: No verification commands logged for {item_id}")
        print("   You must run verification commands AFTER code changes.")
        print(f"   See checklist.yaml for {item_id}:")
        for item in items:
            if item.get("id") == item_id:
                print("   Commands to run:")
                for cmd in item.get("verification_commands", []):
                    print(f"     {cmd}")
                break
        sys.exit(1)

    # Find and update item
    for item in items:
        if item.get("id") == item_id:
            item["status"] = "done"
            item["completed_by"] = agent_name
            item["completed_at"] = datetime.now(UTC).isoformat()

            if files_str:
                item["files_touched"] = [f.strip() for f in files_str.split(",")]

            print(f"\n✅ Marked Done: {item_id}")
            print(f"   Title:        {item.get('title')}")
            print(f"   Completed by: {agent_name}")
            print(f"   Completed at: {item['completed_at']}")
            if files_str:
                print("   Files touched:")
                for f in item["files_touched"]:
                    print(f"     - {f}")

            print("\n   Next: git add .mcp/ && git commit -m 'feat: ...'")
            return

    print(f"❌ Item not found: {item_id}")
    sys.exit(1)


def cmd_verify(item_id: str):
    """Run verification commands for an item."""
    items = load_yaml_simple(CHECKLIST_YAML)
    verifications = load_verification()

    # Find item
    item = None
    for i in items:
        if i.get("id") == item_id:
            item = i
            break

    if not item:
        print(f"❌ Item not found: {item_id}")
        sys.exit(1)

    commands = item.get("verification_commands", [])
    if not commands:
        print(f"❌ No verification commands defined for {item_id}")
        sys.exit(1)

    print(f"\n🔍 Verifying: {item_id}")
    print(f"   Title: {item.get('title')}")
    print(f"\n   Running {len(commands)} verification command(s)...")
    print("=" * 60)

    all_passed = True
    for i, cmd in enumerate(commands, 1):
        print(f"\n[{i}/{len(commands)}] {cmd}")
        result = subprocess.run(cmd, shell=True, cwd=REPO_ROOT)
        if result.returncode != 0:
            all_passed = False
            print("❌ FAILED")
        else:
            print("✅ PASSED")

    if all_passed:
        print("\n" + "=" * 60)
        print("✅ All verification commands passed!")

        # Log verification
        verifications[item_id] = {
            "last_verified": datetime.now(UTC).isoformat(),
            "verified_by": "cli",
            "commands_run": commands,
            "passed": True,
        }
        save_verification(verifications)

        print("\n   You can now run:")
        print(f"   python scripts/checklist.py done {item_id} --by '<agent>' --files '<files>'")
    else:
        print("\n" + "=" * 60)
        print("❌ Some commands failed. Fix and re-run.")
        sys.exit(1)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Cricksy Scorer MCP Checklist CLI")

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # status
    status_parser = subparsers.add_parser("status", help="Show checklist status")
    status_parser.add_argument("--week", type=int, help="Filter by week")

    # next
    next_parser = subparsers.add_parser("next", help="Suggest next items")
    next_parser.add_argument("--count", type=int, default=3, help="Number of items to show")

    # start
    start_parser = subparsers.add_parser("start", help="Start working on item")
    start_parser.add_argument("id", help="Item ID")

    # done
    done_parser = subparsers.add_parser("done", help="Mark item as done")
    done_parser.add_argument("id", help="Item ID")
    done_parser.add_argument("--by", required=True, dest="agent_name", help="Agent name")
    done_parser.add_argument("--files", default="", help="Comma-separated files touched")

    # verify
    verify_parser = subparsers.add_parser("verify", help="Run verification commands")
    verify_parser.add_argument("id", help="Item ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "status":
        cmd_status(args.week)
    elif args.command == "next":
        cmd_next(args.count)
    elif args.command == "start":
        cmd_start(args.id)
    elif args.command == "done":
        cmd_done(args.id, args.agent_name, args.files)
    elif args.command == "verify":
        cmd_verify(args.id)


if __name__ == "__main__":
    main()
