import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';

import { schoolContextKey, type SchoolContext } from '@/composables/useSchoolContext';
import * as schoolApi from '@/services/schoolAdminApi';
import SchoolCompetitionsView from '@/views/school/SchoolCompetitionsView.vue';

vi.mock('@/services/schoolAdminApi');
const currentOrganizationId = ref('org-a');

const competition = (id: string) => ({
  id,
  organization_id: 'org-a',
  name: `Competition ${id}`,
  description: null,
  tournament_type: 'league' as const,
  start_date: null,
  end_date: null,
  status: 'upcoming' as const,
  created_at: '',
  updated_at: '',
});

const fixture = {
  id: 'fixture-a',
  tournament_id: 'competition-a',
  team_a_id: 'team-a',
  team_b_id: 'team-b',
  team_a_name: 'Synthetic Adult XI',
  team_b_name: 'Practice Adults',
  match_number: 1,
  venue: null,
  scheduled_date: null,
  game_id: 'game-a',
  status: 'scheduled' as const,
  created_at: '',
  updated_at: '',
};

const association = (youtube_video_id: string | null) => ({
  game_id: 'game-a',
  youtube_video_id,
  updated_by_user_id: 'synthetic-adult-owner',
  updated_at: '2026-10-13T00:00:00Z',
});

function mountEditor(competitionRows = [competition('competition-a')]) {
  currentOrganizationId.value = 'org-a';
  const allowed = computed(() => true);
  const context = {
    organizationId: computed(() => currentOrganizationId.value),
    terminology: computed(() => ({ kindLabel: 'Club' })),
    canViewCompetitions: allowed,
    canManageCompetitions: allowed,
    canManageCommunity: allowed,
    canDeleteCompetitions: allowed,
    canLinkFixtures: allowed,
  } as unknown as SchoolContext;
  vi.mocked(schoolApi.listSchoolCompetitions).mockResolvedValue(competitionRows);
  vi.mocked(schoolApi.listSchoolTeams).mockResolvedValue([]);
  vi.mocked(schoolApi.listSchoolCompetitionTeams).mockResolvedValue([]);
  vi.mocked(schoolApi.listSchoolCompetitionFixtures).mockResolvedValue([fixture]);
  vi.mocked(schoolApi.getSchoolStandings).mockResolvedValue({
    competition_id: 'competition-a',
    entries: [],
    unresolved_completed_games: 0,
  });
  return mount(SchoolCompetitionsView, {
    global: { provide: { [schoolContextKey as symbol]: context } },
  });
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((settle) => {
    resolve = settle;
  });
  return { promise, resolve: (value: T) => resolve(value) };
}

async function clickVideoEditor(wrapper: ReturnType<typeof mount>) {
  const button = wrapper.findAll('button').find((candidate) => (
    candidate.text().includes('Associate YouTube video')
    || candidate.text().includes('Close YouTube video editor')
  ));
  if (!button) throw new Error('YouTube video editor control was not rendered');
  await button.trigger('click');
}

describe('organization fixture YouTube editor async state', () => {
  afterEach(() => {
    currentOrganizationId.value = 'org-a';
    vi.resetAllMocks();
  });

  it('hides controls while loading and ignores a late response after close and reopen', async () => {
    const oldResponse = deferred<Awaited<ReturnType<typeof schoolApi.getSchoolFixtureYoutubeVideo>>>();
    const currentResponse = deferred<Awaited<ReturnType<typeof schoolApi.getSchoolFixtureYoutubeVideo>>>();
    vi.mocked(schoolApi.getSchoolFixtureYoutubeVideo)
      .mockReturnValueOnce(oldResponse.promise)
      .mockReturnValueOnce(currentResponse.promise);
    const wrapper = mountEditor();
    await flushPromises();

    await clickVideoEditor(wrapper);
    expect(wrapper.find('#youtube-video-fixture-a').exists()).toBe(false);
    expect(wrapper.text()).toContain('Loading the current video association');
    await clickVideoEditor(wrapper);
    await clickVideoEditor(wrapper);

    currentResponse.resolve(association('AbCdEf123_-'));
    await flushPromises();
    expect((wrapper.get('#youtube-video-fixture-a').element as HTMLInputElement).value)
      .toBe('https://youtu.be/AbCdEf123_-');

    oldResponse.resolve(association('ZyXwVu987_-'));
    await flushPromises();
    expect((wrapper.get('#youtube-video-fixture-a').element as HTMLInputElement).value)
      .toBe('https://youtu.be/AbCdEf123_-');
    wrapper.unmount();
  });

  it('serializes Save and Remove and updates from each confirmed mutation response', async () => {
    const saveResponse = deferred<Awaited<ReturnType<typeof schoolApi.updateSchoolFixtureYoutubeVideo>>>();
    vi.mocked(schoolApi.getSchoolFixtureYoutubeVideo).mockResolvedValue(association('AbCdEf123_-'));
    vi.mocked(schoolApi.updateSchoolFixtureYoutubeVideo)
      .mockReturnValueOnce(saveResponse.promise)
      .mockResolvedValueOnce(association(null));
    const wrapper = mountEditor();
    await flushPromises();
    await clickVideoEditor(wrapper);
    await flushPromises();

    const input = wrapper.get('#youtube-video-fixture-a');
    await input.setValue('https://youtube.com/watch?v=ZyXwVu987_-&list=synthetic');
    await wrapper.get('form.video-editor-form').trigger('submit');
    await flushPromises();
    const remove = wrapper.get('.video-editor-form button.danger');
    expect((remove.element as HTMLButtonElement).disabled).toBe(true);
    await remove.trigger('click');
    expect(schoolApi.updateSchoolFixtureYoutubeVideo).toHaveBeenCalledTimes(1);

    saveResponse.resolve(association('ZyXwVu987_-'));
    await flushPromises();
    expect((input.element as HTMLInputElement).value).toBe('https://youtu.be/ZyXwVu987_-');
    await wrapper.get('.video-editor-form button.danger').trigger('click');
    await flushPromises();
    expect(schoolApi.updateSchoolFixtureYoutubeVideo).toHaveBeenNthCalledWith(
      2,
      'org-a',
      'competition-a',
      'fixture-a',
      'game-a',
      null,
    );
    expect(wrapper.text()).toContain('YouTube association removed');
    expect((input.element as HTMLInputElement).value).toBe('');
    wrapper.unmount();
  });

  it('invalidates a pending editor read when switching competitions and on unmount', async () => {
    const oldResponse = deferred<Awaited<ReturnType<typeof schoolApi.getSchoolFixtureYoutubeVideo>>>();
    vi.mocked(schoolApi.getSchoolFixtureYoutubeVideo).mockReturnValue(oldResponse.promise);
    const wrapper = mountEditor([competition('competition-a'), competition('competition-b')]);
    await flushPromises();
    await clickVideoEditor(wrapper);
    const competitionSelect = wrapper.findAll('select').find((select) => (
      select.find('option[value="competition-b"]').exists()
    ));
    if (!competitionSelect) throw new Error('Competition selector was not rendered');
    await competitionSelect.setValue('competition-b');
    await flushPromises();

    oldResponse.resolve(association('AbCdEf123_-'));
    await flushPromises();
    expect(wrapper.find('#youtube-video-fixture-a').exists()).toBe(false);
    wrapper.unmount();
  });

  it('invalidates a pending read when the active organization changes', async () => {
    const pending = deferred<Awaited<ReturnType<typeof schoolApi.getSchoolFixtureYoutubeVideo>>>();
    vi.mocked(schoolApi.getSchoolFixtureYoutubeVideo).mockReturnValue(pending.promise);
    const wrapper = mountEditor();
    await flushPromises();
    await clickVideoEditor(wrapper);

    currentOrganizationId.value = 'org-b';
    await flushPromises();
    pending.resolve(association('AbCdEf123_-'));
    await flushPromises();
    expect(wrapper.find('#youtube-video-fixture-a').exists()).toBe(false);
    wrapper.unmount();
  });
});
