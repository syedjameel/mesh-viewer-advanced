"""
Theme Manager for the Mesh Viewer application.

This module provides centralized theme and styling management for the ImGui interface,
including font loading and color scheme setup.
"""

from typing import Optional
from imgui_bundle import imgui, hello_imgui, ImVec2, ImVec4
from utils.logging import get_logger


class ThemeManager:
    """
    Manager class for UI theming and styling.
    
    This class handles:
    - ImGui style configuration
    - Color scheme setup
    - Font loading and management
    - Theme consistency across the application
    """
    
    def __init__(self):
        """Initialize the theme manager."""
        self.logger = get_logger("ui.theme_manager")
        self.font_title: Optional = None
        
    def setup_theme(self) -> None:
        """Setup the complete UI theme including colors and styling."""
        try:
            self._setup_style_parameters()
            self._setup_color_scheme()
            self.logger.info("UI theme setup completed")
            
        except Exception as e:
            self.logger.error(f"Error setting up theme: {e}")
            
    def _setup_style_parameters(self) -> None:
        """Configure ImGui style parameters."""
        style = imgui.get_style()
        
        # Spacing and padding
        style.window_padding = ImVec2(8, 8)
        style.frame_padding = ImVec2(6, 4)
        style.item_spacing = ImVec2(6, 4)
        style.item_inner_spacing = ImVec2(4, 4)
        
        # Rounding
        style.window_rounding = 5.0
        style.frame_rounding = 3.0
        style.scrollbar_rounding = 3.0
        style.grab_rounding = 3.0
        
        self.logger.debug("Style parameters configured")
        
    def _setup_color_scheme(self) -> None:
        """Configure the color scheme for the UI."""
        style = imgui.get_style()
        
        # Dark theme colors
        color_config = {
            imgui.Col_.window_bg: ImVec4(0.08, 0.08, 0.10, 1.00),
            imgui.Col_.child_bg: ImVec4(0.10, 0.10, 0.12, 1.00),
            imgui.Col_.frame_bg: ImVec4(0.15, 0.15, 0.18, 1.00),
            imgui.Col_.frame_bg_hovered: ImVec4(0.20, 0.20, 0.25, 1.00),
            imgui.Col_.frame_bg_active: ImVec4(0.25, 0.25, 0.30, 1.00),
            imgui.Col_.title_bg: ImVec4(0.10, 0.10, 0.12, 1.00),
            imgui.Col_.title_bg_active: ImVec4(0.12, 0.12, 0.15, 1.00),
            imgui.Col_.check_mark: ImVec4(0.40, 0.70, 1.00, 1.00),
            imgui.Col_.slider_grab: ImVec4(0.40, 0.70, 1.00, 1.00),
            imgui.Col_.slider_grab_active: ImVec4(0.50, 0.80, 1.00, 1.00),
            imgui.Col_.button: ImVec4(0.20, 0.20, 0.25, 1.00),
            imgui.Col_.button_hovered: ImVec4(0.30, 0.30, 0.35, 1.00),
            imgui.Col_.button_active: ImVec4(0.25, 0.25, 0.30, 1.00),
            imgui.Col_.header: ImVec4(0.20, 0.20, 0.25, 1.00),
            imgui.Col_.header_hovered: ImVec4(0.30, 0.30, 0.35, 1.00),
            imgui.Col_.header_active: ImVec4(0.25, 0.25, 0.30, 1.00),
            imgui.Col_.separator: ImVec4(0.30, 0.30, 0.35, 1.00),
            imgui.Col_.separator_hovered: ImVec4(0.40, 0.40, 0.45, 1.00),
            imgui.Col_.separator_active: ImVec4(0.50, 0.50, 0.60, 1.00),
            imgui.Col_.text_selected_bg: ImVec4(0.40, 0.70, 1.00, 0.35)
        }
        
        # Apply colors
        for color_id, color_value in color_config.items():
            style.set_color_(color_id, color_value)
            
        self.logger.debug("Color scheme configured")
        
    def load_fonts(self) -> None:
        """Load fonts for the application."""
        try:
            # Load default font with Font Awesome icons
            hello_imgui.imgui_default_settings.load_default_font_with_font_awesome_icons()
            
            # Load title font
            font_loading_params = hello_imgui.FontLoadingParams()
            font_loading_params.merge_font_awesome = True
            
            try:
                self.font_title = hello_imgui.load_font(
                    "fonts/Roboto/Roboto-Regular.ttf", 
                    18.0, 
                    font_loading_params
                )
                if self.font_title:
                    self.logger.info("Title font loaded successfully")
                else:
                    self.logger.warning("Title font loading returned None")
                    
            except Exception as font_error:
                self.logger.warning(f"Could not load title font: {font_error}")
                self.font_title = None
                
        except Exception as e:
            self.logger.error(f"Error loading fonts: {e}")
            
    def get_title_font(self) -> Optional:
        """
        Get the title font object.
        
        Returns:
            The title font object, or None if not loaded
        """
        return self.font_title
        
    def apply_accent_color(self, color: ImVec4) -> None:
        """
        Apply an accent color to relevant UI elements.
        
        Args:
            color: The accent color to apply
        """
        style = imgui.get_style()
        
        # Apply accent color to specific elements
        style.set_color_(imgui.Col_.check_mark, color)
        style.set_color_(imgui.Col_.slider_grab, color)
        style.set_color_(imgui.Col_.text_selected_bg, ImVec4(color.x, color.y, color.z, 0.35))
        
        # Lighter version for active states
        active_color = ImVec4(
            min(1.0, color.x + 0.1),
            min(1.0, color.y + 0.1), 
            min(1.0, color.z + 0.1),
            color.w
        )
        style.set_color_(imgui.Col_.slider_grab_active, active_color)
        
        self.logger.debug(f"Applied accent color: {color.x:.2f}, {color.y:.2f}, {color.z:.2f}")
        
    def get_style_summary(self) -> dict:
        """
        Get a summary of the current style configuration.
        
        Returns:
            Dictionary containing key style information
        """
        style = imgui.get_style()
        
        return {
            'window_rounding': style.window_rounding,
            'frame_rounding': style.frame_rounding,
            'window_padding': (style.window_padding.x, style.window_padding.y),
            'frame_padding': (style.frame_padding.x, style.frame_padding.y),
            'has_title_font': self.font_title is not None
        }
        
    def reset_to_default(self) -> None:
        """Reset the theme to ImGui default settings."""
        try:
            # Get a fresh style object (this resets to defaults)
            imgui.style_colors_dark()
            self.logger.info("Theme reset to ImGui defaults")
            
        except Exception as e:
            self.logger.error(f"Error resetting theme: {e}")
            
    def create_font_callback(self):
        """
        Create a callback function for font loading.
        
        Returns:
            Callback function suitable for hello_imgui font loading
        """
        def font_callback():
            self.load_fonts()
            
        return font_callback
        
    def create_theme_callback(self):
        """
        Create a callback function for theme setup.
        
        Returns:
            Callback function suitable for hello_imgui style setup
        """
        def theme_callback():
            self.setup_theme()
            
        return theme_callback