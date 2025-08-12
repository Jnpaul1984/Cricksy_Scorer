// src/utils/api.ts
// Lightweight fetch client with good errors + timeouts.
// Public API: apiService + getErrorMessage (used by the store)

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

if (!BASE_URL) {
  // Helpful dev log; won't crash the app, but you'll see it in console
  // You can throw here if you want to hard-fail when env is missing.
  console.warn('[api] VITE_API_BASE_URL is not set');
}

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

async function request<T>(
  path: string,
  method: HttpMethod = 'GET',
  body?: unknown,
  timeoutMs = 15000
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: body != null ? JSON.stringify(body) : undefined,
      signal: controller.signal,
      // credentials: 'include', // enable if your API needs cookies
    });

    const isJson = res.headers.get('content-type')?.includes('application/json');

    if (!res.ok) {
      let message = `${res.status} ${res.statusText}`;
      if (isJson) {
        try {
          const data = await res.json();
          message = (data?.message as string) || message;
        } catch {}
      }
      const err = new Error(message);
      (err as any).status = res.status;
      throw err;
    }

    return (isJson ? (await res.json()) : (await res.text())) as T;
  } catch (e) {
    // normalize AbortError message
    if ((e as any)?.name === 'AbortError') {
      throw new Error('Request timed out');
    }
    throw e;
  } finally {
    clearTimeout(t);
  }
}

export function getErrorMessage(e: unknown): string {
  if (!e) return 'Unknown error';
  if (typeof e === 'string') return e;
  const any = e as any;
  return any?.message || any?.toString?.() || 'Unknown error';
}

// ===== App-specific endpoints =====

export const apiService = {
  createGame(payload: unknown) {
    return request('/games', 'POST', payload);
  },

  getGame(id: string) {
    return request(`/games/${encodeURIComponent(id)}`, 'GET');
  },

  scoreDelivery(id: string, body: unknown) {
    return request(`/games/${encodeURIComponent(id)}/deliveries`, 'POST', body);
  },

  startNextInnings(id: string) {
    return request(`/games/${encodeURIComponent(id)}/next-innings`, 'POST');
  },
};
