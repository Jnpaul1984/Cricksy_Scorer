export interface CoachPerformanceTelemetry {
  operation: string;
  layer: 'frontend';
  phase: 'request' | 'render' | 'download_handoff';
  duration_ms: number;
  outcome: 'success' | 'failure';
  status?: number;
  payload_size_bytes?: number;
  item_count?: number;
  request_id?: string;
}

export function performanceNow(): number {
  try {
    const timestamp = globalThis.performance?.now() ?? Date.now();
    return Number.isFinite(timestamp) ? timestamp : Date.now();
  } catch {
    return Date.now();
  }
}

export function recordCoachPerformance(event: CoachPerformanceTelemetry): void {
  try {
    console.info('[coach-performance]', event);
  } catch {
    // Telemetry must never affect the user flow.
  }
}

export async function fetchWithCoachPerformance(
  operation: string,
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const startedAt = performanceNow();
  try {
    const response = await fetch(input, init);
    const payloadSizeHeader = response.headers.get('content-length');
    const payloadSize = payloadSizeHeader === null ? Number.NaN : Number(payloadSizeHeader);
    const requestId = response.headers.get('x-request-id');
    recordCoachPerformance({
      operation,
      layer: 'frontend',
      phase: 'request',
      duration_ms: Math.max(0, performanceNow() - startedAt),
      outcome: response.ok ? 'success' : 'failure',
      status: response.status,
      ...(Number.isFinite(payloadSize) && payloadSize >= 0
        ? { payload_size_bytes: payloadSize }
        : {}),
      ...(requestId ? { request_id: requestId } : {}),
    });
    return response;
  } catch (error) {
    recordCoachPerformance({
      operation,
      layer: 'frontend',
      phase: 'request',
      duration_ms: Math.max(0, performanceNow() - startedAt),
      outcome: 'failure',
    });
    throw error;
  }
}
