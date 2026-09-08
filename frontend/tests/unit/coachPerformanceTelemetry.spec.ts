import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  fetchWithCoachPerformance,
  recordCoachPerformance,
} from '@/utils/coachPerformanceTelemetry';

describe('coach performance telemetry', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('records safe request timing metadata and returns the original response', async () => {
    const response = new Response(JSON.stringify({ private_report: 'not-for-telemetry' }), {
      status: 200,
      headers: { 'content-length': '48', 'x-request-id': 'request-123' },
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response));
    const log = vi.spyOn(console, 'info').mockImplementation(() => undefined);

    const result = await fetchWithCoachPerformance('coach_plus.analysis_results', '/safe-path');

    expect(result).toBe(response);
    expect(log).toHaveBeenCalledWith(
      '[coach-performance]',
      expect.objectContaining({
        operation: 'coach_plus.analysis_results',
        layer: 'frontend',
        phase: 'request',
        outcome: 'success',
        status: 200,
        payload_size_bytes: 48,
        request_id: 'request-123',
        duration_ms: expect.any(Number),
      }),
    );
    expect(JSON.stringify(log.mock.calls)).not.toContain('private_report');
    expect(JSON.stringify(log.mock.calls)).not.toContain('not-for-telemetry');
  });

  it('records failed requests without replacing the network error', async () => {
    const failure = new Error('network unavailable');
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(failure));
    const log = vi.spyOn(console, 'info').mockImplementation(() => undefined);

    await expect(fetchWithCoachPerformance('coach_plus.session_list', '/safe-path')).rejects.toBe(
      failure,
    );
    expect(log).toHaveBeenCalledWith(
      '[coach-performance]',
      expect.objectContaining({ outcome: 'failure', phase: 'request' }),
    );
  });

  it('never lets telemetry output failure break the user flow', () => {
    vi.spyOn(console, 'info').mockImplementation(() => {
      throw new Error('console unavailable');
    });

    expect(() =>
      recordCoachPerformance({
        operation: 'coach_plus.session_list',
        layer: 'frontend',
        phase: 'render',
        duration_ms: 1,
        outcome: 'success',
      }),
    ).not.toThrow();
  });
});
