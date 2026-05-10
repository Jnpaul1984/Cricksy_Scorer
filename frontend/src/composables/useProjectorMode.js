/**
 * useProjectorMode.ts - Projector mode configuration
 *
 * Handles query parameter parsing and CSS variable management for
 * projectable/resizable viewer modes (TV, projector, OBS overlay)
 */
import { computed, ref } from 'vue';
// Preset definitions
const PRESETS = {
    default: {
        layout: 'default',
        scale: 1,
        density: 'normal',
        safeArea: 'off',
        showBatters: true,
        showBowler: true,
        showLastBalls: true,
        showWinProb: true,
    },
    tv1080: {
        layout: 'projector',
        scale: 1.15,
        density: 'spacious',
        safeArea: 'on',
        showBatters: true,
        showBowler: true,
        showLastBalls: true,
        showWinProb: true,
    },
    proj720: {
        layout: 'projector',
        scale: 1.3,
        density: 'compact',
        safeArea: 'on',
        showBatters: true,
        showBowler: true,
        showLastBalls: true,
        showWinProb: false,
    },
    overlay: {
        layout: 'projector',
        scale: 1,
        density: 'compact',
        safeArea: 'off',
        showBatters: false,
        showBowler: true,
        showLastBalls: false,
        showWinProb: false,
    },
};
/**
 * Parse query parameters into projector config
 */
function parseQueryParams(query) {
    const config = {};
    // Preset (overrides other params if provided)
    const preset = String(query.preset || 'default');
    if (preset in PRESETS) {
        return PRESETS[preset];
    }
    // Layout
    const layout = String(query.layout || 'default');
    if (layout === 'projector' || layout === 'default') {
        config.layout = layout;
    }
    // Scale
    const scaleStr = String(query.scale || '1');
    const scale = parseFloat(scaleStr);
    if (!isNaN(scale) && scale > 0 && scale <= 3) {
        config.scale = scale;
    }
    // Density
    const density = String(query.density || 'normal');
    if (['compact', 'normal', 'spacious'].includes(density)) {
        config.density = density;
    }
    // SafeArea
    const safeArea = String(query.safeArea || 'off');
    if (['on', 'off'].includes(safeArea)) {
        config.safeArea = safeArea;
    }
    // Show/hide sections
    if (query.show) {
        const showStr = String(query.show);
        config.showBatters = showStr.includes('batters');
        config.showBowler = showStr.includes('bowler');
        config.showLastBalls = showStr.includes('lastballs');
        config.showWinProb = showStr.includes('winprob');
    }
    if (query.hide) {
        const hideStr = String(query.hide);
        if (hideStr.includes('batters'))
            config.showBatters = false;
        if (hideStr.includes('bowler'))
            config.showBowler = false;
        if (hideStr.includes('lastballs'))
            config.showLastBalls = false;
        if (hideStr.includes('winprob'))
            config.showWinProb = false;
    }
    return config;
}
/**
 * Composable for managing projector mode config
 */
export function useProjectorMode(queryParams) {
    // Default config
    const defaultConfig = {
        layout: 'default',
        scale: 1,
        density: 'normal',
        safeArea: 'off',
        showBatters: true,
        showBowler: true,
        showLastBalls: true,
        showWinProb: true,
    };
    // Parse and merge
    const parsed = parseQueryParams(queryParams);
    const config = ref({ ...defaultConfig, ...parsed });
    // Compute CSS variables to apply to root
    const cssVariables = computed(() => {
        const densityMap = {
            compact: { padding: '12px', fontSize: '0.9em', gap: '8px' },
            normal: { padding: '16px', fontSize: '1em', gap: '12px' },
            spacious: { padding: '24px', fontSize: '1.1em', gap: '16px' },
        };
        const density = densityMap[config.value.density];
        const safeAreaPad = config.value.safeArea === 'on' ? '20px' : '0px';
        return {
            '--sb-scale': String(config.value.scale),
            '--sb-density-padding': density.padding,
            '--sb-density-font': density.fontSize,
            '--sb-density-gap': density.gap,
            '--sb-safe-pad': safeAreaPad,
        };
    });
    // Computed visibility flags
    const showBatters = computed(() => config.value.showBatters);
    const showBowler = computed(() => config.value.showBowler);
    const showLastBalls = computed(() => config.value.showLastBalls);
    const showWinProb = computed(() => config.value.showWinProb);
    const isProjectorMode = computed(() => config.value.layout === 'projector');
    return {
        config,
        cssVariables,
        showBatters,
        showBowler,
        showLastBalls,
        showWinProb,
        isProjectorMode,
    };
}
/**
 * Get preset configuration by name
 */
export function getPreset(name) {
    const defaultConfig = {
        layout: 'default',
        scale: 1,
        density: 'normal',
        safeArea: 'off',
        showBatters: true,
        showBowler: true,
        showLastBalls: true,
        showWinProb: true,
    };
    return { ...defaultConfig, ...PRESETS[name] };
}
/**
 * Build a shareable URL with projector params
 */
export function buildProjectorUrl(baseUrl, gameId, preset, additionalParams) {
    const params = new URLSearchParams();
    params.set('preset', preset);
    if (additionalParams) {
        Object.entries(additionalParams).forEach(([k, v]) => {
            params.set(k, v);
        });
    }
    const qs = params.toString();
    return qs ? `${baseUrl}?${qs}` : baseUrl;
}
