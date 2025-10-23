import re
from pathlib import Path

p = Path("backend/main.py")
src = p.read_text(encoding="utf-8")

# Normalize BOM if present
src = src.lstrip("\ufeff")

# 1) Ensure there's only one async def get_db(...) definition
matches = list(re.finditer(r"\basync\s+def\s+get_db\s*\(", src))
if len(matches) >= 2:
    # Remove everything from the second 'get_db' section header through the subsequent in-memory env block if present
    second_idx = matches[1].start()
    # Back up to the nearest section header (the long ===== line) before the second get_db
    header_start = src.rfind(
        "# ===============================================================",
        0,
        second_idx,
    )
    if header_start == -1:
        header_start = second_idx

    # Find an env block that uses os.getenv("CRICKSY_IN_MEMORY_DB") after the second get_db
    env_idx = src.find('os.getenv("CRICKSY_IN_MEMORY_DB")', second_idx)
    # Decide the cut end at the next major section header after either the env block or the second get_db
    seek_from = env_idx if env_idx != -1 else second_idx
    next_header = src.find(
        "# ===============================================================",
        seek_from + 1,
    )
    cut_end = next_header if next_header != -1 else len(src)

    # Splice it out
    src = src[:header_start] + src[cut_end:]

# 2) Remove stray secondary imports of settings if duplicated in that deleted block left residue
# Safe cleanup: collapse accidental duplicate blank lines around where we cut
src = re.sub(r"\n{3,}", "\n\n", src)

p.write_text(src, encoding="utf-8")
print("Deduped DB dependency and in-memory env block in backend/main.py")
