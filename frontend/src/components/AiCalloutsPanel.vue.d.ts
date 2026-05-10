export type CalloutSeverity = "info" | "positive" | "warning" | "critical";
export interface AiCallout {
    id: string;
    title: string;
    body: string;
    category?: string;
    severity?: CalloutSeverity;
    scope?: string;
    /** Optional: the phase ID from backend */
    targetPhaseId?: string;
    /** Optional: explicit DOM id to scroll to */
    targetDomId?: string;
    /** Optional: group/innings ID to expand/select before scrolling (e.g. innings index) */
    targetGroupId?: number;
}
declare const __VLS_export: any;
declare const _default: typeof __VLS_export;
export default _default;
