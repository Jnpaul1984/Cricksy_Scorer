/**
 * useProjectorMode.ts - Projector mode configuration
 *
 * Handles query parameter parsing and CSS variable management for
 * projectable/resizable viewer modes (TV, projector, OBS overlay)
 */
import type { LocationQueryValue } from 'vue-router';
export type Layout = 'default' | 'projector';
export type Density = 'compact' | 'normal' | 'spacious';
export type SafeArea = 'on' | 'off';
export type Preset = 'default' | 'tv1080' | 'proj720' | 'overlay';
export interface ProjectorConfig {
    layout: Layout;
    scale: number;
    density: Density;
    safeArea: SafeArea;
    showBatters: boolean;
    showBowler: boolean;
    showLastBalls: boolean;
    showWinProb: boolean;
}
/**
 * Composable for managing projector mode config
 */
export declare function useProjectorMode(queryParams: Record<string, LocationQueryValue | LocationQueryValue[] | undefined>): {
    config: any;
    cssVariables: any;
    showBatters: any;
    showBowler: any;
    showLastBalls: any;
    showWinProb: any;
    isProjectorMode: any;
};
/**
 * Get preset configuration by name
 */
export declare function getPreset(name: Preset): ProjectorConfig;
/**
 * Build a shareable URL with projector params
 */
export declare function buildProjectorUrl(baseUrl: string, gameId: string, preset: Preset, additionalParams?: Record<string, string>): string;
