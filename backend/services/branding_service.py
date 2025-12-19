"""
Branding Service - White-label theming for organizations

Features:
- Custom organization branding (logos, colors, themes)
- Brand asset management and validation
- Theme CSS generation
- Org-specific color schemes (primary, secondary, accent)
- Typography and font management
- Branding template application
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple
import re


class ColorScheme(str, Enum):
    """Predefined color schemes"""
    LIGHT = "light"
    DARK = "dark"
    CUSTOM = "custom"


class FontFamily(str, Enum):
    """Available font families"""
    INTER = "Inter"
    ROBOTO = "Roboto"
    LATO = "Lato"
    POPPINS = "Poppins"
    SEGOE_UI = "Segoe UI"
    CUSTOM = "Custom"


@dataclass
class BrandColor:
    """Brand color definition with validation"""
    name: str  # primary, secondary, accent, background, text
    hex_code: str  # Validate hex format
    rgb_value: Optional[str] = None  # Computed RGB
    contrast_safe: bool = True  # Whether color meets WCAG contrast requirements

    def __post_init__(self):
        """Validate hex code on creation"""
        if not self._is_valid_hex(self.hex_code):
            raise ValueError(f"Invalid hex color: {self.hex_code}")
        
        # Compute RGB value
        self.rgb_value = self._hex_to_rgb(self.hex_code)

    @staticmethod
    def _is_valid_hex(hex_code: str) -> bool:
        """Validate hex color format"""
        pattern = r"^#[0-9A-Fa-f]{6}$"
        return re.match(pattern, hex_code) is not None

    @staticmethod
    def _hex_to_rgb(hex_code: str) -> str:
        """Convert hex to RGB format"""
        hex_code = hex_code.lstrip("#")
        r = int(hex_code[0:2], 16)
        g = int(hex_code[2:4], 16)
        b = int(hex_code[4:6], 16)
        return f"rgb({r}, {g}, {b})"


@dataclass
class BrandAsset:
    """Brand asset (logo, icon, etc.)"""
    asset_id: str
    asset_type: str  # logo, icon, favicon, background
    name: str
    url: str
    alt_text: str
    dimensions: Optional[Tuple[int, int]] = None  # width, height in pixels
    file_size_bytes: int = 0
    format: str = "png"  # png, svg, jpg, webp
    upload_date: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BrandTypography:
    """Typography settings"""
    primary_font: FontFamily
    secondary_font: Optional[FontFamily] = None
    heading_size_px: int = 32
    body_size_px: int = 14
    line_height: float = 1.5
    letter_spacing_em: float = 0.0
    font_weight_regular: int = 400
    font_weight_bold: int = 700


@dataclass
class OrgBrandTheme:
    """Complete brand theme for organization"""
    theme_id: str
    org_id: str
    org_name: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Branding
    logo_url: str = ""
    favicon_url: Optional[str] = None
    banner_image_url: Optional[str] = None
    
    # Colors
    primary_color: str = "#1F2937"  # Default: dark gray
    secondary_color: str = "#3B82F6"  # Default: blue
    accent_color: str = "#F59E0B"  # Default: amber
    background_color: str = "#FFFFFF"  # Default: white
    text_color: str = "#1F2937"  # Default: dark gray
    
    # Additional colors
    success_color: str = "#10B981"
    warning_color: str = "#F59E0B"
    error_color: str = "#EF4444"
    info_color: str = "#3B82F6"
    
    # Typography
    typography: Optional[BrandTypography] = None
    
    # Color scheme
    color_scheme: ColorScheme = ColorScheme.LIGHT
    
    # Brand assets
    assets: Dict[str, BrandAsset] = field(default_factory=dict)
    
    # Branding flags
    apply_to_viewer: bool = True
    apply_to_scoreboard: bool = True
    apply_to_admin: bool = True
    
    # Metadata
    is_active: bool = True
    description: str = ""


@dataclass
class BrandingValidationResult:
    """Result of branding validation"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    score: float = 0.0  # 0-100 branding completeness score


class BrandingService:
    """Service for managing organization branding and theming"""

    # CSS class names for theme application
    CSS_CLASS_PREFIX = "org-brand"
    
    # Color contrast ratio requirements (WCAG)
    MIN_CONTRAST_RATIO = 4.5  # For normal text

    @staticmethod
    def create_brand_theme(
        org_id: str,
        org_name: str,
        logo_url: str = "",
        primary_color: str = "#1F2937",
        secondary_color: str = "#3B82F6",
        accent_color: str = "#F59E0B",
    ) -> OrgBrandTheme:
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
            OrgBrandTheme object
        """
        theme = OrgBrandTheme(
            theme_id=f"theme_{org_id}_{int(datetime.utcnow().timestamp())}",
            org_id=org_id,
            org_name=org_name,
            logo_url=logo_url,
            primary_color=primary_color,
            secondary_color=secondary_color,
            accent_color=accent_color,
        )

        # Set default typography
        theme.typography = BrandTypography(
            primary_font=FontFamily.INTER,
            secondary_font=FontFamily.ROBOTO,
        )

        return theme

    @staticmethod
    def update_brand_colors(
        theme: OrgBrandTheme,
        primary: Optional[str] = None,
        secondary: Optional[str] = None,
        accent: Optional[str] = None,
        success: Optional[str] = None,
        warning: Optional[str] = None,
        error: Optional[str] = None,
    ) -> OrgBrandTheme:
        """
        Update brand colors in theme

        Args:
            theme: Existing theme to update
            primary: Primary color (hex)
            secondary: Secondary color (hex)
            accent: Accent color (hex)
            success: Success color (hex)
            warning: Warning color (hex)
            error: Error color (hex)

        Returns:
            Updated theme
        """
        if primary:
            theme.primary_color = BrandingService._validate_hex_color(primary)
        if secondary:
            theme.secondary_color = BrandingService._validate_hex_color(secondary)
        if accent:
            theme.accent_color = BrandingService._validate_hex_color(accent)
        if success:
            theme.success_color = BrandingService._validate_hex_color(success)
        if warning:
            theme.warning_color = BrandingService._validate_hex_color(warning)
        if error:
            theme.error_color = BrandingService._validate_hex_color(error)

        theme.updated_at = datetime.utcnow()
        return theme

    @staticmethod
    def set_typography(
        theme: OrgBrandTheme,
        primary_font: FontFamily = FontFamily.INTER,
        secondary_font: Optional[FontFamily] = None,
        heading_size: int = 32,
        body_size: int = 14,
        line_height: float = 1.5,
    ) -> OrgBrandTheme:
        """
        Configure typography settings

        Args:
            theme: Theme to update
            primary_font: Primary font family
            secondary_font: Secondary font family
            heading_size: Heading font size in pixels
            body_size: Body font size in pixels
            line_height: Line height multiplier

        Returns:
            Updated theme
        """
        theme.typography = BrandTypography(
            primary_font=primary_font,
            secondary_font=secondary_font,
            heading_size_px=heading_size,
            body_size_px=body_size,
            line_height=line_height,
        )

        theme.updated_at = datetime.utcnow()
        return theme

    @staticmethod
    def add_brand_asset(
        theme: OrgBrandTheme,
        asset_type: str,
        name: str,
        url: str,
        alt_text: str,
        dimensions: Optional[Tuple[int, int]] = None,
    ) -> OrgBrandTheme:
        """
        Add brand asset (logo, icon, etc.)

        Args:
            theme: Theme to update
            asset_type: Type of asset (logo, icon, favicon, etc.)
            name: Asset name
            url: URL to asset
            alt_text: Alt text for accessibility
            dimensions: Image dimensions (width, height)

        Returns:
            Updated theme
        """
        asset_id = f"asset_{asset_type}_{int(datetime.utcnow().timestamp())}"

        asset = BrandAsset(
            asset_id=asset_id,
            asset_type=asset_type,
            name=name,
            url=url,
            alt_text=alt_text,
            dimensions=dimensions,
        )

        theme.assets[asset_id] = asset

        # Update main URLs based on asset type
        if asset_type == "logo":
            theme.logo_url = url
        elif asset_type == "favicon":
            theme.favicon_url = url
        elif asset_type == "banner":
            theme.banner_image_url = url

        theme.updated_at = datetime.utcnow()
        return theme

    @staticmethod
    def generate_css(theme: OrgBrandTheme) -> str:
        """
        Generate CSS variables for theme

        Args:
            theme: Brand theme

        Returns:
            CSS string with theme variables
        """
        css = f":root {{\n"
        css += f"  --{BrandingService.CSS_CLASS_PREFIX}-primary: {theme.primary_color};\n"
        css += f"  --{BrandingService.CSS_CLASS_PREFIX}-secondary: {theme.secondary_color};\n"
        css += f"  --{BrandingService.CSS_CLASS_PREFIX}-accent: {theme.accent_color};\n"
        css += f"  --{BrandingService.CSS_CLASS_PREFIX}-background: {theme.background_color};\n"
        css += f"  --{BrandingService.CSS_CLASS_PREFIX}-text: {theme.text_color};\n"
        css += f"  --{BrandingService.CSS_CLASS_PREFIX}-success: {theme.success_color};\n"
        css += f"  --{BrandingService.CSS_CLASS_PREFIX}-warning: {theme.warning_color};\n"
        css += f"  --{BrandingService.CSS_CLASS_PREFIX}-error: {theme.error_color};\n"
        css += f"  --{BrandingService.CSS_CLASS_PREFIX}-info: {theme.info_color};\n"

        if theme.typography:
            css += f"  --{BrandingService.CSS_CLASS_PREFIX}-font-primary: '{theme.typography.primary_font.value}';\n"
            if theme.typography.secondary_font:
                css += f"  --{BrandingService.CSS_CLASS_PREFIX}-font-secondary: '{theme.typography.secondary_font.value}';\n"
            css += f"  --{BrandingService.CSS_CLASS_PREFIX}-heading-size: {theme.typography.heading_size_px}px;\n"
            css += f"  --{BrandingService.CSS_CLASS_PREFIX}-body-size: {theme.typography.body_size_px}px;\n"
            css += f"  --{BrandingService.CSS_CLASS_PREFIX}-line-height: {theme.typography.line_height};\n"

        css += "}\n\n"

        # Generate component-level CSS
        css += BrandingService._generate_component_css(theme)

        return css

    @staticmethod
    def _generate_component_css(theme: OrgBrandTheme) -> str:
        """Generate component-specific CSS"""
        css = ""

        # Button styles
        css += ".btn-primary {\n"
        css += f"  background-color: var(--{BrandingService.CSS_CLASS_PREFIX}-primary);\n"
        css += f"  color: var(--{BrandingService.CSS_CLASS_PREFIX}-background);\n"
        css += "}\n\n"

        # Badge styles
        css += ".badge-success {\n"
        css += f"  background-color: var(--{BrandingService.CSS_CLASS_PREFIX}-success);\n"
        css += "}\n\n"

        css += ".badge-warning {\n"
        css += f"  background-color: var(--{BrandingService.CSS_CLASS_PREFIX}-warning);\n"
        css += "}\n\n"

        css += ".badge-error {\n"
        css += f"  background-color: var(--{BrandingService.CSS_CLASS_PREFIX}-error);\n"
        css += "}\n\n"

        # Text styles
        css += "h1, h2, h3, h4, h5, h6 {\n"
        css += f"  font-family: var(--{BrandingService.CSS_CLASS_PREFIX}-font-primary);\n"
        css += f"  font-size: var(--{BrandingService.CSS_CLASS_PREFIX}-heading-size);\n"
        css += "}\n\n"

        css += "body, p {\n"
        css += f"  font-family: var(--{BrandingService.CSS_CLASS_PREFIX}-font-primary);\n"
        css += f"  font-size: var(--{BrandingService.CSS_CLASS_PREFIX}-body-size);\n"
        css += f"  line-height: var(--{BrandingService.CSS_CLASS_PREFIX}-line-height);\n"
        css += f"  color: var(--{BrandingService.CSS_CLASS_PREFIX}-text);\n"
        css += "}\n"

        return css

    @staticmethod
    def validate_branding(theme: OrgBrandTheme) -> BrandingValidationResult:
        """
        Validate brand theme completeness and quality

        Args:
            theme: Brand theme to validate

        Returns:
            BrandingValidationResult
        """
        result = BrandingValidationResult(is_valid=True)
        score = 0.0

        # Check required fields
        if not theme.org_name:
            result.errors.append("Organization name required")
            result.is_valid = False
        else:
            score += 10

        if not theme.logo_url:
            result.warnings.append("Logo URL not set")
        else:
            score += 15

        # Validate colors
        try:
            BrandColor("primary", theme.primary_color)
            BrandColor("secondary", theme.secondary_color)
            BrandColor("accent", theme.accent_color)
            score += 20
        except ValueError as e:
            result.errors.append(f"Invalid color format: {str(e)}")
            result.is_valid = False

        # Check typography
        if theme.typography:
            score += 15
        else:
            result.warnings.append("Typography not configured")

        # Check assets
        if theme.assets:
            score += 15
        else:
            result.warnings.append("No brand assets uploaded")

        # Check branding application scope
        if theme.apply_to_viewer or theme.apply_to_scoreboard or theme.apply_to_admin:
            score += 10
        else:
            result.warnings.append("Branding not applied to any component")

        # Check is_active
        if theme.is_active:
            score += 15
        else:
            result.warnings.append("Theme is not active")

        result.score = min(score, 100.0)
        return result

    @staticmethod
    def get_branding_json(theme: OrgBrandTheme) -> Dict:
        """
        Export branding as JSON for frontend/API

        Args:
            theme: Brand theme

        Returns:
            Dictionary with branding data
        """
        return {
            "theme_id": theme.theme_id,
            "org_id": theme.org_id,
            "org_name": theme.org_name,
            "colors": {
                "primary": theme.primary_color,
                "secondary": theme.secondary_color,
                "accent": theme.accent_color,
                "background": theme.background_color,
                "text": theme.text_color,
                "success": theme.success_color,
                "warning": theme.warning_color,
                "error": theme.error_color,
                "info": theme.info_color,
            },
            "assets": {
                asset_id: {
                    "type": asset.asset_type,
                    "name": asset.name,
                    "url": asset.url,
                    "alt_text": asset.alt_text,
                    "dimensions": asset.dimensions,
                }
                for asset_id, asset in theme.assets.items()
            },
            "typography": {
                "primary_font": theme.typography.primary_font.value if theme.typography else None,
                "heading_size": theme.typography.heading_size_px if theme.typography else None,
                "body_size": theme.typography.body_size_px if theme.typography else None,
            } if theme.typography else None,
            "apply_to": {
                "viewer": theme.apply_to_viewer,
                "scoreboard": theme.apply_to_scoreboard,
                "admin": theme.apply_to_admin,
            },
            "is_active": theme.is_active,
            "created_at": theme.created_at.isoformat(),
            "updated_at": theme.updated_at.isoformat(),
        }

    @staticmethod
    def _validate_hex_color(hex_code: str) -> str:
        """Validate and normalize hex color code"""
        if not hex_code.startswith("#"):
            hex_code = f"#{hex_code}"

        if not BrandColor._is_valid_hex(hex_code):
            raise ValueError(f"Invalid hex color format: {hex_code}")

        return hex_code.upper()
