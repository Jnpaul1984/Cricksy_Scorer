<template>
  <div class="crp">
    <!-- Header -->
    <div class="crp-header">
      <h3 class="crp-title">👥 CPL Roster Registry</h3>
      <p class="crp-subtitle">
        Phase 10T — Manage current CPL season teams and player squads. Supports new teams,
        returning players, aliases, and roster status. All entries are user-maintained;
        historical match data is not altered.
      </p>
    </div>

    <!-- Trust note -->
    <div class="crp-trust-note" role="note">
      🔍 <strong>Trust note:</strong> Roster data is user-maintained and should be reviewed
      before publication. Player statistics are not available for current-season roster entries
      unless historical match data exists.
    </div>

    <!-- Mode tabs -->
    <div class="crp-mode-row">
      <button
        v-for="m in modes"
        :key="m.value"
        :class="['crp-mode-btn', { 'crp-mode-btn--active': mode === m.value }]"
        @click="mode = m.value"
      >
        {{ m.icon }} {{ m.label }}
      </button>
    </div>

    <!-- ── Season / Competition filter bar ── -->
    <div class="crp-filter-bar">
      <div class="crp-filter-group">
        <label class="crp-label" for="crp-comp">Competition</label>
        <input
          id="crp-comp"
          v-model="filterCompetition"
          class="crp-input crp-input--sm"
          placeholder="CPL_MEN"
        />
      </div>
      <div class="crp-filter-group">
        <label class="crp-label" for="crp-season">Season</label>
        <input
          id="crp-season"
          v-model="filterSeason"
          class="crp-input crp-input--sm"
          placeholder="e.g. 2025"
        />
      </div>
      <div class="crp-filter-group">
        <label class="crp-label" for="crp-team-filter">Team</label>
        <input
          id="crp-team-filter"
          v-model="filterTeam"
          class="crp-input crp-input--sm"
          placeholder="Filter by team"
        />
      </div>
      <button class="crp-load-btn" :disabled="loading" @click="loadAll">
        {{ loading ? '⏳' : '🔄' }} Load
      </button>
    </div>

    <div v-if="loadError" class="crp-error">{{ loadError }}</div>

    <!-- =====================================================================
         TEAMS MODE
         ===================================================================== -->
    <div v-if="mode === 'teams'" class="crp-panel">
      <div class="crp-panel-header">
        <h4 class="crp-panel-title">Teams ({{ teams.length }})</h4>
        <button class="crp-add-btn" @click="showAddTeam = !showAddTeam">
          {{ showAddTeam ? '✕ Cancel' : '＋ Add Team' }}
        </button>
      </div>

      <!-- Add team form -->
      <div v-if="showAddTeam" class="crp-form-box">
        <div class="crp-form-row">
          <div class="crp-form-col">
            <label class="crp-label" for="at-comp">Competition</label>
            <input id="at-comp" v-model="newTeam.competition_code" class="crp-input" placeholder="CPL_MEN" />
          </div>
          <div class="crp-form-col">
            <label class="crp-label" for="at-season">Season *</label>
            <input id="at-season" v-model="newTeam.season" class="crp-input" placeholder="2025" />
          </div>
          <div class="crp-form-col crp-form-col--wide">
            <label class="crp-label" for="at-name">Team Name *</label>
            <input id="at-name" v-model="newTeam.team_name" class="crp-input" placeholder="Trinbago Knight Riders" />
          </div>
          <div class="crp-form-col">
            <label class="crp-label" for="at-short">Short Name</label>
            <input id="at-short" v-model="newTeam.short_name" class="crp-input" placeholder="TKR" />
          </div>
        </div>
        <div class="crp-form-row">
          <div class="crp-form-col crp-form-col--wide">
            <label class="crp-label" for="at-source">Source Note</label>
            <input id="at-source" v-model="newTeam.source_note" class="crp-input" placeholder="Manual entry" />
          </div>
        </div>
        <div class="crp-form-actions">
          <button class="crp-save-btn" :disabled="addingTeam || !newTeam.team_name || !newTeam.season" @click="addTeam">
            {{ addingTeam ? '⏳ Saving…' : '💾 Save Team' }}
          </button>
        </div>
        <div v-if="addTeamError" class="crp-error">{{ addTeamError }}</div>
        <div v-if="addTeamSuccess" class="crp-success">✅ Team added.</div>
      </div>

      <!-- Teams table -->
      <div v-if="teams.length === 0 && !loading" class="crp-empty">
        No teams found for this filter. Use Load or Add Team above.
      </div>
      <div v-else class="crp-table-wrapper">
        <table class="crp-table">
          <thead>
            <tr>
              <th>Team</th>
              <th>Short</th>
              <th>Season</th>
              <th>Competition</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="team in teams" :key="team.id">
              <td>{{ team.team_name }}</td>
              <td>{{ team.short_name ?? '—' }}</td>
              <td>{{ team.season }}</td>
              <td>{{ team.competition_code }}</td>
              <td class="crp-td-muted">{{ team.source_note ?? '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- =====================================================================
         PLAYERS MODE
         ===================================================================== -->
    <div v-if="mode === 'players'" class="crp-panel">
      <div class="crp-panel-header">
        <h4 class="crp-panel-title">
          Players ({{ players.length }} / {{ playersMeta.total }})
          <span v-if="playersMeta.returning_count > 0" class="crp-returning-badge">
            {{ playersMeta.returning_count }} returning
          </span>
        </h4>
        <button class="crp-add-btn" @click="showAddPlayer = !showAddPlayer">
          {{ showAddPlayer ? '✕ Cancel' : '＋ Add Player' }}
        </button>
      </div>

      <!-- Add player form -->
      <div v-if="showAddPlayer" class="crp-form-box">
        <div class="crp-form-row">
          <div class="crp-form-col">
            <label class="crp-label" for="ap-comp">Competition</label>
            <input id="ap-comp" v-model="newPlayer.competition_code" class="crp-input" placeholder="CPL_MEN" />
          </div>
          <div class="crp-form-col">
            <label class="crp-label" for="ap-season">Season *</label>
            <input id="ap-season" v-model="newPlayer.season" class="crp-input" placeholder="2025" />
          </div>
          <div class="crp-form-col crp-form-col--wide">
            <label class="crp-label" for="ap-name">Player Name *</label>
            <input id="ap-name" v-model="newPlayer.player_name" class="crp-input" placeholder="Full player name" />
          </div>
          <div class="crp-form-col">
            <label class="crp-label" for="ap-display">Display Name</label>
            <input id="ap-display" v-model="newPlayer.display_name" class="crp-input" placeholder="Optional" />
          </div>
        </div>
        <div class="crp-form-row">
          <div class="crp-form-col">
            <label class="crp-label" for="ap-team">Team</label>
            <input id="ap-team" v-model="newPlayer.team_name" class="crp-input" placeholder="Team name" />
          </div>
          <div class="crp-form-col">
            <label class="crp-label" for="ap-role">Role</label>
            <select id="ap-role" v-model="newPlayer.role" class="crp-select">
              <option value="">— select —</option>
              <option value="batsman">Batsman</option>
              <option value="bowler">Bowler</option>
              <option value="all-rounder">All-Rounder</option>
              <option value="wicketkeeper">Wicketkeeper</option>
              <option value="wicketkeeper-batsman">WK-Batsman</option>
            </select>
          </div>
          <div class="crp-form-col">
            <label class="crp-label" for="ap-bat">Batting Style</label>
            <select id="ap-bat" v-model="newPlayer.batting_style" class="crp-select">
              <option value="">— select —</option>
              <option value="right-hand bat">Right-hand bat</option>
              <option value="left-hand bat">Left-hand bat</option>
            </select>
          </div>
          <div class="crp-form-col">
            <label class="crp-label" for="ap-bowl">Bowling Style</label>
            <input id="ap-bowl" v-model="newPlayer.bowling_style" class="crp-input" placeholder="e.g. right-arm fast" />
          </div>
          <div class="crp-form-col">
            <label class="crp-label" for="ap-status">Status</label>
            <select id="ap-status" v-model="newPlayer.status" class="crp-select">
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="unknown">Unknown</option>
            </select>
          </div>
        </div>
        <div class="crp-form-row">
          <div class="crp-form-col crp-form-col--wide">
            <label class="crp-label" for="ap-source">Source Note</label>
            <input id="ap-source" v-model="newPlayer.source_note" class="crp-input" placeholder="Manual entry" />
          </div>
        </div>
        <div class="crp-form-actions">
          <button class="crp-save-btn" :disabled="addingPlayer || !newPlayer.player_name || !newPlayer.season" @click="addPlayer">
            {{ addingPlayer ? '⏳ Saving…' : '💾 Save Player' }}
          </button>
        </div>
        <div v-if="addPlayerError" class="crp-error">{{ addPlayerError }}</div>
        <div v-if="addPlayerSuccess" class="crp-success">✅ Player added.</div>
      </div>

      <!-- Players table -->
      <div v-if="players.length === 0 && !loading" class="crp-empty">
        No players found. Use Load or Add Player above.
      </div>
      <div v-else class="crp-table-wrapper">
        <table class="crp-table">
          <thead>
            <tr>
              <th>Player</th>
              <th>Team</th>
              <th>Role</th>
              <th>Status</th>
              <th>Returning</th>
              <th>Season</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="player in players" :key="player.id">
              <td>
                <span class="crp-player-name">{{ player.display_name || player.player_name }}</span>
                <span v-if="player.display_name && player.display_name !== player.player_name" class="crp-alias">
                  ({{ player.player_name }})
                </span>
              </td>
              <td>{{ player.team_name ?? '—' }}</td>
              <td>{{ player.role ?? '—' }}</td>
              <td>
                <span :class="['crp-status-badge', `crp-status-badge--${player.status}`]">
                  {{ player.status }}
                </span>
              </td>
              <td>
                <span v-if="player.is_returning" class="crp-returning-pill">↩ {{ player.prior_season }}</span>
                <span v-else class="crp-td-muted">new</span>
              </td>
              <td>{{ player.season }}</td>
              <td>
                <button
                  v-if="editingPlayerId !== player.id"
                  class="crp-edit-btn"
                  @click="startEditPlayer(player)"
                >
                  Edit
                </button>
                <div v-else class="crp-inline-edit">
                  <select v-model="editPlayerStatus" class="crp-select crp-select--sm">
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                    <option value="unknown">Unknown</option>
                  </select>
                  <input v-model="editPlayerTeam" class="crp-input crp-input--sm" placeholder="Team" />
                  <button class="crp-save-btn crp-save-btn--sm" :disabled="savingPlayer" @click="savePlayerEdit(player.id)">
                    {{ savingPlayer ? '…' : '✓' }}
                  </button>
                  <button class="crp-cancel-btn" @click="cancelEditPlayer">✕</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- =====================================================================
         IMPORT MODE
         ===================================================================== -->
    <div v-if="mode === 'import'" class="crp-panel">
      <div class="crp-panel-header">
        <h4 class="crp-panel-title">📥 Roster Import (CSV / JSON)</h4>
      </div>

      <div class="crp-import-instructions">
        <p>
          Paste CSV rows below (one player per row). Expected columns:
        </p>
        <pre class="crp-import-cols">competition,season,team,player,role,batting_style,bowling_style,status,source_note</pre>
        <p>
          Or paste a JSON array of player objects with the same fields.
          The first row of CSV may be a header. Click <strong>Preview</strong> to check for
          new teams, returning players, and duplicates before applying.
        </p>
      </div>

      <div class="crp-form-row">
        <div class="crp-form-col">
          <label class="crp-label" for="imp-comp">Competition</label>
          <input id="imp-comp" v-model="importCompetition" class="crp-input" placeholder="CPL_MEN" />
        </div>
        <div class="crp-form-col">
          <label class="crp-label" for="imp-season">Season *</label>
          <input id="imp-season" v-model="importSeason" class="crp-input" placeholder="2025" />
        </div>
      </div>

      <div class="crp-form-col crp-form-col--wide">
        <label class="crp-label" for="imp-raw">Paste CSV or JSON</label>
        <textarea
          id="imp-raw"
          v-model="importRaw"
          class="crp-textarea"
          rows="8"
          placeholder="competition,season,team,player,role,batting_style,bowling_style,status,source_note&#10;CPL_MEN,2025,Trinbago Knight Riders,Kieron Pollard,all-rounder,right-hand bat,right-arm medium,active,Official squad"
        />
      </div>

      <div class="crp-form-actions">
        <button
          class="crp-load-btn"
          :disabled="importPreviewing || !importRaw.trim() || !importSeason.trim()"
          @click="previewImport"
        >
          {{ importPreviewing ? '⏳ Checking…' : '🔍 Preview Import' }}
        </button>
      </div>

      <div v-if="importError" class="crp-error">{{ importError }}</div>

      <!-- Preview results -->
      <div v-if="importPreview" class="crp-preview">
        <h5 class="crp-preview-title">Import Preview</h5>

        <div v-if="importPreview.blockers.length > 0" class="crp-preview-blockers">
          <strong>🚫 Blockers (must resolve before applying):</strong>
          <ul>
            <li v-for="(b, i) in importPreview.blockers" :key="i">{{ b }}</li>
          </ul>
        </div>

        <div v-if="importPreview.warnings.length > 0" class="crp-preview-warnings">
          <strong>⚠️ Warnings:</strong>
          <ul>
            <li v-for="(w, i) in importPreview.warnings" :key="i">{{ w }}</li>
          </ul>
        </div>

        <div class="crp-preview-stats">
          <div class="crp-preview-stat">
            <span class="crp-preview-stat-count">{{ importPreview.new_teams.length }}</span>
            <span class="crp-preview-stat-label">New Teams</span>
          </div>
          <div class="crp-preview-stat">
            <span class="crp-preview-stat-count">{{ importPreview.existing_teams_matched.length }}</span>
            <span class="crp-preview-stat-label">Teams Matched</span>
          </div>
          <div class="crp-preview-stat">
            <span class="crp-preview-stat-count">{{ importPreview.new_players.length }}</span>
            <span class="crp-preview-stat-label">New Players</span>
          </div>
          <div class="crp-preview-stat">
            <span class="crp-preview-stat-count">{{ importPreview.existing_players_matched.length }}</span>
            <span class="crp-preview-stat-label">Players Updated</span>
          </div>
          <div class="crp-preview-stat">
            <span class="crp-preview-stat-count crp-preview-stat-count--warn">{{ importPreview.duplicates.length }}</span>
            <span class="crp-preview-stat-label">Possible Duplicates</span>
          </div>
          <div class="crp-preview-stat">
            <span class="crp-preview-stat-count crp-preview-stat-count--info">{{ importPreview.returning_players.length }}</span>
            <span class="crp-preview-stat-label">Returning Players</span>
          </div>
        </div>

        <!-- Returning players list -->
        <div v-if="importPreview.returning_players.length > 0" class="crp-preview-section">
          <strong>↩ Returning players detected:</strong>
          <span class="crp-returning-chips">
            <span v-for="p in importPreview.returning_players" :key="p" class="crp-returning-chip">{{ p }}</span>
          </span>
        </div>

        <!-- Duplicates list -->
        <div v-if="importPreview.duplicates.length > 0" class="crp-preview-section crp-preview-section--warn">
          <strong>Possible duplicates (will be skipped):</strong>
          <ul>
            <li v-for="(d, i) in importPreview.duplicates" :key="i">
              {{ d.player_name }} <span v-if="d.warning">({{ d.warning }})</span>
            </li>
          </ul>
        </div>

        <!-- Apply button -->
        <div class="crp-form-actions">
          <button
            class="crp-apply-btn"
            :disabled="importApplying || importPreview.blockers.length > 0"
            @click="applyImport"
          >
            {{ importApplying ? '⏳ Applying…' : '✅ Apply Import' }}
          </button>
          <button class="crp-cancel-btn" @click="importPreview = null">Clear Preview</button>
        </div>
      </div>

      <!-- Apply result -->
      <div v-if="importResult" class="crp-import-result">
        <h5 class="crp-preview-title">✅ Import Applied</h5>
        <ul class="crp-result-list">
          <li>Teams created: <strong>{{ importResult.teams_created }}</strong></li>
          <li>Players created: <strong>{{ importResult.players_created }}</strong></li>
          <li>Players updated: <strong>{{ importResult.players_updated }}</strong></li>
          <li>Returning flagged: <strong>{{ importResult.returning_flagged }}</strong></li>
          <li>Duplicates skipped: <strong>{{ importResult.skipped_duplicates }}</strong></li>
        </ul>
        <div v-if="importResult.warnings.length > 0" class="crp-preview-warnings">
          <strong>Warnings:</strong>
          <ul><li v-for="(w, i) in importResult.warnings" :key="i">{{ w }}</li></ul>
        </div>
        <div v-if="importResult.errors.length > 0" class="crp-error">
          <strong>Errors:</strong>
          <ul><li v-for="(e, i) in importResult.errors" :key="i">{{ e }}</li></ul>
        </div>
        <button class="crp-load-btn" @click="() => { importResult = null; importPreview = null; importRaw = ''; loadAll() }">
          Done — Reload Roster
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import {
  listCplTeams,
  listCplPlayers,
  createCplTeam,
  createCplPlayer,
  updateCplPlayer,
  rosterImportPreview,
  rosterImportApply,
} from '@/services/api'
import type {
  CplTeamResponse,
  CplPlayerResponse,
  RosterImportPreviewResponse,
  RosterImportApplyResponse,
  RosterImportRow,
} from '@/services/api'

// ---------------------------------------------------------------------------
// Mode config
// ---------------------------------------------------------------------------

type Mode = 'teams' | 'players' | 'import'

const modes: { value: Mode; label: string; icon: string }[] = [
  { value: 'teams', label: 'Teams', icon: '🏏' },
  { value: 'players', label: 'Players', icon: '👤' },
  { value: 'import', label: 'Import', icon: '📥' },
]

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const mode = ref<Mode>('teams')
const filterCompetition = ref('CPL_MEN')
const filterSeason = ref('')
const filterTeam = ref('')
const loading = ref(false)
const loadError = ref('')

// Teams
const teams = ref<CplTeamResponse[]>([])
const showAddTeam = ref(false)
const addingTeam = ref(false)
const addTeamError = ref('')
const addTeamSuccess = ref(false)
const newTeam = reactive({
  competition_code: 'CPL_MEN',
  season: '',
  team_name: '',
  short_name: '',
  source_note: '',
})

// Players
const players = ref<CplPlayerResponse[]>([])
const playersMeta = reactive({ total: 0, returning_count: 0, new_count: 0 })
const showAddPlayer = ref(false)
const addingPlayer = ref(false)
const addPlayerError = ref('')
const addPlayerSuccess = ref(false)
const newPlayer = reactive({
  competition_code: 'CPL_MEN',
  season: '',
  team_name: '',
  player_name: '',
  display_name: '',
  role: '',
  batting_style: '',
  bowling_style: '',
  status: 'active' as 'active' | 'inactive' | 'unknown',
  source_note: '',
})

// Inline edit
const editingPlayerId = ref<string | null>(null)
const editPlayerStatus = ref<'active' | 'inactive' | 'unknown'>('active')
const editPlayerTeam = ref('')
const savingPlayer = ref(false)

// Import
const importCompetition = ref('CPL_MEN')
const importSeason = ref('')
const importRaw = ref('')
const importPreviewing = ref(false)
const importApplying = ref(false)
const importError = ref('')
const importPreview = ref<RosterImportPreviewResponse | null>(null)
const importResult = ref<RosterImportApplyResponse | null>(null)

// ---------------------------------------------------------------------------
// Load
// ---------------------------------------------------------------------------

async function loadAll() {
  loading.value = true
  loadError.value = ''
  try {
    const [teamResp, playerResp] = await Promise.all([
      listCplTeams({
        competition_code: filterCompetition.value || undefined,
        season: filterSeason.value || undefined,
      }),
      listCplPlayers({
        competition_code: filterCompetition.value || undefined,
        season: filterSeason.value || undefined,
        team_name: filterTeam.value || undefined,
      }),
    ])
    teams.value = teamResp.teams
    players.value = playerResp.players
    playersMeta.total = playerResp.total
    playersMeta.returning_count = playerResp.returning_count
    playersMeta.new_count = playerResp.new_count
  } catch (e: unknown) {
    loadError.value = e instanceof Error ? e.message : 'Failed to load roster data.'
  } finally {
    loading.value = false
  }
}

// ---------------------------------------------------------------------------
// Add team
// ---------------------------------------------------------------------------

async function addTeam() {
  addTeamError.value = ''
  addTeamSuccess.value = false
  addingTeam.value = true
  try {
    const created = await createCplTeam({
      competition_code: newTeam.competition_code || 'CPL_MEN',
      season: newTeam.season,
      team_name: newTeam.team_name,
      short_name: newTeam.short_name || null,
      source_note: newTeam.source_note || null,
    })
    teams.value.push(created)
    addTeamSuccess.value = true
    Object.assign(newTeam, { team_name: '', short_name: '', source_note: '' })
    showAddTeam.value = false
  } catch (e: unknown) {
    addTeamError.value = e instanceof Error ? e.message : 'Failed to add team.'
  } finally {
    addingTeam.value = false
  }
}

// ---------------------------------------------------------------------------
// Add player
// ---------------------------------------------------------------------------

async function addPlayer() {
  addPlayerError.value = ''
  addPlayerSuccess.value = false
  addingPlayer.value = true
  try {
    const created = await createCplPlayer({
      competition_code: newPlayer.competition_code || 'CPL_MEN',
      season: newPlayer.season,
      team_name: newPlayer.team_name || null,
      player_name: newPlayer.player_name,
      display_name: newPlayer.display_name || null,
      role: newPlayer.role || null,
      batting_style: newPlayer.batting_style || null,
      bowling_style: newPlayer.bowling_style || null,
      status: newPlayer.status,
      source_note: newPlayer.source_note || null,
    })
    players.value.push(created)
    playersMeta.total += 1
    addPlayerSuccess.value = true
    Object.assign(newPlayer, {
      player_name: '', display_name: '', team_name: '', role: '',
      batting_style: '', bowling_style: '', source_note: '',
    })
    showAddPlayer.value = false
  } catch (e: unknown) {
    addPlayerError.value = e instanceof Error ? e.message : 'Failed to add player.'
  } finally {
    addingPlayer.value = false
  }
}

// ---------------------------------------------------------------------------
// Edit player
// ---------------------------------------------------------------------------

function startEditPlayer(player: CplPlayerResponse) {
  editingPlayerId.value = player.id
  editPlayerStatus.value = player.status as 'active' | 'inactive' | 'unknown'
  editPlayerTeam.value = player.team_name ?? ''
}

function cancelEditPlayer() {
  editingPlayerId.value = null
}

async function savePlayerEdit(playerId: string) {
  savingPlayer.value = true
  try {
    const updated = await updateCplPlayer(playerId, {
      status: editPlayerStatus.value,
      team_name: editPlayerTeam.value || null,
    })
    const idx = players.value.findIndex(p => p.id === playerId)
    if (idx >= 0) players.value[idx] = updated
    editingPlayerId.value = null
  } catch {
    // ignore edit error silently
  } finally {
    savingPlayer.value = false
  }
}

// ---------------------------------------------------------------------------
// Import: parse raw CSV/JSON
// ---------------------------------------------------------------------------

function parseImportRows(raw: string, defaultCompetition: string, defaultSeason: string): RosterImportRow[] {
  const trimmed = raw.trim()
  if (trimmed.startsWith('[') || trimmed.startsWith('{')) {
    // JSON
    const parsed = JSON.parse(trimmed.startsWith('[') ? trimmed : `[${trimmed}]`) as Record<string, unknown>[]
    return parsed.map(row => ({
      competition: String(row.competition ?? defaultCompetition),
      season: String(row.season ?? defaultSeason),
      team: row.team ? String(row.team) : null,
      player: String(row.player ?? row.player_name ?? ''),
      role: row.role ? String(row.role) : null,
      batting_style: row.batting_style ? String(row.batting_style) : null,
      bowling_style: row.bowling_style ? String(row.bowling_style) : null,
      status: (row.status as 'active' | 'inactive' | 'unknown') ?? 'active',
      source_note: row.source_note ? String(row.source_note) : null,
    }))
  }
  // CSV
  const lines = trimmed.split('\n').map(l => l.trim()).filter(Boolean)
  const CSV_HEADERS = ['competition', 'season', 'team', 'player', 'role', 'batting_style', 'bowling_style', 'status', 'source_note']
  const firstLine = lines[0].toLowerCase().replace(/\s/g, '')
  const hasHeader = CSV_HEADERS.some(h => firstLine.includes(h))
  const dataLines = hasHeader ? lines.slice(1) : lines
  return dataLines.map(line => {
    const parts = line.split(',').map(p => p.trim())
    const get = (i: number) => parts[i] && parts[i] !== '' ? parts[i] : null
    return {
      competition: get(0) ?? defaultCompetition,
      season: get(1) ?? defaultSeason,
      team: get(2),
      player: get(3) ?? '',
      role: get(4),
      batting_style: get(5),
      bowling_style: get(6),
      status: (get(7) as 'active' | 'inactive' | 'unknown') ?? 'active',
      source_note: get(8),
    }
  }).filter(r => r.player)
}

async function previewImport() {
  importError.value = ''
  importPreview.value = null
  importResult.value = null
  importPreviewing.value = true
  try {
    const rows = parseImportRows(importRaw.value, importCompetition.value, importSeason.value)
    importPreview.value = await rosterImportPreview({
      competition_code: importCompetition.value || 'CPL_MEN',
      season: importSeason.value,
      rows,
    })
  } catch (e: unknown) {
    importError.value = e instanceof Error ? e.message : 'Failed to preview import.'
  } finally {
    importPreviewing.value = false
  }
}

async function applyImport() {
  if (!importPreview.value || importPreview.value.blockers.length > 0) return
  importError.value = ''
  importApplying.value = true
  try {
    const rows = parseImportRows(importRaw.value, importCompetition.value, importSeason.value)
    importResult.value = await rosterImportApply({
      competition_code: importCompetition.value || 'CPL_MEN',
      season: importSeason.value,
      rows,
      confirmed: true,
    })
    importPreview.value = null
  } catch (e: unknown) {
    importError.value = e instanceof Error ? e.message : 'Failed to apply import.'
  } finally {
    importApplying.value = false
  }
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

onMounted(() => {
  loadAll()
})
</script>

<style scoped>
.crp {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.crp-header {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.crp-title {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0;
}

.crp-subtitle {
  font-size: 0.85rem;
  color: var(--color-text-muted, #6b7280);
  margin: 0;
}

.crp-trust-note {
  padding: 0.5rem 0.75rem;
  background: #fefce8;
  border: 1px solid #fef08a;
  border-radius: 6px;
  font-size: 0.82rem;
  color: #713f12;
}

.crp-mode-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.crp-mode-btn {
  padding: 0.4rem 0.9rem;
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  background: var(--color-surface, #fff);
  transition: all 0.15s;
}

.crp-mode-btn--active {
  background: var(--color-primary, #1d4ed8);
  color: #fff;
  border-color: var(--color-primary, #1d4ed8);
}

.crp-filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  align-items: flex-end;
  padding: 0.75rem;
  background: var(--color-surface-alt, #f9fafb);
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 8px;
}

.crp-filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.crp-label {
  font-size: 0.73rem;
  font-weight: 600;
  color: var(--color-text-muted, #6b7280);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.crp-input, .crp-select {
  padding: 0.38rem 0.6rem;
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 5px;
  font-size: 0.875rem;
  background: var(--color-surface, #fff);
  color: var(--color-text, #111827);
}

.crp-input--sm, .crp-select--sm {
  font-size: 0.78rem;
  padding: 0.28rem 0.45rem;
}

.crp-load-btn {
  padding: 0.38rem 0.85rem;
  background: var(--color-primary, #1d4ed8);
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
  align-self: flex-end;
}

.crp-load-btn:disabled { opacity: 0.45; cursor: not-allowed; }

.crp-panel {
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 8px;
  overflow: hidden;
}

.crp-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: var(--color-surface-alt, #f9fafb);
  border-bottom: 1px solid var(--color-border, #e5e7eb);
}

.crp-panel-title {
  font-size: 0.95rem;
  font-weight: 700;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.crp-returning-badge {
  font-size: 0.72rem;
  background: #dbeafe;
  color: #1d4ed8;
  padding: 0.15rem 0.5rem;
  border-radius: 10px;
  font-weight: 600;
}

.crp-add-btn {
  padding: 0.3rem 0.75rem;
  background: #059669;
  color: #fff;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 600;
}

.crp-form-box {
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--color-border, #e5e7eb);
  background: color-mix(in srgb, #059669 4%, transparent);
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.crp-form-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
}

.crp-form-col {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
  min-width: 120px;
}

.crp-form-col--wide {
  flex: 3;
}

.crp-form-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.crp-save-btn {
  padding: 0.38rem 0.9rem;
  background: #059669;
  color: #fff;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
}

.crp-save-btn:disabled { opacity: 0.45; cursor: not-allowed; }

.crp-save-btn--sm {
  padding: 0.25rem 0.55rem;
  font-size: 0.75rem;
}

.crp-cancel-btn {
  padding: 0.38rem 0.75rem;
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 5px;
  cursor: pointer;
  font-size: 0.82rem;
  background: var(--color-surface, #fff);
}

.crp-apply-btn {
  padding: 0.45rem 1.1rem;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
}

.crp-apply-btn:disabled { opacity: 0.45; cursor: not-allowed; }

.crp-error {
  background: #fef2f2;
  border: 1px solid #fca5a5;
  color: #b91c1c;
  padding: 0.6rem 0.85rem;
  border-radius: 6px;
  font-size: 0.85rem;
  margin: 0.5rem 0;
}

.crp-success {
  background: #f0fdf4;
  border: 1px solid #86efac;
  color: #166534;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
}

.crp-empty {
  padding: 1.5rem;
  text-align: center;
  font-size: 0.875rem;
  color: var(--color-text-muted, #9ca3af);
}

.crp-table-wrapper {
  overflow-x: auto;
}

.crp-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.crp-table th {
  padding: 0.5rem 0.75rem;
  text-align: left;
  font-size: 0.73rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-muted, #9ca3af);
  background: var(--color-surface-alt, #f9fafb);
  border-bottom: 1px solid var(--color-border, #e5e7eb);
}

.crp-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--color-border, #f3f4f6);
  vertical-align: middle;
}

.crp-table tr:last-child td { border-bottom: none; }

.crp-td-muted {
  color: var(--color-text-muted, #9ca3af);
  font-style: italic;
}

.crp-player-name { font-weight: 600; }

.crp-alias {
  font-size: 0.78rem;
  color: var(--color-text-muted, #9ca3af);
  margin-left: 0.3rem;
}

.crp-status-badge {
  padding: 0.15rem 0.5rem;
  border-radius: 10px;
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: capitalize;
}

.crp-status-badge--active { background: #dcfce7; color: #166534; }
.crp-status-badge--inactive { background: #fee2e2; color: #991b1b; }
.crp-status-badge--unknown { background: #f3f4f6; color: #6b7280; }

.crp-returning-pill {
  background: #dbeafe;
  color: #1d4ed8;
  padding: 0.15rem 0.5rem;
  border-radius: 10px;
  font-size: 0.72rem;
  font-weight: 600;
}

.crp-edit-btn {
  padding: 0.2rem 0.55rem;
  font-size: 0.75rem;
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 4px;
  cursor: pointer;
  background: var(--color-surface, #fff);
}

.crp-inline-edit {
  display: flex;
  gap: 0.3rem;
  align-items: center;
  flex-wrap: wrap;
}

.crp-import-instructions {
  padding: 0.75rem 1rem;
  background: var(--color-surface-alt, #f9fafb);
  border-radius: 6px;
  font-size: 0.85rem;
}

.crp-import-instructions p { margin: 0 0 0.4rem; }

.crp-import-cols {
  background: #f3f4f6;
  padding: 0.4rem 0.6rem;
  border-radius: 4px;
  font-size: 0.78rem;
  overflow-x: auto;
  margin: 0.25rem 0;
}

.crp-textarea {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 5px;
  font-family: monospace;
  font-size: 0.8rem;
  background: var(--color-surface, #fff);
  resize: vertical;
  box-sizing: border-box;
}

.crp-preview {
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 0.85rem 1rem;
  background: #eff6ff;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.crp-preview-title {
  font-size: 0.95rem;
  font-weight: 700;
  margin: 0;
}

.crp-preview-blockers {
  background: #fef2f2;
  border: 1px solid #fca5a5;
  color: #991b1b;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  font-size: 0.82rem;
}

.crp-preview-warnings {
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #92400e;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  font-size: 0.82rem;
}

.crp-preview-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.crp-preview-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: #fff;
  border: 1px solid #bfdbfe;
  border-radius: 6px;
  padding: 0.5rem 0.85rem;
  min-width: 80px;
}

.crp-preview-stat-count {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--color-primary, #1d4ed8);
}

.crp-preview-stat-count--warn { color: #d97706; }
.crp-preview-stat-count--info { color: #059669; }

.crp-preview-stat-label {
  font-size: 0.72rem;
  color: var(--color-text-muted, #6b7280);
  text-align: center;
}

.crp-preview-section {
  font-size: 0.82rem;
}

.crp-preview-section--warn {
  background: #fffbeb;
  padding: 0.5rem 0.75rem;
  border-radius: 5px;
}

.crp-returning-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-top: 0.35rem;
}

.crp-returning-chip {
  background: #dbeafe;
  color: #1d4ed8;
  padding: 0.15rem 0.5rem;
  border-radius: 10px;
  font-size: 0.75rem;
  font-weight: 600;
}

.crp-import-result {
  border: 1px solid #86efac;
  border-radius: 8px;
  padding: 0.85rem 1rem;
  background: #f0fdf4;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.crp-result-list {
  font-size: 0.875rem;
  margin: 0;
  padding-left: 1.2rem;
}

.crp-result-list li { margin-bottom: 0.2rem; }
</style>
