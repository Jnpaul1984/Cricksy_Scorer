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

let observers: Array<{ callback: IntersectionObserverCallback; disconnected: boolean }> = [];
class MockIntersectionObserver {
  callback: IntersectionObserverCallback;
  disconnected = false;
  constructor(callback: IntersectionObserverCallback) { this.callback = callback; observers.push(this); }
  observe() {}
  disconnect() { this.disconnected = true; }
  unobserve() {}
  takeRecords() { return []; }
}

const community = (public_identifier: string) => ({
  public_identifier, display_name: 'North School', organization_type: 'school',
  branding: { logo_url: null, logo_alt_text: 'North School logo', fallback_text: 'N' }, competitions: [],
});
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolver) => { resolve = resolver; });
  return { promise, resolve };
}

beforeEach(() => {
  vi.resetAllMocks();
  observers = [];
  vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);
  Object.defineProperty(window, 'IntersectionObserver', { configurable: true, value: MockIntersectionObserver });
  Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' });
  api.recordPublicSponsorPlacementEvent.mockResolvedValue({ accepted: true, duplicate: false });
  vi.useFakeTimers();
});
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
    await flushPromises(); await nextTick();
    expect(wrapper.text()).toContain('Local sponsor');
    expect(window.IntersectionObserver).toBe(MockIntersectionObserver);
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

  it('reports a display only after a visible threshold, once per public placement despite polling, and uses the separate click capability', async () => {
    api.getPublicOrganizationCommunity.mockResolvedValue(community('north'));
    api.getPublicOrganizationSponsorPlacement
      .mockResolvedValueOnce({ sponsor_name: 'Local sponsor', sponsor_url: 'https://example.org', placement_surface: 'public_organization_homepage', reporting: { display_capability: 'display-capability', click_capability: 'click-capability', report_view_key: 'stable-placement-revision' } })
      .mockResolvedValueOnce({ sponsor_name: 'Local sponsor', sponsor_url: 'https://example.org', placement_surface: 'public_organization_homepage', reporting: { display_capability: 'rotated-display-capability', click_capability: 'rotated-click-capability', report_view_key: 'stable-placement-revision' } })
      .mockResolvedValueOnce({ sponsor_name: 'Replacement sponsor', sponsor_url: 'https://replacement.example.org', placement_surface: 'public_organization_homepage', reporting: { display_capability: 'replacement-display-capability', click_capability: 'replacement-click-capability', report_view_key: 'replacement-placement-revision' } });
    const wrapper = mount(OrganizationCommunityView, { props: { publicIdentifier: 'north' } });
    await flushPromises(); await nextTick();
    expect(wrapper.text()).toContain('Local sponsor');
    await flushPromises();
    observers[0].callback([{ isIntersecting: true, intersectionRatio: 0.49 } as IntersectionObserverEntry], {} as IntersectionObserver);
    expect(api.recordPublicSponsorPlacementEvent).not.toHaveBeenCalled();
    observers[0].callback([{ isIntersecting: true, intersectionRatio: 0.5 } as IntersectionObserverEntry], {} as IntersectionObserver);
    expect(api.recordPublicSponsorPlacementEvent).toHaveBeenCalledTimes(1);
    expect(api.recordPublicSponsorPlacementEvent.mock.calls[0][0]).toBe('display-capability');
    expect(api.recordPublicSponsorPlacementEvent.mock.calls[0][1]).toMatch(/^[0-9a-f-]{36}$/i);
    observers[0].callback([{ isIntersecting: true, intersectionRatio: 1 } as IntersectionObserverEntry], {} as IntersectionObserver);
    expect(api.recordPublicSponsorPlacementEvent).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(30_000);
    await flushPromises();
    observers.at(-1)?.callback([{ isIntersecting: true, intersectionRatio: 1 } as IntersectionObserverEntry], {} as IntersectionObserver);
    expect(api.recordPublicSponsorPlacementEvent).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(30_000);
    await flushPromises();
    observers.at(-1)?.callback([{ isIntersecting: true, intersectionRatio: 1 } as IntersectionObserverEntry], {} as IntersectionObserver);
    expect(api.recordPublicSponsorPlacementEvent).toHaveBeenCalledTimes(2);
    expect(api.recordPublicSponsorPlacementEvent.mock.calls[1][0]).toBe('replacement-display-capability');

    await wrapper.get('.sponsor-placement a').trigger('click');
    expect(api.recordPublicSponsorPlacementEvent.mock.calls[2][0]).toBe('replacement-click-capability');
  });

  it('does not report while the document is hidden and cleans observer resources on route changes and unmount', async () => {
    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' });
    api.getPublicOrganizationCommunity.mockImplementation((value: string) => Promise.resolve(community(value)));
    api.getPublicOrganizationSponsorPlacement.mockResolvedValue({ sponsor_name: 'Local sponsor', sponsor_url: null, placement_surface: 'public_organization_homepage', reporting: { display_capability: 'hidden-capability', click_capability: 'click-capability', report_view_key: 'hidden-placement-revision' } });
    const wrapper = mount(OrganizationCommunityView, { props: { publicIdentifier: 'north' } });
    await flushPromises(); await nextTick();
    observers[0].callback([{ isIntersecting: true, intersectionRatio: 1 } as IntersectionObserverEntry], {} as IntersectionObserver);
    expect(api.recordPublicSponsorPlacementEvent).not.toHaveBeenCalled();
    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' });
    document.dispatchEvent(new Event('visibilitychange'));
    expect(api.recordPublicSponsorPlacementEvent).toHaveBeenCalledTimes(1);
    await wrapper.setProps({ publicIdentifier: 'next' });
    await flushPromises();
    expect(observers[0].disconnected).toBe(true);
    wrapper.unmount();
    expect(observers.at(-1)?.disconnected).toBe(true);
  });
});
