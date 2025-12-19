import { ref } from 'vue'

interface BrandingData {
  theme_id: string
  org_id: string
  org_name: string
  colors: {
    primary: string
    secondary: string
    accent: string
    success: string
    warning: string
    error: string
    info: string
  }
  assets: Record<string, any>
  typography: {
    primary_font: string
    heading_size: number
    body_size: number
  } | null
  apply_to: {
    viewer: boolean
    scoreboard: boolean
    admin: boolean
  }
  is_active: boolean
  created_at: string
  updated_at: string
}

/**
 * Composable for managing organization branding
 */
export function useBranding() {
  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  /**
   * Fetch branding for an organization
   */
  const fetchOrgBranding = async (orgId: string): Promise<BrandingData | null> => {
    try {
      const response = await fetch(`${API_BASE}/branding/themes/${orgId}`)
      if (!response.ok) throw new Error('Failed to fetch branding')
      return await response.json()
    } catch (error) {
      console.error('Error fetching branding:', error)
      return null
    }
  }

  /**
   * Create new branding theme
   */
  const createBrandingTheme = async (
    orgId: string,
    orgName: string,
    logoUrl: string = '',
    primaryColor: string = '#1F2937',
    secondaryColor: string = '#3B82F6',
    accentColor: string = '#F59E0B'
  ): Promise<any | null> => {
    try {
      const response = await fetch(`${API_BASE}/branding/themes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          org_id: orgId,
          org_name: orgName,
          logo_url: logoUrl,
          primary_color: primaryColor,
          secondary_color: secondaryColor,
          accent_color: accentColor,
        }),
      })
      if (!response.ok) throw new Error('Failed to create branding theme')
      return await response.json()
    } catch (error) {
      console.error('Error creating branding:', error)
      return null
    }
  }

  /**
   * Update brand colors
   */
  const updateBrandColors = async (
    orgId: string,
    updates: {
      primary?: string
      secondary?: string
      accent?: string
      success?: string
      warning?: string
      error?: string
    }
  ): Promise<any | null> => {
    try {
      const params = new URLSearchParams()
      if (updates.primary) params.append('primary', updates.primary)
      if (updates.secondary) params.append('secondary', updates.secondary)
      if (updates.accent) params.append('accent', updates.accent)
      if (updates.success) params.append('success', updates.success)
      if (updates.warning) params.append('warning', updates.warning)
      if (updates.error) params.append('error', updates.error)

      const response = await fetch(
        `${API_BASE}/branding/themes/${orgId}/colors?${params}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
        }
      )
      if (!response.ok) throw new Error('Failed to update colors')
      return await response.json()
    } catch (error) {
      console.error('Error updating branding colors:', error)
      return null
    }
  }

  /**
   * Update typography settings
   */
  const updateTypography = async (
    orgId: string,
    primaryFont: string,
    headingSize: number = 32,
    bodySize: number = 14,
    lineHeight: number = 1.5
  ): Promise<any | null> => {
    try {
      const response = await fetch(
        `${API_BASE}/branding/themes/${orgId}/typography` +
          `?primary_font=${primaryFont}` +
          `&heading_size=${headingSize}` +
          `&body_size=${bodySize}` +
          `&line_height=${lineHeight}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
        }
      )
      if (!response.ok) throw new Error('Failed to update typography')
      return await response.json()
    } catch (error) {
      console.error('Error updating typography:', error)
      return null
    }
  }

  /**
   * Add brand asset
   */
  const addBrandAsset = async (
    orgId: string,
    assetType: string,
    name: string,
    url: string,
    altText: string,
    width?: number,
    height?: number
  ): Promise<any | null> => {
    try {
      const params = new URLSearchParams({
        asset_type: assetType,
        name,
        url,
        alt_text: altText,
      })
      if (width) params.append('width', width.toString())
      if (height) params.append('height', height.toString())

      const response = await fetch(
        `${API_BASE}/branding/themes/${orgId}/assets?${params}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        }
      )
      if (!response.ok) throw new Error('Failed to add asset')
      return await response.json()
    } catch (error) {
      console.error('Error adding asset:', error)
      return null
    }
  }

  /**
   * Get theme CSS
   */
  const getThemeCSS = async (orgId: string): Promise<string | null> => {
    try {
      const response = await fetch(`${API_BASE}/branding/themes/${orgId}/css`)
      if (!response.ok) throw new Error('Failed to fetch CSS')
      const data = await response.json()
      return data.css
    } catch (error) {
      console.error('Error fetching CSS:', error)
      return null
    }
  }

  /**
   * Validate branding
   */
  const validateBranding = async (orgId: string): Promise<any | null> => {
    try {
      const response = await fetch(`${API_BASE}/branding/themes/${orgId}/validate`, {
        method: 'POST',
      })
      if (!response.ok) throw new Error('Failed to validate branding')
      return await response.json()
    } catch (error) {
      console.error('Error validating branding:', error)
      return null
    }
  }

  /**
   * Get available fonts
   */
  const getAvailableFonts = async (): Promise<any[] | null> => {
    try {
      const response = await fetch(`${API_BASE}/branding/fonts`)
      if (!response.ok) throw new Error('Failed to fetch fonts')
      const data = await response.json()
      return data.fonts
    } catch (error) {
      console.error('Error fetching fonts:', error)
      return null
    }
  }

  /**
   * Get color schemes
   */
  const getColorSchemes = async (): Promise<any[] | null> => {
    try {
      const response = await fetch(`${API_BASE}/branding/color-schemes`)
      if (!response.ok) throw new Error('Failed to fetch color schemes')
      const data = await response.json()
      return data.schemes
    } catch (error) {
      console.error('Error fetching color schemes:', error)
      return null
    }
  }

  /**
   * Apply theme CSS to document
   */
  const applyThemeCSS = (css: string) => {
    let styleElement = document.getElementById('org-brand-theme-style')
    if (!styleElement) {
      styleElement = document.createElement('style')
      styleElement.id = 'org-brand-theme-style'
      document.head.appendChild(styleElement)
    }
    styleElement.innerHTML = css
  }

  /**
   * Load and apply branding for organization
   */
  const loadAndApplyBranding = async (orgId: string): Promise<boolean> => {
    try {
      const branding = await fetchOrgBranding(orgId)
      if (!branding) return false

      const css = await getThemeCSS(orgId)
      if (css) {
        applyThemeCSS(css)
      }

      return true
    } catch (error) {
      console.error('Error loading and applying branding:', error)
      return false
    }
  }

  return {
    fetchOrgBranding,
    createBrandingTheme,
    updateBrandColors,
    updateTypography,
    addBrandAsset,
    getThemeCSS,
    validateBranding,
    getAvailableFonts,
    getColorSchemes,
    applyThemeCSS,
    loadAndApplyBranding,
  }
}
