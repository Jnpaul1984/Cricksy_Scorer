import type { LocationQueryValue } from 'vue-router'

/** Accept only same-application, absolute paths. */
export function safeInternalRedirect(value: LocationQueryValue | LocationQueryValue[] | undefined, fallback = '/setup'): string {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || value.includes('\\')) return fallback
  try {
    const parsed = new URL(value, 'https://cricksy.local')
    return parsed.origin === 'https://cricksy.local' && parsed.pathname.startsWith('/') ? `${parsed.pathname}${parsed.search}${parsed.hash}` : fallback
  } catch {
    return fallback
  }
}

export function authEntryRedirect(value: LocationQueryValue | LocationQueryValue[] | undefined): string {
  return safeInternalRedirect(value, '/setup')
}
