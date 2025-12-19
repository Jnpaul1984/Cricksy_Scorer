"""
Branding API Routes

Endpoints for managing organization branding and themes
"""

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from backend.services.branding_service import (
    BrandingService,
    ColorScheme,
    FontFamily,
    OrgBrandTheme,
)

router = APIRouter(prefix="/branding", tags=["branding"])

# In-memory storage for demo (in production, use database)
_org_themes: Dict[str, OrgBrandTheme] = {}


@router.post("/themes")
async def create_brand_theme(
    org_id: str,
    org_name: str,
    logo_url: str = "",
    primary_color: str = "#1F2937",
    secondary_color: str = "#3B82F6",
    accent_color: str = "#F59E0B",
):
    """
    Create new brand theme for organization

    Args:
        org_id: Organization ID
        org_name: Organization name
        logo_url: URL to organization logo
        primary_color: Primary brand color (hex)
        secondary_color: Secondary brand color (hex)
        accent_color: Accent brand color (hex)

    Returns:
        Created theme
    """
    try:
        theme = BrandingService.create_brand_theme(
            org_id=org_id,
            org_name=org_name,
            logo_url=logo_url,
            primary_color=primary_color,
            secondary_color=secondary_color,
            accent_color=accent_color,
        )

        # Store in memory
        _org_themes[org_id] = theme

        return {
            "status": "success",
            "theme_id": theme.theme_id,
            "org_id": theme.org_id,
            "org_name": theme.org_name,
            "colors": {
                "primary": theme.primary_color,
                "secondary": theme.secondary_color,
                "accent": theme.accent_color,
            },
            "created_at": theme.created_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create theme: {str(e)}")


@router.get("/themes/{org_id}")
async def get_brand_theme(org_id: str):
    """
    Get brand theme for organization

    Args:
        org_id: Organization ID

    Returns:
        Brand theme
    """
    try:
        if org_id not in _org_themes:
            raise HTTPException(status_code=404, detail=f"Theme not found for org {org_id}")

        theme = _org_themes[org_id]
        return BrandingService.get_branding_json(theme)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch theme: {str(e)}")


@router.put("/themes/{org_id}/colors")
async def update_brand_colors(
    org_id: str,
    primary: Optional[str] = Query(None),
    secondary: Optional[str] = Query(None),
    accent: Optional[str] = Query(None),
    success: Optional[str] = Query(None),
    warning: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """
    Update brand colors

    Args:
        org_id: Organization ID
        primary: Primary color (hex)
        secondary: Secondary color (hex)
        accent: Accent color (hex)
        success: Success color (hex)
        warning: Warning color (hex)
        error: Error color (hex)

    Returns:
        Updated theme
    """
    try:
        if org_id not in _org_themes:
            raise HTTPException(status_code=404, detail=f"Theme not found for org {org_id}")

        theme = _org_themes[org_id]
        theme = BrandingService.update_brand_colors(
            theme=theme,
            primary=primary,
            secondary=secondary,
            accent=accent,
            success=success,
            warning=warning,
            error=error,
        )

        return {
            "status": "success",
            "message": "Colors updated",
            "colors": {
                "primary": theme.primary_color,
                "secondary": theme.secondary_color,
                "accent": theme.accent_color,
                "success": theme.success_color,
                "warning": theme.warning_color,
                "error": theme.error_color,
            },
            "updated_at": theme.updated_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update colors: {str(e)}")


@router.put("/themes/{org_id}/typography")
async def update_typography(
    org_id: str,
    primary_font: str = "Inter",
    secondary_font: Optional[str] = None,
    heading_size: int = 32,
    body_size: int = 14,
    line_height: float = 1.5,
):
    """
    Update typography settings

    Args:
        org_id: Organization ID
        primary_font: Primary font family
        secondary_font: Secondary font family
        heading_size: Heading size in pixels
        body_size: Body size in pixels
        line_height: Line height multiplier

    Returns:
        Updated theme
    """
    try:
        if org_id not in _org_themes:
            raise HTTPException(status_code=404, detail=f"Theme not found for org {org_id}")

        theme = _org_themes[org_id]

        # Validate font
        try:
            primary = FontFamily[primary_font.upper().replace(" ", "_")]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid font: {primary_font}. Available: {', '.join([f.value for f in FontFamily])}",
            )

        secondary = None
        if secondary_font:
            try:
                secondary = FontFamily[secondary_font.upper().replace(" ", "_")]
            except KeyError:
                pass

        theme = BrandingService.set_typography(
            theme=theme,
            primary_font=primary,
            secondary_font=secondary,
            heading_size=heading_size,
            body_size=body_size,
            line_height=line_height,
        )

        return {
            "status": "success",
            "message": "Typography updated",
            "typography": {
                "primary_font": theme.typography.primary_font.value,
                "secondary_font": theme.typography.secondary_font.value if theme.typography.secondary_font else None,
                "heading_size": theme.typography.heading_size_px,
                "body_size": theme.typography.body_size_px,
                "line_height": theme.typography.line_height,
            },
            "updated_at": theme.updated_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update typography: {str(e)}")


@router.post("/themes/{org_id}/assets")
async def add_brand_asset(
    org_id: str,
    asset_type: str,
    name: str,
    url: str,
    alt_text: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
):
    """
    Add brand asset (logo, icon, favicon, etc.)

    Args:
        org_id: Organization ID
        asset_type: Type of asset (logo, icon, favicon, banner)
        name: Asset name
        url: URL to asset
        alt_text: Alt text for accessibility
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        Updated theme with new asset
    """
    try:
        if org_id not in _org_themes:
            raise HTTPException(status_code=404, detail=f"Theme not found for org {org_id}")

        theme = _org_themes[org_id]
        dimensions = (width, height) if width and height else None

        theme = BrandingService.add_brand_asset(
            theme=theme,
            asset_type=asset_type,
            name=name,
            url=url,
            alt_text=alt_text,
            dimensions=dimensions,
        )

        return {
            "status": "success",
            "message": f"Asset '{name}' added",
            "asset_type": asset_type,
            "url": url,
            "updated_at": theme.updated_at.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add asset: {str(e)}")


@router.get("/themes/{org_id}/css")
async def get_theme_css(org_id: str):
    """
    Get generated CSS variables for theme

    Args:
        org_id: Organization ID

    Returns:
        CSS string with theme variables
    """
    try:
        if org_id not in _org_themes:
            raise HTTPException(status_code=404, detail=f"Theme not found for org {org_id}")

        theme = _org_themes[org_id]
        css = BrandingService.generate_css(theme)

        return {
            "org_id": org_id,
            "css": css,
            "content_type": "text/css",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate CSS: {str(e)}")


@router.post("/themes/{org_id}/validate")
async def validate_branding(org_id: str):
    """
    Validate brand theme completeness and quality

    Args:
        org_id: Organization ID

    Returns:
        Validation result with score and recommendations
    """
    try:
        if org_id not in _org_themes:
            raise HTTPException(status_code=404, detail=f"Theme not found for org {org_id}")

        theme = _org_themes[org_id]
        result = BrandingService.validate_branding(theme)

        return {
            "org_id": org_id,
            "is_valid": result.is_valid,
            "score": result.score,
            "errors": result.errors,
            "warnings": result.warnings,
            "completeness_percent": result.score,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate branding: {str(e)}")


@router.put("/themes/{org_id}/scope")
async def update_application_scope(
    org_id: str,
    apply_to_viewer: Optional[bool] = None,
    apply_to_scoreboard: Optional[bool] = None,
    apply_to_admin: Optional[bool] = None,
):
    """
    Update where brand theme is applied

    Args:
        org_id: Organization ID
        apply_to_viewer: Apply to viewer component
        apply_to_scoreboard: Apply to scoreboard
        apply_to_admin: Apply to admin panel

    Returns:
        Updated theme
    """
    try:
        if org_id not in _org_themes:
            raise HTTPException(status_code=404, detail=f"Theme not found for org {org_id}")

        theme = _org_themes[org_id]

        if apply_to_viewer is not None:
            theme.apply_to_viewer = apply_to_viewer
        if apply_to_scoreboard is not None:
            theme.apply_to_scoreboard = apply_to_scoreboard
        if apply_to_admin is not None:
            theme.apply_to_admin = apply_to_admin

        theme.updated_at = datetime.utcnow()

        return {
            "status": "success",
            "apply_to": {
                "viewer": theme.apply_to_viewer,
                "scoreboard": theme.apply_to_scoreboard,
                "admin": theme.apply_to_admin,
            },
            "updated_at": theme.updated_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update scope: {str(e)}")


@router.get("/fonts")
async def get_available_fonts():
    """
    Get available font families

    Returns:
        List of available fonts
    """
    return {
        "fonts": [
            {
                "value": font.value,
                "name": font.name,
            }
            for font in FontFamily
        ]
    }


@router.get("/color-schemes")
async def get_color_schemes():
    """
    Get available color schemes

    Returns:
        List of color schemes
    """
    return {
        "schemes": [
            {
                "value": scheme.value,
                "name": scheme.name.title(),
            }
            for scheme in ColorScheme
        ]
    }
