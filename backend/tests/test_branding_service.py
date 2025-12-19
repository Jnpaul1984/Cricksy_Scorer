"""
Tests for Branding Service - Feature 13

Comprehensive tests for organization branding and theming
"""

import pytest
from datetime import datetime

from backend.services.branding_service import (
    BrandColor,
    BrandingService,
    ColorScheme,
    FontFamily,
    OrgBrandTheme,
)


class TestBrandColorValidation:
    """Tests for brand color validation"""

    def test_valid_hex_color(self):
        """Test creating color with valid hex code"""
        color = BrandColor("primary", "#FF5733")
        
        assert color.hex_code == "#FF5733"
        assert color.rgb_value == "rgb(255, 87, 51)"

    def test_invalid_hex_format(self):
        """Test that invalid hex format raises error"""
        with pytest.raises(ValueError):
            BrandColor("primary", "FF5733")  # Missing #

    def test_invalid_hex_characters(self):
        """Test that invalid hex characters raise error"""
        with pytest.raises(ValueError):
            BrandColor("primary", "#GGGGGG")

    def test_hex_case_insensitive(self):
        """Test hex color case handling"""
        color = BrandColor("primary", "#ff5733")
        assert color.hex_code == "#ff5733"

    def test_rgb_conversion(self):
        """Test hex to RGB conversion"""
        color = BrandColor("primary", "#FFFFFF")
        assert color.rgb_value == "rgb(255, 255, 255)"

        color = BrandColor("primary", "#000000")
        assert color.rgb_value == "rgb(0, 0, 0)"


class TestBrandThemeCreation:
    """Tests for creating brand themes"""

    def test_creates_brand_theme(self):
        """Test creating new brand theme"""
        theme = BrandingService.create_brand_theme(
            org_id="org1",
            org_name="Test Org",
            logo_url="https://example.com/logo.png",
            primary_color="#FF5733",
            secondary_color="#3498DB",
            accent_color="#E74C3C",
        )

        assert theme.org_id == "org1"
        assert theme.org_name == "Test Org"
        assert theme.logo_url == "https://example.com/logo.png"
        assert theme.primary_color == "#FF5733"
        assert theme.is_active is True

    def test_theme_has_default_typography(self):
        """Test that new theme has default typography"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")

        assert theme.typography is not None
        assert theme.typography.primary_font == FontFamily.INTER
        assert theme.typography.heading_size_px == 32
        assert theme.typography.body_size_px == 14

    def test_theme_has_created_timestamp(self):
        """Test that theme has creation timestamp"""
        before = datetime.utcnow()
        theme = BrandingService.create_brand_theme("org1", "Test Org")
        after = datetime.utcnow()

        assert before <= theme.created_at <= after

    def test_theme_defaults_for_optional_fields(self):
        """Test that theme has sensible defaults"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")

        assert theme.background_color == "#FFFFFF"
        assert theme.text_color == "#1F2937"
        assert theme.success_color == "#10B981"
        assert theme.error_color == "#EF4444"


class TestBrandColorUpdates:
    """Tests for updating brand colors"""

    def test_updates_primary_color(self):
        """Test updating primary color"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")
        original = theme.primary_color

        theme = BrandingService.update_brand_colors(theme, primary="#FF0000")

        assert theme.primary_color == "#FF0000"
        assert theme.primary_color != original

    def test_updates_multiple_colors(self):
        """Test updating multiple colors at once"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")

        theme = BrandingService.update_brand_colors(
            theme,
            primary="#FF0000",
            secondary="#00FF00",
            accent="#0000FF",
            success="#FFFF00",
            warning="#FF00FF",
            error="#00FFFF",
        )

        assert theme.primary_color == "#FF0000"
        assert theme.secondary_color == "#00FF00"
        assert theme.accent_color == "#0000FF"
        assert theme.success_color == "#FFFF00"
        assert theme.warning_color == "#FF00FF"
        assert theme.error_color == "#00FFFF"

    def test_partial_color_update(self):
        """Test updating only some colors"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")
        original_secondary = theme.secondary_color

        theme = BrandingService.update_brand_colors(theme, primary="#FF0000")

        assert theme.primary_color == "#FF0000"
        assert theme.secondary_color == original_secondary

    def test_updates_timestamp_on_color_change(self):
        """Test that updated_at timestamp is updated"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")
        original_time = theme.updated_at

        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)

        theme = BrandingService.update_brand_colors(theme, primary="#FF0000")

        assert theme.updated_at > original_time


class TestTypographyConfiguration:
    """Tests for configuring typography"""

    def test_sets_typography(self):
        """Test setting typography settings"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")

        theme = BrandingService.set_typography(
            theme,
            primary_font=FontFamily.ROBOTO,
            secondary_font=FontFamily.LATO,
            heading_size=40,
            body_size=16,
            line_height=1.8,
        )

        assert theme.typography.primary_font == FontFamily.ROBOTO
        assert theme.typography.secondary_font == FontFamily.LATO
        assert theme.typography.heading_size_px == 40
        assert theme.typography.body_size_px == 16
        assert theme.typography.line_height == 1.8

    def test_sets_primary_font_only(self):
        """Test setting only primary font"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")

        theme = BrandingService.set_typography(
            theme, primary_font=FontFamily.POPPINS
        )

        assert theme.typography.primary_font == FontFamily.POPPINS

    def test_typography_updates_timestamp(self):
        """Test that typography update changes updated_at"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")
        original_time = theme.updated_at

        import time
        time.sleep(0.01)

        theme = BrandingService.set_typography(theme, primary_font=FontFamily.ROBOTO)

        assert theme.updated_at > original_time


class TestBrandAssets:
    """Tests for managing brand assets"""

    def test_adds_logo_asset(self):
        """Test adding logo asset"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")

        theme = BrandingService.add_brand_asset(
            theme,
            asset_type="logo",
            name="Company Logo",
            url="https://example.com/logo.png",
            alt_text="Company logo",
            dimensions=(200, 100),
        )

        assert len(theme.assets) == 1
        assert theme.logo_url == "https://example.com/logo.png"

    def test_adds_multiple_assets(self):
        """Test adding multiple assets"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")

        theme = BrandingService.add_brand_asset(
            theme,
            asset_type="logo",
            name="Logo",
            url="https://example.com/logo.png",
            alt_text="Logo",
        )

        theme = BrandingService.add_brand_asset(
            theme,
            asset_type="favicon",
            name="Favicon",
            url="https://example.com/favicon.ico",
            alt_text="Favicon",
        )

        theme = BrandingService.add_brand_asset(
            theme,
            asset_type="banner",
            name="Banner",
            url="https://example.com/banner.jpg",
            alt_text="Banner",
        )

        assert len(theme.assets) == 3
        assert theme.logo_url == "https://example.com/logo.png"
        assert theme.favicon_url == "https://example.com/favicon.ico"
        assert theme.banner_image_url == "https://example.com/banner.jpg"

    def test_asset_has_metadata(self):
        """Test that assets have proper metadata"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")

        theme = BrandingService.add_brand_asset(
            theme,
            asset_type="logo",
            name="Logo",
            url="https://example.com/logo.png",
            alt_text="Company logo",
            dimensions=(300, 150),
        )

        asset = list(theme.assets.values())[0]
        assert asset.name == "Logo"
        assert asset.dimensions == (300, 150)
        assert asset.alt_text == "Company logo"


class TestCSSGeneration:
    """Tests for CSS generation"""

    def test_generates_css_variables(self):
        """Test generating CSS with color variables"""
        theme = BrandingService.create_brand_theme(
            "org1",
            "Test Org",
            primary_color="#FF5733",
        )

        css = BrandingService.generate_css(theme)

        assert "--org-brand-primary: #FF5733" in css
        assert "--org-brand-secondary" in css
        assert "--org-brand-accent" in css

    def test_css_includes_typography(self):
        """Test that CSS includes typography variables"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")
        theme = BrandingService.set_typography(
            theme,
            primary_font=FontFamily.ROBOTO,
            heading_size=40,
            body_size=16,
        )

        css = BrandingService.generate_css(theme)

        assert "--org-brand-font-primary: 'Roboto'" in css
        assert "--org-brand-heading-size: 40px" in css
        assert "--org-brand-body-size: 16px" in css

    def test_css_includes_component_styles(self):
        """Test that generated CSS includes component styles"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")

        css = BrandingService.generate_css(theme)

        assert ".btn-primary" in css
        assert ".badge-success" in css
        assert ".badge-error" in css


class TestBrandingValidation:
    """Tests for validating branding completeness"""

    def test_validates_complete_branding(self):
        """Test validating fully configured branding"""
        theme = BrandingService.create_brand_theme(
            "org1",
            "Test Org",
            logo_url="https://example.com/logo.png",
            primary_color="#FF5733",
        )

        theme = BrandingService.set_typography(
            theme, primary_font=FontFamily.INTER
        )

        theme = BrandingService.add_brand_asset(
            theme,
            asset_type="logo",
            name="Logo",
            url="https://example.com/logo.png",
            alt_text="Logo",
        )

        result = BrandingService.validate_branding(theme)

        assert result.is_valid is True
        assert result.score > 50  # Should be fairly complete

    def test_validates_minimal_branding(self):
        """Test validating minimal branding"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")

        result = BrandingService.validate_branding(theme)

        assert result.is_valid is True
        assert len(result.warnings) > 0  # Should have warnings for missing assets

    def test_validation_missing_org_name(self):
        """Test validation fails with missing org name"""
        theme = OrgBrandTheme(
            theme_id="t1",
            org_id="org1",
            org_name="",  # Empty name
            primary_color="#FF5733",
        )

        result = BrandingService.validate_branding(theme)

        assert result.is_valid is False
        assert "Organization name required" in result.errors

    def test_validation_score_improves_with_completeness(self):
        """Test that validation score improves as branding is completed"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")
        result1 = BrandingService.validate_branding(theme)

        # Add assets
        theme = BrandingService.add_brand_asset(
            theme,
            asset_type="logo",
            name="Logo",
            url="https://example.com/logo.png",
            alt_text="Logo",
        )
        result2 = BrandingService.validate_branding(theme)

        # Add typography
        theme = BrandingService.set_typography(theme, primary_font=FontFamily.INTER)
        result3 = BrandingService.validate_branding(theme)

        assert result2.score >= result1.score
        assert result3.score >= result2.score


class TestBrandingExport:
    """Tests for exporting branding data"""

    def test_exports_to_json(self):
        """Test exporting theme to JSON format"""
        theme = BrandingService.create_brand_theme(
            "org1",
            "Test Org",
            logo_url="https://example.com/logo.png",
            primary_color="#FF5733",
        )

        json_data = BrandingService.get_branding_json(theme)

        assert json_data["org_id"] == "org1"
        assert json_data["org_name"] == "Test Org"
        assert json_data["colors"]["primary"] == "#FF5733"
        assert json_data["is_active"] is True

    def test_json_includes_all_metadata(self):
        """Test that JSON export includes all metadata"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")
        theme = BrandingService.add_brand_asset(
            theme,
            asset_type="logo",
            name="Logo",
            url="https://example.com/logo.png",
            alt_text="Logo",
        )

        json_data = BrandingService.get_branding_json(theme)

        assert "theme_id" in json_data
        assert "created_at" in json_data
        assert "updated_at" in json_data
        assert len(json_data["assets"]) == 1

    def test_json_includes_typography(self):
        """Test that JSON includes typography data"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")

        json_data = BrandingService.get_branding_json(theme)

        assert json_data["typography"] is not None
        assert "primary_font" in json_data["typography"]


class TestApplicationScope:
    """Tests for controlling where branding is applied"""

    def test_can_apply_to_multiple_components(self):
        """Test applying branding to multiple components"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")

        assert theme.apply_to_viewer is True
        assert theme.apply_to_scoreboard is True
        assert theme.apply_to_admin is True

    def test_can_disable_component_application(self):
        """Test disabling branding for specific component"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")
        theme.apply_to_admin = False

        assert theme.apply_to_viewer is True
        assert theme.apply_to_scoreboard is True
        assert theme.apply_to_admin is False


class TestColorValidation:
    """Tests for color validation utilities"""

    def test_validates_hex_color(self):
        """Test hex color validation"""
        valid_colors = ["#FF5733", "#000000", "#FFFFFF", "#3498DB"]
        
        for color in valid_colors:
            BrandingService._validate_hex_color(color)  # Should not raise

    def test_adds_hash_if_missing(self):
        """Test that validation adds # if missing"""
        result = BrandingService._validate_hex_color("FF5733")
        assert result.startswith("#")

    def test_rejects_invalid_colors(self):
        """Test that invalid colors raise error"""
        invalid_colors = ["GGGGGG", "FF573", "FF57333"]

        for color in invalid_colors:
            with pytest.raises(ValueError):
                BrandingService._validate_hex_color(color)


class TestEdgeCases:
    """Tests for edge cases"""

    def test_handles_very_long_org_name(self):
        """Test handling very long organization name"""
        long_name = "A" * 500

        theme = BrandingService.create_brand_theme("org1", long_name)

        assert theme.org_name == long_name

    def test_handles_unicode_in_asset_metadata(self):
        """Test handling unicode characters in asset metadata"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")

        theme = BrandingService.add_brand_asset(
            theme,
            asset_type="logo",
            name="Logo 🏏",
            url="https://example.com/logo.png",
            alt_text="Logo with cricket emoji 🏏",
        )

        asset = list(theme.assets.values())[0]
        assert "🏏" in asset.name
        assert "🏏" in asset.alt_text

    def test_handles_very_small_dimensions(self):
        """Test handling very small image dimensions"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")

        theme = BrandingService.add_brand_asset(
            theme,
            asset_type="icon",
            name="Favicon",
            url="https://example.com/favicon.ico",
            alt_text="Icon",
            dimensions=(16, 16),
        )

        asset = list(theme.assets.values())[0]
        assert asset.dimensions == (16, 16)

    def test_handles_very_large_dimensions(self):
        """Test handling very large image dimensions"""
        theme = BrandingService.create_brand_theme("org1", "Test Org")

        theme = BrandingService.add_brand_asset(
            theme,
            asset_type="banner",
            name="Banner",
            url="https://example.com/banner.jpg",
            alt_text="Banner",
            dimensions=(4000, 2000),
        )

        asset = list(theme.assets.values())[0]
        assert asset.dimensions == (4000, 2000)
