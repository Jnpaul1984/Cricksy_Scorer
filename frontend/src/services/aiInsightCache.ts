export type AiInsightCacheScope = 'match-summary' | 'player-insights'

type AiInsightCacheStatus = 'miss' | 'fresh' | 'stale'

interface AiInsightCacheEntry<T> {
  value: T
  contextHash: string
  cachedAtMs: number
}

interface ReadAiInsightCacheOptions {
  scope: AiInsightCacheScope
  key: string
  contextHash: string
  staleAfterMs: number
}

interface WriteAiInsightCacheOptions<T> {
  scope: AiInsightCacheScope
  key: string
  contextHash: string
  value: T
}

const aiInsightCache = new Map<string, AiInsightCacheEntry<unknown>>()

function buildCacheId(scope: AiInsightCacheScope, key: string): string {
  return `${scope}:${key}`
}

export function readAiInsightCache<T>(
  options: ReadAiInsightCacheOptions,
): { status: AiInsightCacheStatus; entry: AiInsightCacheEntry<T> | null } {
  const cacheId = buildCacheId(options.scope, options.key)
  const cached = aiInsightCache.get(cacheId)
  if (!cached) {
    return { status: 'miss', entry: null }
  }
  if (cached.contextHash !== options.contextHash) {
    aiInsightCache.delete(cacheId)
    return { status: 'miss', entry: null }
  }
  const ageMs = Date.now() - cached.cachedAtMs
  return {
    status: ageMs > options.staleAfterMs ? 'stale' : 'fresh',
    entry: cached as AiInsightCacheEntry<T>,
  }
}

export function writeAiInsightCache<T>(options: WriteAiInsightCacheOptions<T>): void {
  const cacheId = buildCacheId(options.scope, options.key)
  aiInsightCache.set(cacheId, {
    value: options.value,
    contextHash: options.contextHash,
    cachedAtMs: Date.now(),
  })
}

export function clearAiInsightCache(scope: AiInsightCacheScope, key: string): void {
  aiInsightCache.delete(buildCacheId(scope, key))
}

export function __resetAiInsightCacheForTests(): void {
  aiInsightCache.clear()
}
