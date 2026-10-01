import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, ref } from 'vue';

import OrganizationCommunityView from '@/views/OrganizationCommunityView.vue';

const api = vi.hoisted(() => ({
  getPublicOrganizationCommunity: vi.fn(),
  getPublicOrganizationSponsorPlacement: vi.fn(),
  recordPublicSponsorPlacementEvent: vi.fn(),
}));
vi.mock('@/services/schoolAdminApi', () => api);

const community = (public_identifier: string) => ({
  public_identifier, display_name: 'North School', organization_type: 'school',
  branding: { logo_url: null, logo_alt_text: 'North School logo', fallback_text: 'N' }, competitions: [],
});
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolver) => { resolve = resolver; });
  return { promise, resolve };
}

beforeEach(() => { vi.resetAllMocks(); api.recordPublicSponsorPlacementEvent.mockResolvedValue({ accepted: true, duplicate: false }); vi.useFakeTimers(); });
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

describe('OrganizationCommunityView sponsor placement', () => {
  it('drops a deferred stale sponsor response after the public route changes', async () => {
    const staleSponsor = deferred<{ id: string; sponsor_name: string; sponsor_url: null; placement_surface: 'public_organization_homepage' }>();
    const identifier = ref('first');
    api.getPublicOrganizationCommunity.mockImplementation((value: string) => Promise.resolve(community(value)));
    api.getPublicOrganizationSponsorPlacement.mockImplementationOnce(() => staleSponsor.promise)
      .mockResolvedValueOnce({ id: 'current', sponsor_name: 'Current sponsor', sponsor_url: null, placement_surface: 'public_organization_homepage' });
    const wrapper = mount(OrganizationCommunityView, { props: { publicIdentifier: identifier.value } });
    await flushPromises();
    identifier.value = 'second';
    await wrapper.setProps({ publicIdentifier: identifier.value });
    await nextTick(); await flushPromises();
    staleSponsor.resolve({ id: 'stale', sponsor_name: 'Stale sponsor', sponsor_url: null, placement_surface: 'public_organization_homepage' });
    await flushPromises();
    expect(wrapper.text()).toContain('Current sponsor');
    expect(wrapper.text()).not.toContain('Stale sponsor');
  });

  it('polls every 30 seconds and removes a taken-down sponsor, then cleans up on unmount', async () => {
    api.getPublicOrganizationCommunity.mockResolvedValue(community('north'));
    api.getPublicOrganizationSponsorPlacement.mockResolvedValueOnce({ id: 'local', sponsor_name: 'Local sponsor', sponsor_url: null, placement_surface: 'public_organization_homepage' })
      .mockRejectedValueOnce(new Error('taken down'));
    const wrapper = mount(OrganizationCommunityView, { props: { publicIdentifier: 'north' } });
    await flushPromises();
    expect(wrapper.text()).toContain('Local sponsor');
    await vi.advanceTimersByTimeAsync(30_000);
    await flushPromises();
    expect(wrapper.text()).not.toContain('Local sponsor');
    expect(api.getPublicOrganizationSponsorPlacement).toHaveBeenCalledTimes(2);
    wrapper.unmount();
    await vi.advanceTimersByTimeAsync(30_000);
    expect(api.getPublicOrganizationSponsorPlacement).toHaveBeenCalledTimes(2);
  });

  it('reports one anonymous display per placement and a click without making public rendering depend on reporting', async () => {
    api.getPublicOrganizationCommunity.mockResolvedValue(community('north'));
    api.getPublicOrganizationSponsorPlacement.mockResolvedValue({ id: 'placement-1', sponsor_name: 'Local sponsor', sponsor_url: 'https://example.org', placement_surface: 'public_organization_homepage', reporting: { event_capability: 'opaque-capability' } });
    const wrapper = mount(OrganizationCommunityView, { props: { publicIdentifier: 'north' } });
    await flushPromises();
    expect(api.recordPublicSponsorPlacementEvent).toHaveBeenCalledWith('opaque-capability', 'display');
    await vi.advanceTimersByTimeAsync(30_000); await flushPromises();
    expect(api.recordPublicSponsorPlacementEvent).toHaveBeenCalledTimes(1);
    await wrapper.get('.sponsor-placement a').trigger('click');
    expect(api.recordPublicSponsorPlacementEvent).toHaveBeenLastCalledWith('opaque-capability', 'click');
  });
});
