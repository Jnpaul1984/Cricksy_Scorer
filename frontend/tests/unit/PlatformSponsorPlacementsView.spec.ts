import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import PlatformSponsorPlacementsView from '@/views/PlatformSponsorPlacementsView.vue';

const api = vi.hoisted(() => ({
  listPlatformSponsorPlacements: vi.fn(),
  approvePlatformSponsorPlacement: vi.fn(),
  takedownPlatformSponsorPlacement: vi.fn(),
  getPlatformSponsorVisibility: vi.fn(),
  setPlatformSponsorGlobalVisibility: vi.fn(),
  setPlatformSponsorOrganizationVisibility: vi.fn(),
  setPlatformSponsorPlacementVisibility: vi.fn(),
}));
const auth = vi.hoisted(() => ({ isSuper: true }));

vi.mock('@/services/schoolAdminApi', () => api);
vi.mock('@/stores/authStore', () => ({ useAuthStore: () => auth }));

const placement = {
  id: 'placement-1', organization_id: 'org-1', organization_label: 'North School',
  sponsor_name: 'Local Cricket Shop', category: 'local-sport', state: 'proposed' as const,
};
const visibility = {
  global_enabled: false,
  organizations: [
    { id: 'school-1', label: 'North School', type: 'school' as const, enabled: false },
    { id: 'club-1', label: 'North Club', type: 'club' as const, enabled: true },
  ],
  placements: [
    { id: 'sponsor-1', sponsor_name: 'School Sponsor', category: 'sports-equipment', orgid: 'school-1', state: 'approved' as const, enabled: false },
    { id: 'sponsor-2', sponsor_name: 'Club Sponsor', category: 'education', orgid: 'club-1', state: 'approved' as const, enabled: true },
  ],
  page: {
    organizations: { page: 1, page_size: 50, total: 2, pages: 1 },
    placements: { page: 1, page_size: 50, total: 2, pages: 1 },
  },
  states: ['proposed', 'approved'] as const,
};
const review = (items: typeof placement[], page = 1, pages = 1) => ({
  items, page: { page, page_size: 50, total: items.length, pages }, states: ['proposed', 'approved'] as const,
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolver, rejecter) => { resolve = resolver; reject = rejecter; });
  return { promise, resolve, reject };
}

beforeEach(() => {
  vi.resetAllMocks();
  auth.isSuper = true;
  api.listPlatformSponsorPlacements.mockResolvedValue(review([]));
  api.getPlatformSponsorVisibility.mockResolvedValue(visibility);
});
afterEach(() => vi.restoreAllMocks());

describe('PlatformSponsorPlacementsView', () => {
  it('does not fetch or expose review controls to a non-platform user', async () => {
    auth.isSuper = false;
    const wrapper = mount(PlatformSponsorPlacementsView);
    await flushPromises();
    expect(wrapper.get('[role="alert"]').text()).toContain('Platform administrator authority');
    expect(api.listPlatformSponsorPlacements).not.toHaveBeenCalled();
    expect(api.getPlatformSponsorVisibility).not.toHaveBeenCalled();
  });

  it('lists organization labels, approves a proposal, then takes it down immediately', async () => {
    api.listPlatformSponsorPlacements
      .mockResolvedValueOnce(review([placement]))
      .mockResolvedValueOnce(review([{ ...placement, state: 'approved' }]))
      .mockResolvedValueOnce(review([]));
    api.approvePlatformSponsorPlacement.mockResolvedValue({ id: placement.id, state: 'approved' });
    api.takedownPlatformSponsorPlacement.mockResolvedValue({ id: placement.id, state: 'taken_down' });
    const wrapper = mount(PlatformSponsorPlacementsView);
    await flushPromises();
    expect(wrapper.text()).toContain('North School');
    await wrapper.findAll('button').find((button) => button.text() === 'Approve')!.trigger('click');
    await flushPromises();
    expect(api.approvePlatformSponsorPlacement).toHaveBeenCalledWith('placement-1');
    expect(wrapper.text()).toContain('Approved');
    await wrapper.findAll('button').find((button) => button.text() === 'Take down')!.trigger('click');
    await flushPromises();
    expect(api.takedownPlatformSponsorPlacement).toHaveBeenCalledWith('placement-1');
    expect(wrapper.text()).toContain('No active sponsor placements.');
  });

  it('disables concurrent actions and keeps the row available after an action error', async () => {
    const pending = deferred<{ id: string; state: 'approved' }>();
    api.listPlatformSponsorPlacements.mockResolvedValue(review([placement]));
    api.approvePlatformSponsorPlacement.mockReturnValue(pending.promise);
    const wrapper = mount(PlatformSponsorPlacementsView);
    await flushPromises();
    const approve = wrapper.findAll('button').find((button) => button.text() === 'Approve')!;
    await approve.trigger('click');
    expect(approve.attributes('disabled')).toBeDefined();
    pending.reject(new Error('Approval denied'));
    await flushPromises();
    expect(wrapper.get('[role="alert"]').text()).toContain('Approval denied');
    expect(wrapper.text()).toContain('Local Cricket Shop');
  });

  it('reloads the authoritative queue after replacement approval so a superseded sibling is not active', async () => {
    const previous = { ...placement, id: 'placement-old', sponsor_name: 'Previous sponsor', state: 'approved' as const };
    const replacement = { ...placement, id: 'placement-new', sponsor_name: 'Replacement sponsor' };
    api.listPlatformSponsorPlacements
      .mockResolvedValueOnce(review([previous, replacement]))
      .mockResolvedValueOnce(review([{ ...replacement, state: 'approved' }]));
    api.approvePlatformSponsorPlacement.mockResolvedValue({ id: replacement.id, state: 'approved' });

    const wrapper = mount(PlatformSponsorPlacementsView);
    await flushPromises();
    expect(wrapper.text()).toContain('Previous sponsor');
    await wrapper.findAll('button').find((button) => button.text() === 'Approve')!.trigger('click');
    await flushPromises();

    expect(api.listPlatformSponsorPlacements).toHaveBeenCalledTimes(2);
    expect(wrapper.text()).toContain('Replacement sponsor');
    expect(wrapper.text()).not.toContain('Previous sponsor');
    expect(wrapper.findAll('button').some((button) => button.text() === 'Take down')).toBe(true);
  });

  it('shows global, School, Club, and individual sponsor visibility controls', async () => {
    api.getPlatformSponsorVisibility
      .mockResolvedValueOnce(visibility)
      .mockResolvedValueOnce({ ...visibility, global_enabled: true })
      .mockResolvedValue(visibility);
    const wrapper = mount(PlatformSponsorPlacementsView);
    await flushPromises();
    expect(wrapper.text()).toContain('Global visibility');
    expect(wrapper.text()).toContain('North School');
    expect(wrapper.text()).toContain('North Club');
    expect(wrapper.text()).toContain('School Sponsor');
    expect(wrapper.text()).toContain('sports equipment, education, ordinary food businesses, and local services');

    api.setPlatformSponsorGlobalVisibility.mockResolvedValue({ ...visibility, global_enabled: true });
    await wrapper.findAll('button').find((button) => button.text() === 'Turn global visibility on')!.trigger('click');
    await flushPromises();
    expect(api.setPlatformSponsorGlobalVisibility).toHaveBeenCalledWith(true, { organizationPage: 1, placementPage: 1, pageSize: 50 });
    expect(wrapper.text()).toContain('Turn global visibility off');

    api.setPlatformSponsorOrganizationVisibility.mockResolvedValue(visibility);
    await wrapper.findAll('button').find((button) => button.text() === 'Turn organization on')!.trigger('click');
    await flushPromises();
    expect(api.setPlatformSponsorOrganizationVisibility).toHaveBeenCalledWith('school-1', true, { organizationPage: 1, placementPage: 1, pageSize: 50 });

    api.setPlatformSponsorPlacementVisibility.mockResolvedValue(visibility);
    await wrapper.findAll('button').find((button) => button.text() === 'Turn sponsor on')!.trigger('click');
    await flushPromises();
    expect(api.setPlatformSponsorPlacementVisibility).toHaveBeenCalledWith('sponsor-1', true, { organizationPage: 1, placementPage: 1, pageSize: 50 });
  });

  it('keeps visibility controls disabled while a mutation is pending and reports mutation errors', async () => {
    const pending = deferred<typeof visibility>();
    api.setPlatformSponsorGlobalVisibility.mockReturnValue(pending.promise);
    const wrapper = mount(PlatformSponsorPlacementsView);
    await flushPromises();
    const global = wrapper.findAll('button').find((button) => button.text() === 'Turn global visibility on')!;
    await global.trigger('click');
    expect(global.attributes('disabled')).toBeDefined();
    pending.reject(new Error('Global gate denied'));
    await flushPromises();
    expect(wrapper.get('[role="alert"]').text()).toContain('Global gate denied');
  });

  it('keeps a sponsor control accessible when organization and placement pages do not overlap', async () => {
    const mismatchedPages = {
      ...visibility,
      organizations: [visibility.organizations[0]],
      placements: [visibility.placements[1]],
      page: {
        organizations: { page: 1, page_size: 50, total: 51, pages: 2 },
        placements: { page: 2, page_size: 50, total: 51, pages: 2 },
      },
    };
    api.getPlatformSponsorVisibility.mockResolvedValue(mismatchedPages);
    const wrapper = mount(PlatformSponsorPlacementsView);
    await flushPromises();
    expect(wrapper.text()).toContain('Club Sponsor');
    expect(wrapper.text()).toContain('Organization club-1');
    expect(wrapper.text()).not.toContain('No sponsor placements for this organization.');
    expect(wrapper.findAll('button').some((button) => button.text() === 'Turn sponsor off')).toBe(true);
  });

  it('paginates review entries, organizations, and individual sponsor controls independently', async () => {
    const pagedVisibility = {
      ...visibility,
      page: {
        organizations: { page: 1, page_size: 50, total: 100, pages: 2 },
        placements: { page: 1, page_size: 50, total: 100, pages: 2 },
      },
    };
    api.listPlatformSponsorPlacements.mockResolvedValue(review([placement], 1, 2));
    api.getPlatformSponsorVisibility.mockResolvedValue(pagedVisibility);
    const wrapper = mount(PlatformSponsorPlacementsView);
    await flushPromises();
    await wrapper.findAll('button').find((button) => button.text() === 'Next review entries')!.trigger('click');
    await wrapper.findAll('button').find((button) => button.text() === 'Next organizations')!.trigger('click');
    await wrapper.findAll('button').find((button) => button.text() === 'Next sponsors')!.trigger('click');
    await flushPromises();
    expect(api.listPlatformSponsorPlacements).toHaveBeenLastCalledWith(2, 50);
    expect(api.getPlatformSponsorVisibility).toHaveBeenLastCalledWith(2, 2, 50);
    api.setPlatformSponsorGlobalVisibility.mockResolvedValue({
      ...pagedVisibility,
      page: {
        organizations: { ...pagedVisibility.page.organizations, page: 2 },
        placements: { ...pagedVisibility.page.placements, page: 2 },
      },
    });
    await wrapper.findAll('button').find((button) => button.text() === 'Turn global visibility on')!.trigger('click');
    await flushPromises();
    expect(api.setPlatformSponsorGlobalVisibility).toHaveBeenLastCalledWith(true, { organizationPage: 2, placementPage: 2, pageSize: 50 });
  });
});
