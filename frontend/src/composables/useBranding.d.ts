interface BrandingData {
    theme_id: string;
    org_id: string;
    org_name: string;
    colors: {
        primary: string;
        secondary: string;
        accent: string;
        success: string;
        warning: string;
        error: string;
        info: string;
    };
    assets: Record<string, any>;
    typography: {
        primary_font: string;
        heading_size: number;
        body_size: number;
    } | null;
    apply_to: {
        viewer: boolean;
        scoreboard: boolean;
        admin: boolean;
    };
    is_active: boolean;
    created_at: string;
    updated_at: string;
}
/**
 * Composable for managing organization branding
 */
export declare function useBranding(): {
    fetchOrgBranding: (orgId: string) => Promise<BrandingData | null>;
    createBrandingTheme: (orgId: string, orgName: string, logoUrl?: string, primaryColor?: string, secondaryColor?: string, accentColor?: string) => Promise<any | null>;
    updateBrandColors: (orgId: string, updates: {
        primary?: string;
        secondary?: string;
        accent?: string;
        success?: string;
        warning?: string;
        error?: string;
    }) => Promise<any | null>;
    updateTypography: (orgId: string, primaryFont: string, headingSize?: number, bodySize?: number, lineHeight?: number) => Promise<any | null>;
    addBrandAsset: (orgId: string, assetType: string, name: string, url: string, altText: string, width?: number, height?: number) => Promise<any | null>;
    getThemeCSS: (orgId: string) => Promise<string | null>;
    validateBranding: (orgId: string) => Promise<any | null>;
    getAvailableFonts: () => Promise<any[] | null>;
    getColorSchemes: () => Promise<any[] | null>;
    applyThemeCSS: (css: string) => void;
    loadAndApplyBranding: (orgId: string) => Promise<boolean>;
};
export {};
