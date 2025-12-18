import { ref, computed } from 'vue'

interface FollowedEntity {
  id: string
  type: 'team' | 'player' | 'tournament'
  name: string
  followedAt: string
}

// Persistent store for followed entities
const followedEntities = ref<Map<string, FollowedEntity>>(new Map())

// Load from localStorage on init
function initializeFollows() {
  const stored = localStorage.getItem('cricksy-followed-entities')
  if (stored) {
    const parsed = JSON.parse(stored) as FollowedEntity[]
    const map = new Map(parsed.map((e) => [e.id, e]))
    followedEntities.value = map
  }
}

// Save to localStorage
function saveFollows() {
  const array = Array.from(followedEntities.value.values())
  localStorage.setItem('cricksy-followed-entities', JSON.stringify(array))
}

export function useFollowSystem() {
  // Follow an entity
  function follow(id: string, type: 'team' | 'player' | 'tournament', name: string) {
    const entity: FollowedEntity = {
      id,
      type,
      name,
      followedAt: new Date().toISOString(),
    }
    followedEntities.value.set(id, entity)
    saveFollows()
  }

  // Unfollow an entity
  function unfollow(id: string) {
    followedEntities.value.delete(id)
    saveFollows()
  }

  // Check if entity is followed
  function isFollowed(id: string): boolean {
    return followedEntities.value.has(id)
  }

  // Get all followed entities
  const all = computed(() => Array.from(followedEntities.value.values()))

  // Get followed entities by type
  function getByType(type: 'team' | 'player' | 'tournament') {
    return all.value.filter((e) => e.type === type)
  }

  // Get recently followed
  const recentlyFollowed = computed(() => {
    return all.value.sort(
      (a, b) => new Date(b.followedAt).getTime() - new Date(a.followedAt).getTime()
    )
  })

  return {
    follow,
    unfollow,
    isFollowed,
    all,
    getByType,
    recentlyFollowed,
  }
}

// Initialize on module load
initializeFollows()
