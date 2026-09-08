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

interface PendingCoachRequest {
  operation: string;
  started_at: number;
}

const pendingRequests = new WeakMap<Response, PendingCoachRequest>();

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

function finishCoachRequest(response: Response, outcome?: 'success' | 'failure'): void {
  try {
    const pending = pendingRequests.get(response);
    if (!pending) return;
    pendingRequests.delete(response);

    const payloadSizeHeader = response.headers.get('content-length');
    const payloadSize = payloadSizeHeader === null ? Number.NaN : Number(payloadSizeHeader);
    const requestId = response.headers.get('x-request-id');
    recordCoachPerformance({
      operation: pending.operation,
      layer: 'frontend',
      phase: 'request',
      duration_ms: Math.max(0, performanceNow() - pending.started_at),
      outcome: outcome ?? (response.ok ? 'success' : 'failure'),
      status: response.status,
      ...(Number.isFinite(payloadSize) && payloadSize >= 0
        ? { payload_size_bytes: payloadSize }
        : {}),
      ...(requestId ? { request_id: requestId } : {}),
    });
  } catch {
    // Telemetry must never affect response consumption.
  }
}

export async function readCoachPerformanceJson<T>(response: Response): Promise<T> {
  try {
    const result = (await response.json()) as T;
    finishCoachRequest(response);
    return result;
  } catch (error) {
    finishCoachRequest(response, 'failure');
    throw error;
  }
}

export function finishCoachPerformanceRequest(response: Response): void {
  finishCoachRequest(response);
}

export async function fetchWithCoachPerformance(
  operation: string,
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const startedAt = performanceNow();
  try {
    const response = await fetch(input, init);
    try {
      pendingRequests.set(response, { operation, started_at: startedAt });
    } catch {
      // Telemetry must never affect the fetch result.
    }
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
