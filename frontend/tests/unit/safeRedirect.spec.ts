import { describe, expect, it } from 'vitest';

import { authEntryRedirect, safeInternalRedirect } from '@/utils/safeRedirect';

describe('safeInternalRedirect', () => {
  it('retains internal routes including query strings', () => {
    expect(safeInternalRedirect('/schools/create?source=free')).toBe('/schools/create?source=free');
  });

  it.each(['https://evil.example', '//evil.example', 'schools/create', '/\\evil.example'])(
    'rejects unsafe target %s',
    (target) => expect(safeInternalRedirect(target)).toBe('/setup'),
  );
});

describe('authEntryRedirect', () => {
  it.each(['/login', '/register'])('preserves School continuation from %s', () => {
    expect(authEntryRedirect('/schools/create')).toBe('/schools/create');
  });
  it('falls back for unsafe continuation', () => expect(authEntryRedirect('https://evil.example')).toBe('/setup'));
  it('falls back without continuation', () => expect(authEntryRedirect(undefined)).toBe('/setup'));
});
