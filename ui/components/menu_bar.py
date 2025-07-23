"""
Menu Bar UI Component for the Mesh Viewer application.

This module contains the MenuBarComponent class that handles the main menu bar
with File and View menus.
"""

from typing import Callable, Optional
from imgui_bundle import imgui, hello_imgui
from .base_component import BaseUIComponent


class MenuBarComponent(BaseUIComponent):
    """
    UI component responsible for the main menu bar.
    
    This component handles:
    - File menu (Load, Clear, Exit)
    - View menu (Wireframe, Show Axes, Reset View)
    - Menu item actions through callbacks
    """
    
    def __init__(self):
        """Initialize the menu bar component."""
        super().__init__("MenuBar")
        
        # Callbacks - will be injected by the main application
        self._load_callback: Optional[Callable] = None
        self._clear_callback: Optional[Callable] = None
        self._reset_view_callback: Optional[Callable] = None
        
        # View options - will be injected by the main application
        self._view_options = {'wireframe': False, 'show_axes': True}
        
    def render(self) -> None:
        """Render the menu bar with File and View menus."""
        if not self.enabled:
            return
            
        try:
            self._render_file_menu()
            self._render_view_menu()
            
        except Exception as e:
            self.handle_error(e, "menu bar rendering")
            
    def _render_file_menu(self) -> None:
        """Render the File menu with its items."""
        if imgui.begin_menu("File"):
            # Load Mesh menu item
            if imgui.menu_item("Load Mesh...", "Ctrl+O")[0]:
                if self._load_callback:
                    try:
                        self._load_callback()
                        self.logger.info("Load mesh menu item triggered")
                    except Exception as e:
                        self.handle_error(e, "load mesh menu callback")
                        
            # Clear All Meshes menu item
            if imgui.menu_item("Clear All Meshes")[0]:
                if self._clear_callback:
                    try:
                        self._clear_callback()
                        self.logger.info("Clear all meshes menu item triggered")
                    except Exception as e:
                        self.handle_error(e, "clear meshes menu callback")
                        
            imgui.separator()
            
            # Exit menu item
            if imgui.menu_item("Exit")[0]:
                hello_imgui.get_runner_params().app_shall_exit = True
                self.logger.info("Exit menu item triggered")
                
            imgui.end_menu()
            
    def _render_view_menu(self) -> None:
        """Render the View menu with its items."""
        if imgui.begin_menu("View"):
            # Wireframe toggle
            clicked, new_wireframe = imgui.menu_item(
                "Wireframe", "", self._view_options['wireframe']
            )
            if clicked:
                self._view_options['wireframe'] = new_wireframe
                self.logger.debug(f"Wireframe menu toggle: {new_wireframe}")
                
            # Show Axes toggle
            clicked, new_show_axes = imgui.menu_item(
                "Show Axes", "", self._view_options['show_axes']
            )
            if clicked:
                self._view_options['show_axes'] = new_show_axes
                self.logger.debug(f"Show axes menu toggle: {new_show_axes}")
                
            imgui.separator()
            
            # Reset View menu item
            if imgui.menu_item("Reset View")[0]:
                if self._reset_view_callback:
                    try:
                        self._reset_view_callback()
                        self.logger.info("Reset view menu item triggered")
                    except Exception as e:
                        self.handle_error(e, "reset view menu callback")
                        
            imgui.end_menu()
            
    def set_callbacks(self, load_callback: Callable = None,
                     clear_callback: Callable = None,
                     reset_view_callback: Callable = None) -> None:
        """
        Set callback functions for menu actions.
        
        Args:
            load_callback: Function to call when Load Mesh is selected
            clear_callback: Function to call when Clear All Meshes is selected
            reset_view_callback: Function to call when Reset View is selected
        """
        self._load_callback = load_callback
        self._clear_callback = clear_callback
        self._reset_view_callback = reset_view_callback
        
    def set_view_options(self, view_options: dict) -> None:
        """
        Set the view options dictionary.
        
        Args:
            view_options: Dictionary containing view settings
        """
        self._view_options = view_options
        
    def get_view_options(self) -> dict:
        """
        Get the current view options.
        
        Returns:
            Dictionary containing current view settings
        """
        return self._view_options