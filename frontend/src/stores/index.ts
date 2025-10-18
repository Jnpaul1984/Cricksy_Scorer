// src/stores/index.ts
import { createPinia } from 'pinia'

const pinia = createPinia()

// If you want global mutation logs, do it like this:
pinia.use(({ store }) => {
  store.$subscribe(() => {
    // mutation has: { type: 'direct' | 'patch object' | 'patch function', storeId, events? }
    // No `payload` field. Use mutation.events for 'direct', or inspect `state`.
    // console.debug(`[${mutation.storeId}]`, mutation.type, mutation.events)
  })
})

export default pinia
