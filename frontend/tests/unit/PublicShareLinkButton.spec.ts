import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { createRouter, createWebHashHistory } from 'vue-router';

import PublicShareLinkButton from '@/components/PublicShareLinkButton.vue';

describe('PublicShareLinkButton', () => {
  it('copies the canonical router URL with configured hash-mode base', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    const router = createRouter({
      history: createWebHashHistory('/cricksy/'),
      routes: [{ path: '/community/:publicIdentifier', component: { template: '<div />' } }],
    });
    const wrapper = mount(PublicShareLinkButton, {
      props: { path: '/community/org_0123456789abcdef01234567', label: 'Copy' },
      global: { plugins: [router] },
    });

    await wrapper.get('button').trigger('click');
    expect(writeText).toHaveBeenCalledWith(
      `${window.location.origin}/cricksy/#/community/org_0123456789abcdef01234567`,
    );
  });
});
