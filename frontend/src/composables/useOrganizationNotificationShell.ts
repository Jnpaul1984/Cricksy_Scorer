import type { InjectionKey, Ref } from 'vue';
import { inject } from 'vue';

export interface OrganizationNotificationShellContext {
  unreadCount: Ref<number>;
  refreshUnreadCount: () => Promise<void>;
  clearPrivateState: () => void;
}

export const organizationNotificationShellKey: InjectionKey<OrganizationNotificationShellContext> =
  Symbol('organization-notification-shell');

export function useOrganizationNotificationShell(): OrganizationNotificationShellContext | null {
  return inject(organizationNotificationShellKey, null);
}
