import { describe, expect, it } from 'vitest';

import { safeInternalRedirect } from '@/utils/safeRedirect';

describe('safeInternalRedirect', () => {
  it('retains internal routes including query strings', () => {
    expect(safeInternalRedirect('/schools/create?source=free')).toBe('/schools/create?source=free');
  });

  it.each(['https://evil.example', '//evil.example', 'schools/create', '/\\evil.example'])(
    'rejects unsafe target %s',
    (target) => expect(safeInternalRedirect(target)).toBe('/setup'),
  );
});
