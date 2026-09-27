import { describe, expect, it } from 'vitest';

import { organizationOperationError } from '@/utils/organizationOperations';

describe('organization operations error presentation', () => {
  it.each([
    [403, 'forbidden detail', 'do not have permission'],
    [404, 'private metadata', 'not found or is not available'],
    [409, 'Event cannot be deleted while retained history exists', 'retained history'],
    [422, 'Roster player is not eligible for this event', 'not eligible'],
  ])('maps HTTP %s to a controlled message', (status, detail, expected) => {
    const reason = Object.assign(new Error(detail), { status });
    expect(organizationOperationError(reason, 'event')).toContain(expected);
  });

  it('presents a network failure without leaking implementation details', () => {
    expect(organizationOperationError(new TypeError('fetch failed'), 'register')).toBe(
      'The service could not be reached. Check your connection and try again.',
    );
  });
});
