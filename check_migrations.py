#!/usr/bin/env python3
"""Check current Alembic migration heads."""
import re
from pathlib import Path

versions_dir = Path('backend/alembic/versions')
migrations = {}

for f in sorted(versions_dir.glob('*.py')):
    if f.name.startswith('.'):
        continue
    with open(f) as file:
        content = file.read()
        # Extract revision ID
        rev_match = re.search(r'revision\s*:\s*str\s*=\s*["\']([a-z0-9]+)["\']', content)
        # Extract down_revision
        down_match = re.search(r'down_revision\s*:\s*\w+\[?\w*\]?\s*=\s*["\']([a-z0-9]+)["\']', content)
        
        if rev_match:
            rev = rev_match.group(1)
            down_rev = down_match.group(1) if down_match else None
            migrations[rev] = {'down': down_rev, 'file': f.name}

# Find heads (revisions with no children)
all_revs = set(migrations.keys())
all_downs = set(m['down'] for m in migrations.values() if m['down'])
heads = [r for r in all_revs if r not in all_downs]

print(f'Total migrations: {len(migrations)}')
print(f'Current heads ({len(heads)}):')
for h in sorted(heads):
    print(f'  {h} ({migrations[h]["file"]})')

# Check for multiple heads and broken references
if len(heads) > 1:
    print(f'\n⚠️  WARNING: Multiple heads detected!')
    print('This will cause "Multiple head revisions are present" error in Alembic.')
