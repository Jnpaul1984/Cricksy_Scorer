<script setup lang="ts">
type Delivery = {
  over_number: number
  ball_number: number
  bowler_id: string
  striker_id: string
  non_striker_id: string
  runs_scored: number
  is_extra?: boolean
  extra_type?: string | null
  is_wicket?: boolean
  dismissal_type?: string | null
  dismissed_player_id?: string | null
  commentary?: string | null
}

const props = defineProps<{
  deliveries: Delivery[]
  playerNameById?: (id?: string | null) => string
  reverse?: boolean
}>()

const nameOf = (id?: string | null) =>
  (props.playerNameById ? props.playerNameById(id) : id) || ''
</script>

<template>
  <div class="table-wrap">
    <table v-if="deliveries?.length">
      <thead>
        <tr>
          <th>Ov</th>
          <th>Ball</th>
          <th>Striker</th>
          <th>Bowler</th>
          <th>Runs</th>
          <th>Extra</th>
          <th>Wicket</th>
          <th>Notes</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(d, i) in (reverse ? [...deliveries].slice().reverse() : deliveries)"
          :key="i"
        >
          <td>{{ d.over_number }}</td>
          <td>{{ d.ball_number }}</td>
          <td>{{ nameOf(d.striker_id) }}</td>
          <td>{{ nameOf(d.bowler_id) }}</td>
          <td class="num">{{ d.runs_scored }}</td>
          <td class="tag" v-if="d.is_extra">
            {{ (d.extra_type || '').toUpperCase() }}
          </td>
          <td class="tag wicket" v-else-if="d.is_wicket">
            {{ (d.dismissal_type || 'WICKET').toUpperCase() }}
          </td>
          <td v-else>—</td>
          <td class="notes">{{ d.commentary || '' }}</td>
        </tr>
      </tbody>
    </table>

    <div v-else class="empty">
      No deliveries yet.
    </div>
  </div>
</template>

<style scoped>
.table-wrap{overflow-x:auto;border-radius:12px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.15)}
table{width:100%;border-collapse:collapse}
th,td{padding:.65rem .75rem;border-bottom:1px solid rgba(255,255,255,.08);color:#fff}
th{background:rgba(255,255,255,.08);text-align:left;font-weight:600}
.num{font-variant-numeric:tabular-nums}
.tag{font-size:.85rem;font-weight:700;letter-spacing:.02em}
.wicket{color:#ffb3b3}
.notes{opacity:.9}
.empty{padding:1rem;color:#fff;opacity:.85}
</style>
