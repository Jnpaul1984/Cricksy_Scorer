import { mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, reactive } from 'vue';

import {
  createCoachPrivatePlayer,
  getAnalysisHistory,
  listCoachPlayers,
  listVideoSessions,
  type VideoAnalysisJob,
  type VideoSession,
} from '@/services/coachPlusVideoService';
import CoachProPlusVideoSessionsView from '@/views/CoachProPlusVideoSessionsView.vue';

const authStoreMock = reactive({
  canCoach: false,
  isCoach: false,
  isCoachPro: false,
  isCoachProPlus: false,
  isSuperuser: false,
  currentUser: null,
  planName: 'free',
  role: 'free',
});

const videoStoreCleanup = vi.fn();
const videoStoreCreateSession = vi.fn();
const videoStoreMock = reactive({
  error: null as string | null,
  uploading: null as { status: string } | null,
  uploadProgress: 0,
  cleanup: videoStoreCleanup,
  createSession: videoStoreCreateSession,
});

vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => authStoreMock,
}));

vi.mock('@/stores/coachPlusVideoStore', () => ({
  useCoachPlusVideoStore: () => videoStoreMock,
}));

vi.mock('@/services/coachPlusVideoService', () => ({
  ApiError: class ApiError extends Error {},
  listVideoSessions: vi.fn(),
  listCoachPlayers: vi.fn(),
  createCoachPrivatePlayer: vi.fn(),
  getAnalysisHistory: vi.fn(),
  getVideoStreamUrl: vi.fn(),
  calculateCompliance: vi.fn(),
  getJobOutcomes: vi.fn(),
  generateCoachSuggestions: vi.fn(),
  getCoachSuggestions: vi.fn(),
}));

vi.mock('@/services/playerDevelopmentApi', () => ({
  PlayerDevelopmentApiError: class PlayerDevelopmentApiError extends Error {
    isUnauthorized() {
      return false;
    }

    isNotFound() {
      return false;
    }

    isConflict() {
      return false;
    }

    isValidationError() {
      return false;
    }
  },
  listPlayerDevelopmentPlans: vi.fn(),
  reviewPlayerDevelopmentPlan: vi.fn(),
}));

async function flushAsync() {
  await Promise.resolve();
  await nextTick();
  await Promise.resolve();
  await nextTick();
}

function mountView() {
  return mount(CoachProPlusVideoSessionsView, {
    global: {
      stubs: {
        RouterLink: { template: '<a><slot /></a>' },
        GoalsPanel: true,
        SessionComparison: true,
        CoachSuggestionsPanel: true,
        CoachingSkillRecommendationReviewCard: true,
        PlayerSummaryCard: true,
      },
    },
  });
}

describe('CoachProPlusVideoSessionsView', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.resetAllMocks();
    authStoreMock.canCoach = false;
    authStoreMock.isCoach = false;
    authStoreMock.isCoachPro = false;
    authStoreMock.isCoachProPlus = false;
    authStoreMock.isSuperuser = false;
    authStoreMock.currentUser = null;
    authStoreMock.planName = 'free';
    authStoreMock.role = 'free';
    videoStoreMock.error = null;
    videoStoreMock.uploading = null;
    videoStoreMock.uploadProgress = 0;
    videoStoreMock.cleanup = videoStoreCleanup;
    videoStoreMock.createSession = videoStoreCreateSession;
    vi.mocked(listVideoSessions).mockResolvedValue([]);
    vi.mocked(getAnalysisHistory).mockResolvedValue([]);
    vi.mocked(listCoachPlayers).mockResolvedValue([]);
  });

  it('shows the video sessions workspace for authorized org pro reviewers', async () => {
    authStoreMock.canCoach = true;
    authStoreMock.isCoachProPlus = true;
    authStoreMock.role = 'org_pro';

    const wrapper = mountView();
    await flushAsync();

    expect(wrapper.text()).toContain('Video Sessions');
    expect(wrapper.text()).not.toContain('Unlock Video Sessions');
  });

  it('records session-list render only after the visible loading gate clears', async () => {
    authStoreMock.canCoach = true;
    authStoreMock.isCoachProPlus = true;
    authStoreMock.role = 'coach_pro_plus';
    let finishSessionRequest!: (sessions: VideoSession[]) => void;
    vi.mocked(listVideoSessions).mockImplementation(
      () => new Promise((resolve) => (finishSessionRequest = resolve)),
    );

    let wrapper: ReturnType<typeof mountView> | undefined;
    let listWasVisibleAtEvent = false;
    vi.spyOn(console, 'info').mockImplementation((label, event) => {
      if (
        label === '[coach-performance]' &&
        (event as { operation?: string; phase?: string }).operation === 'coach_plus.session_list' &&
        (event as { phase?: string }).phase === 'render'
      ) {
        listWasVisibleAtEvent = Boolean(
          wrapper?.find('.sessions-list').exists() && !wrapper.find('.loading').exists(),
        );
      }
    });

    wrapper = mountView();
    await vi.waitFor(() => expect(listVideoSessions).toHaveBeenCalled());
    finishSessionRequest([
      {
        id: 'session-visible',
        title: 'Visible session',
        status: 'ready',
        player_ids: [],
      } as VideoSession,
    ]);
    await flushAsync();

    expect(listWasVisibleAtEvent).toBe(true);
    expect(wrapper.find('.sessions-list').text()).toContain('Visible session');
  });

  it('records the visible Analysis Results modal render once', async () => {
    authStoreMock.canCoach = true;
    authStoreMock.isCoachPro = true;
    authStoreMock.role = 'coach_pro';

    let wrapper: ReturnType<typeof mountView> | undefined;
    let resultsWereVisibleAtEvent = false;
    const resultsEvents: unknown[] = [];
    vi.spyOn(console, 'info').mockImplementation((label, event) => {
      const telemetry = event as { operation?: string; phase?: string };
      if (
        label === '[coach-performance]' &&
        telemetry.operation === 'coach_plus.analysis_results' &&
        telemetry.phase === 'render'
      ) {
        resultsEvents.push(event);
        resultsWereVisibleAtEvent = Boolean(
          wrapper?.findAll('h2').some((heading) => heading.text() === 'Analysis Results'),
        );
      }
    });

    wrapper = mountView();
    await flushAsync();
    const now = new Date().toISOString();
    const job = {
      id: 'job-visible-results',
      session_id: 'session-visible-results',
      sample_fps: 10,
      include_frames: false,
      status: 'done',
      error_message: null,
      sqs_message_id: null,
      results: null,
      created_at: now,
      started_at: now,
      completed_at: now,
      updated_at: now,
    } as VideoAnalysisJob;

    await (
      wrapper.vm as unknown as { viewJobResults: (value: VideoAnalysisJob) => Promise<void> }
    ).viewJobResults(job);

    expect(resultsWereVisibleAtEvent).toBe(true);
    expect(resultsEvents).toHaveLength(1);
  });

  it('uses player-centered create form fields instead of manual player ID textarea', async () => {
    authStoreMock.canCoach = true;
    authStoreMock.isCoachProPlus = true;
    authStoreMock.role = 'coach_pro_plus';

    vi.mocked(listCoachPlayers).mockResolvedValue([
      {
        player_id: 'player-1',
        player_name: 'Player One',
        date_of_birth: null,
        assignment_active: true,
      },
    ]);

    const wrapper = mountView();
    await flushAsync();

    await wrapper.find('button.btn-primary').trigger('click');
    await flushAsync();

    expect(wrapper.text()).toContain('Discipline');
    expect(wrapper.text()).toContain('Add coaching player');
    expect(wrapper.text()).not.toContain('existing Match Setup workflow');
    expect(wrapper.text()).not.toContain('Player IDs (comma-separated)');
  });

  it('creates a private coaching player and immediately selects it', async () => {
    authStoreMock.canCoach = true;
    authStoreMock.isCoachProPlus = true;
    authStoreMock.role = 'coach_pro_plus';

    const createdPlayer = {
      player_id: 'coach-player-new',
      player_name: 'Private Player',
      date_of_birth: '2010-06-15',
      assignment_active: true,
    };
    vi.mocked(listCoachPlayers).mockResolvedValueOnce([]).mockResolvedValueOnce([createdPlayer]);
    vi.mocked(createCoachPrivatePlayer).mockResolvedValue(createdPlayer);

    const wrapper = mountView();
    await flushAsync();
    await wrapper.find('button.btn-primary').trigger('click');
    await flushAsync();
    await wrapper.find('.btn-link-inline').trigger('click');
    await wrapper.find('#new-player-name').setValue('Private Player');
    await wrapper.find('#new-player-dob').setValue('2010-06-15');
    await wrapper.find('.player-create-panel .btn-primary').trigger('click');
    await flushAsync();

    expect(createCoachPrivatePlayer).toHaveBeenCalledWith({
      player_name: 'Private Player',
      date_of_birth: '2010-06-15',
    });
    expect((wrapper.find('#primary-player').element as HTMLSelectElement).value).toBe(
      'coach-player-new',
    );
    expect(wrapper.findAll('#primary-player option[value="coach-player-new"]')).toHaveLength(1);
    expect(wrapper.text()).not.toContain('Quick add coaching player');
  });

  it('preserves a created player when refresh fails and reconciles it without duplicates later', async () => {
    authStoreMock.canCoach = true;
    authStoreMock.isCoachProPlus = true;
    authStoreMock.role = 'coach_pro_plus';

    const createdPlayer = {
      player_id: 'coach-player-preserved',
      player_name: 'Preserved Player',
      date_of_birth: null,
      assignment_active: true,
    };
    vi.mocked(listCoachPlayers)
      .mockResolvedValueOnce([])
      .mockRejectedValueOnce(new Error('Temporary player refresh failure'))
      .mockResolvedValueOnce([createdPlayer]);
    vi.mocked(createCoachPrivatePlayer).mockResolvedValue(createdPlayer);

    const wrapper = mountView();
    await flushAsync();
    await wrapper.find('button.btn-primary').trigger('click');
    await flushAsync();
    await wrapper.find('.btn-link-inline').trigger('click');
    await wrapper.find('#new-player-name').setValue('Preserved Player');
    await wrapper.find('.player-create-panel .btn-primary').trigger('click');
    await flushAsync();

    const selector = wrapper.find('#primary-player');
    expect((selector.element as HTMLSelectElement).value).toBe('coach-player-preserved');
    expect(wrapper.findAll('#primary-player option[value="coach-player-preserved"]')).toHaveLength(
      1,
    );
    expect(wrapper.text()).toContain('Temporary player refresh failure');
    expect(wrapper.text()).not.toContain('Quick add coaching player');
    expect(createCoachPrivatePlayer).toHaveBeenCalledTimes(1);

    await (
      wrapper.vm as unknown as { fetchAssignedPlayers: () => Promise<void> }
    ).fetchAssignedPlayers();
    await flushAsync();

    expect(wrapper.findAll('#primary-player option[value="coach-player-preserved"]')).toHaveLength(
      1,
    );
    expect((wrapper.find('#primary-player').element as HTMLSelectElement).value).toBe(
      'coach-player-preserved',
    );
    expect(wrapper.text()).not.toContain('Temporary player refresh failure');
    expect(createCoachPrivatePlayer).toHaveBeenCalledTimes(1);
  });

  it('keeps the upgrade gate for users without coach access', async () => {
    const wrapper = mountView();
    await flushAsync();

    expect(wrapper.text()).toContain('Unlock Video Sessions');
  });

  it('renders the shared player presentation and suppresses legacy priorities for V2 jobs', async () => {
    authStoreMock.canCoach = true;
    authStoreMock.isCoachPro = true;
    authStoreMock.role = 'coach_pro';

    const wrapper = mountView();
    await flushAsync();

    const vm = wrapper.vm as unknown as {
      showResultsModal: boolean;
      selectedJob: VideoAnalysisJob | null;
    };

    vm.selectedJob = {
      id: 'job-reps',
      session_id: 'session-reps',
      sample_fps: 10,
      include_frames: false,
      status: 'done',
      error_message: null,
      sqs_message_id: null,
      deep_results: {
        pose_summary: {
          total_frames: 120,
          sampled_frames: 30,
          frames_with_pose: 28,
          detection_rate_percent: 93,
          video_fps: 30,
        },
        report: { summary: 'Done' },
        findings: {
          findings: [
            {
              code: 'ELBOW_DROP',
              title: 'Legacy High elbow issue',
              severity: 'high',
              why_it_matters: 'Unsupported injury-risk claim',
              suggested_drills: ['Stop all match practice until technique improves'],
            },
          ],
        },
        meta: {
          repetition_segmentation: {
            enabled: true,
            validity_state: 'VALID',
            repetitions_count: 1,
          },
          phase_recognition: {
            enabled: true,
            validity_state: 'LOW_CONFIDENCE',
            phases_count: 1,
          },
        },
        v2: {
          repetitions: [
            {
              repetition_id: 'rep-1',
              discipline: 'bowling',
              action_type: 'bowling_delivery',
              start_ts: 0.5,
              end_ts: 1.1,
              start_frame: 15,
              end_frame: 33,
              segmentation_confidence: 0.84,
              validity_state: 'VALID',
            },
          ],
          phases: [
            {
              phase_id: 'rep-1:phase:1',
              repetition_id: 'rep-1',
              phase_name: 'contact_proxy_window',
              start_ts: 0.8,
              end_ts: 0.9,
              start_frame: 24,
              end_frame: 27,
              confidence: 0.58,
              validity_state: 'LOW_CONFIDENCE',
              requires_object_evidence: true,
              limitations: ['proxy only'],
            },
          ],
        },
      },
      v2_coaching_report: {
        report_version: 'coaching_analysis_report.v2',
        source: 'persisted_video_analysis_v2',
        player_presentation: {
          presentation_version: 'coaching_analysis_presentation.v1',
          discipline: 'pace_bowling',
          discipline_label: 'Pace bowling',
          usable_repetition_count: 1,
          repetition_count: 1,
          analysis_quality:
            'The recording provided clear evidence for the available technique review.',
          session_summary: 'We identified 1 usable delivery.',
          insufficient_evidence: { active: false },
          movement_summary: {
            summary: '1 usable delivery identified.',
            phase_confidence_summary:
              '1 phase observation across 1 movement phase: 1 low confidence.',
          },
          repetitions: [
            {
              repetition_id: 'rep-1',
              label: 'Delivery 1',
              confidence: 'High confidence',
              validity: null,
              start_ts: 0.5,
              end_ts: 1.1,
            },
          ],
          phases: [
            {
              phase_id: 'rep-1:phase:1',
              label: 'Release estimate',
              repetition_label: 'Delivery 1',
              confidence: 'Low confidence',
              validity: 'Estimate only',
              proxy: 'Approximate movement phase',
            },
          ],
          metrics: [
            {
              metric_id: 'pace_bowling_release_proxy_bowling_arm_angle_deg',
              label: 'Bowling-arm angle near release',
              phase: 'Release estimate',
              value: '145.0°',
              confidence: 'High confidence',
              validity: null,
              proxy: 'Approximate measurement',
              classification: 'Needs attention',
            },
            {
              metric_id: 'unavailable-test-metric',
              label: 'Unavailable test measurement',
              phase: 'Release estimate',
              value: 'Unavailable',
              confidence: 'Confidence unavailable',
              validity: 'Could not measure clearly',
              proxy: null,
              classification: null,
            },
          ],
          current_session_positives: [
            {
              metric_id: 'pace_bowling_approach_head_stability_score',
              title: 'Head stability during the approach',
              observation: 'This measurement looked good in this session.',
              value: '82%',
              phase: 'Approach',
              confidence: 'High confidence',
              validity: 'Estimate only',
              proxy: 'Approximate measurement',
            },
            {
              metric_id: 'pace_bowling_follow_through_balance_drift_ratio',
              title: 'Balance through the follow through',
              observation: 'This measurement looked good in this session.',
              value: '75%',
              phase: 'Follow through',
              confidence: 'High confidence',
              validity: null,
              proxy: null,
            },
          ],
          strengths: [],
          priorities: [
            {
              metric_id: 'pace_bowling_release_proxy_bowling_arm_angle_deg',
              title: 'Bowling-arm angle near release',
              observation: 'This pattern appeared in the comparable deliveries.',
              repetition_count: 3,
              repetition_labels: ['Delivery 1'],
              confidence: 'High confidence',
              limitations: [],
              why_it_matters: 'A repeatable release can improve control.',
              proxy: 'Approximate measurement',
            },
            {
              metric_id: 'pace_bowling_release_proxy_trunk_lean_deg',
              title: 'Body lean near release',
              observation: 'Comparable evidence was not persisted for this pattern.',
              repetition_count: null,
              repetition_labels: [],
              confidence: 'High confidence',
              limitations: [],
              why_it_matters: 'A repeatable release can improve control.',
              proxy: 'Approximate measurement',
            },
          ],
          governed_actions: [
            {
              action_id: 'pace-release-follow-through',
              linked_metric_id: 'pace_bowling_release_proxy_bowling_arm_angle_deg',
              linked_metric_ids: ['pace_bowling_release_proxy_bowling_arm_angle_deg'],
              title: 'Release and follow-through',
              observed_issue: 'Bowling-arm angle near release',
              coaching_goal: 'Repeat the release shape.',
              cue: 'Reach tall through release.',
              drills: ['Walk-through delivery'],
              coach_watches_for: 'A repeatable arm path.',
              reassess: 'Compare the release estimate.',
              requires_coach_approval: true,
              review_status: 'approved_for_coach_review',
            },
          ],
          consistency: [],
          representative_repetitions: {
            best: { available: false, label: null, rationale: null, confidence: null },
            needs_work: { available: false, label: null, rationale: null, confidence: null },
          },
          progress: {
            state: 'Baseline established',
            summary:
              "This is the player's first recorded assessment. Future comparable sessions will show what improved, stayed consistent, or needs more work.",
            items: [],
          },
        },
      },
      results: null,
      created_at: new Date().toISOString(),
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    } as unknown as VideoAnalysisJob;
    vm.showResultsModal = true;
    await flushAsync();

    const text = wrapper.text();
    expect(text).toContain('How did I do?');
    expect(text).toContain('Delivery 1');
    expect(text).toContain('Release estimate');
    expect(text).toContain('Estimate only');
    expect(text).toContain('Approximate movement phase');
    expect(text).toContain('Bowling-arm angle near release');
    expect(text).toContain('145.0°');
    const unavailableMetric = wrapper
      .findAll('.phase-row')
      .find((row) => row.text().includes('Unavailable test measurement'));
    expect(unavailableMetric?.find('.status-text').text().replace(/\s+/g, ' ').trim()).toBe(
      'Confidence unavailable • Could not measure clearly',
    );
    expect(text).toContain('Release and follow-through');
    expect(text).toContain('What looked good in this session');
    expect(text).toContain('Head stability during the approach');
    expect(text).toContain('This measurement looked good in this session');
    const positiveCards = wrapper.findAll('.finding-card');
    const caveatedPositive = positiveCards.find((card) =>
      card.text().includes('Head stability during the approach'),
    );
    expect(caveatedPositive?.find('.status-text').text().replace(/\s+/g, ' ').trim()).toBe(
      '82% • Approach • High confidence • Approximate measurement • Estimate only',
    );
    const normalPositive = positiveCards.find((card) =>
      card.text().includes('Balance through the follow through'),
    );
    expect(normalPositive?.find('.status-text').text().replace(/\s+/g, ' ').trim()).toBe(
      '75% • Follow through • High confidence',
    );
    expect(text).not.toContain('No repeatable strengths could be confirmed');
    expect(text).toContain('3 comparable repetitions');
    expect(text).not.toContain('Comparable repetition count unavailable');
    expect(text).not.toContain('null comparable repetitions');
    expect(text).not.toContain('0 comparable repetitions');
    expect(wrapper.find('details.movement-evidence').attributes('open')).toBeUndefined();
    expect(wrapper.findAll('h3').map((heading) => heading.text())).not.toContain('Priorities');
    expect(text).not.toContain('rep-1:phase:1');
    expect(text).not.toContain('pace_bowling_release_proxy_bowling_arm_angle_deg');
    expect(text).not.toContain('Legacy High elbow issue');
    expect(text).not.toContain('Rating: High Risk');
    expect(text).not.toContain('injury-risk');
    expect(text).not.toContain('Stop all match practice');
  });

  it('shows one V2 insufficient-evidence summary without legacy findings or actions', async () => {
    authStoreMock.canCoach = true;
    authStoreMock.isCoachPro = true;
    authStoreMock.role = 'coach_pro';
    const wrapper = mountView();
    await flushAsync();
    const vm = wrapper.vm as unknown as {
      showResultsModal: boolean;
      selectedJob: VideoAnalysisJob | null;
    };
    const now = new Date().toISOString();
    vm.selectedJob = {
      id: 'job-insufficient',
      session_id: 'session-1',
      sample_fps: 10,
      include_frames: false,
      status: 'done',
      error_message: null,
      sqs_message_id: null,
      results: null,
      deep_results: {
        v2: {
          repetitions: [
            {
              repetition_id: 'raw-delivery-1',
              discipline: 'pace_bowling',
              validity_state: 'VALID',
            },
          ],
        },
        findings: {
          findings: [
            { code: 'HEAD_MOVEMENT', title: 'Legacy High hip-shoulder issue', severity: 'high' },
          ],
        },
      },
      v2_coaching_report: {
        report_version: 'coaching_analysis_report.v2',
        source: 'persisted_video_analysis_v2',
        player_presentation: {
          presentation_version: 'coaching_analysis_presentation.v1',
          discipline: 'pace_bowling',
          discipline_label: 'Pace bowling',
          usable_repetition_count: 2,
          repetition_count: 2,
          analysis_quality: 'There was not enough clear evidence for reliable technique judgments.',
          session_summary: 'We identified 2 usable deliveries.',
          insufficient_evidence: {
            active: true,
            title: 'We detected 2 deliveries.',
            summary:
              'That is enough to review the movement phases, but not enough to make reliable technique judgments yet.',
            recommendation: 'Record at least 3 comparable deliveries for a fuller analysis.',
            minimum_repetitions: 3,
          },
          movement_summary: {
            summary: '2 usable deliveries identified.',
            phase_confidence_summary: 'Phase evidence unavailable.',
          },
          repetitions: [],
          phases: [],
          metrics: [],
          current_session_positives: [],
          strengths: [],
          priorities: [],
          governed_actions: [],
          consistency: [],
          representative_repetitions: {
            best: { available: false, label: null, rationale: null, confidence: null },
            needs_work: { available: false, label: null, rationale: null, confidence: null },
          },
          progress: {
            state: 'Baseline established',
            summary:
              "This is the player's first recorded assessment. Future comparable sessions will show what improved, stayed consistent, or needs more work.",
            items: [],
          },
        },
      },
      created_at: now,
      started_at: now,
      completed_at: now,
      updated_at: now,
    } as VideoAnalysisJob;
    vm.showResultsModal = true;
    await flushAsync();

    const text = wrapper.text();
    expect(text.match(/We detected 2 deliveries\./g)).toHaveLength(1);
    expect(text).toContain('No governed training action is available');
    expect(wrapper.findAll('h3').map((heading) => heading.text())).not.toContain('Priorities');
    expect(text).not.toContain('Legacy High hip-shoulder issue');
  });

  it('retains the legacy Priorities block for historical non-V2 jobs', async () => {
    authStoreMock.canCoach = true;
    authStoreMock.isCoachPro = true;
    authStoreMock.role = 'coach_pro';
    const wrapper = mountView();
    await flushAsync();
    const vm = wrapper.vm as unknown as {
      showResultsModal: boolean;
      selectedJob: VideoAnalysisJob | null;
    };
    const now = new Date().toISOString();
    vm.selectedJob = {
      id: 'legacy-job',
      session_id: 'legacy-session',
      sample_fps: 10,
      include_frames: false,
      status: 'done',
      error_message: null,
      sqs_message_id: null,
      results: {
        findings: {
          findings: [
            { code: 'HEAD_MOVEMENT', title: 'Historical head movement', severity: 'medium' },
          ],
        },
      },
      created_at: now,
      started_at: now,
      completed_at: now,
      updated_at: now,
    } as VideoAnalysisJob;
    vm.showResultsModal = true;
    await flushAsync();

    expect(wrapper.findAll('h3').map((heading) => heading.text())).toContain('Priorities');
    expect(wrapper.text()).toContain('Historical head movement');
  });
});
