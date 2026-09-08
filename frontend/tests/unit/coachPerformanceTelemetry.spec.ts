import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  fetchWithCoachPerformance,
  readCoachPerformanceJson,
  recordCoachPerformance,
} from '@/utils/coachPerformanceTelemetry';

describe('coach performance telemetry', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('records safe request timing metadata only after response-body consumption', async () => {
    const response = new Response(JSON.stringify({ private_report: 'not-for-telemetry' }), {
      status: 200,
      headers: { 'content-length': '48', 'x-request-id': 'request-123' },
    });
    let finishBody: ((value: unknown) => void) | undefined;
    vi.spyOn(response, 'json').mockImplementation(
      () => new Promise((resolve) => (finishBody = resolve)),
    );
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response));
    vi.stubGlobal('performance', { now: vi.fn().mockReturnValueOnce(10).mockReturnValueOnce(35) });
    const log = vi.spyOn(console, 'info').mockImplementation(() => undefined);

    const result = await fetchWithCoachPerformance('coach_plus.analysis_results', '/safe-path');
    expect(result).toBe(response);
    expect(log).not.toHaveBeenCalled();

    const bodyPromise = readCoachPerformanceJson<{ private_report: string }>(result);
    expect(log).not.toHaveBeenCalled();
    finishBody?.({ private_report: 'not-for-telemetry' });
    await expect(bodyPromise).resolves.toEqual({ private_report: 'not-for-telemetry' });

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
        duration_ms: 25,
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
