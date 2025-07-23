"""
Controls Panel UI Component for the Mesh Viewer application.

This module contains the ControlsPanelComponent class that handles the main
control interface including buttons, options, and mesh management.
"""

from typing import List, Callable, Optional, Dict, Any, Set
from imgui_bundle import imgui, icons_fontawesome_6, hello_imgui
from .base_component import BaseUIComponent
from core.scene import Scene


class ControlsPanelComponent(BaseUIComponent):
    """
    UI component responsible for the main controls panel.
    
    This component handles:
    - Action buttons (Load, Delete, Reset)
    - View option toggles (Wireframe, Show Axes)
    - Mesh list display and management
    - Mesh visibility and selection controls
    """
    
    def __init__(self, scene: Scene):
        """
        Initialize the controls panel component.
        
        Args:
            scene: The 3D scene containing meshes
        """
        super().__init__("ControlsPanel")
        self.scene = scene
        self.font_title = None
        
        # Callbacks - will be injected by the main application
        self._load_callback: Optional[Callable] = None
        self._delete_callback: Optional[Callable] = None
        self._reset_callback: Optional[Callable] = None
        
        # View options - will be injected by the main application
        self._view_options: Dict[str, Any] = {'wireframe': False, 'show_axes': True}
        
    def render(self) -> None:
        """Render the controls panel with all UI elements."""
        if not self.enabled:
            return
            
        try:
            self._render_title()
            self._render_action_buttons()
            self._render_view_options()
            self._render_mesh_list()
            
        except Exception as e:
            self.handle_error(e, "controls panel rendering")
            
    def _render_title(self) -> None:
        """Render the panel title with styling."""
        if self.font_title:
            imgui.push_font(self.font_title)
        imgui.text("Controls")
        if self.font_title:
            imgui.pop_font()
        imgui.separator()
        
    def _render_action_buttons(self) -> None:
        """Render the main action buttons (Load, Delete, Reset)."""
        # Load Mesh button
        if imgui.button(
            f"{icons_fontawesome_6.ICON_FA_FOLDER_OPEN} Load Mesh...", 
            imgui.ImVec2(-1, 0)
        ):
            if self._load_callback:
                try:
                    self._load_callback()
                    self.logger.info("Load mesh callback triggered")
                except Exception as e:
                    self.handle_error(e, "load mesh callback")
                    
        # Delete Selected button
        has_selected = any(mesh.selected for mesh in self.scene.meshes)
        
        if not has_selected:
            imgui.push_style_var(imgui.StyleVar_.alpha, 0.5)
            
        button_clicked = imgui.button(
            f"{icons_fontawesome_6.ICON_FA_TRASH} Delete Selected", 
            imgui.ImVec2(-1, 0)
        )
        
        if not has_selected:
            imgui.pop_style_var()
            
        if button_clicked and has_selected:
            if self._delete_callback:
                try:
                    self._delete_callback()
                    self.logger.info("Delete selected callback triggered")
                except Exception as e:
                    self.handle_error(e, "delete selected callback")
                    
        # Reset View button
        if imgui.button(
            f"{icons_fontawesome_6.ICON_FA_ARROWS_ROTATE} Reset View", 
            imgui.ImVec2(-1, 0)
        ):
            if self._reset_callback:
                try:
                    self._reset_callback()
                    self.logger.info("Reset view callback triggered")
                except Exception as e:
                    self.handle_error(e, "reset view callback")
                    
    def _render_view_options(self) -> None:
        """Render view option checkboxes."""
        # Wireframe checkbox
        _, new_wireframe = imgui.checkbox("Wireframe", self._view_options['wireframe'])
        if new_wireframe != self._view_options['wireframe']:
            self._view_options['wireframe'] = new_wireframe
            self.logger.debug(f"Wireframe mode: {new_wireframe}")
            
        # Show Axes checkbox
        _, new_show_axes = imgui.checkbox("Show Axes", self._view_options['show_axes'])
        if new_show_axes != self._view_options['show_axes']:
            self._view_options['show_axes'] = new_show_axes
            self.logger.debug(f"Show axes: {new_show_axes}")
            
        imgui.separator()
        
    def _render_mesh_list(self) -> None:
        """Render the list of loaded meshes with controls."""
        # Mesh list title
        if self.font_title:
            imgui.push_font(self.font_title)
        imgui.text("Meshes")
        if self.font_title:
            imgui.pop_font()
        imgui.separator()
        
        if not self.scene.meshes:
            imgui.text("No meshes loaded.")
            return
            
        # Render each mesh in the list
        for i, mesh in enumerate(self.scene.meshes):
            self._render_mesh_item(i, mesh)
            
    def _render_mesh_item(self, index: int, mesh) -> None:
        """
        Render a single mesh item in the list.
        
        Args:
            index: The index of the mesh in the list
            mesh: The mesh object to render
        """
        try:
            # Visibility checkbox
            clicked, mesh.visible = imgui.checkbox(f"##vis_{index}", mesh.visible)
            if clicked:
                self.logger.debug(f"Mesh '{mesh.name}' visibility: {mesh.visible}")
                
            imgui.same_line()
            
            # Mesh icon with selection-based coloring
            icon = icons_fontawesome_6.ICON_FA_CUBE
            if mesh.selected:
                imgui.text_colored(imgui.ImVec4(0.4, 0.7, 1.0, 1.0), icon + " ")
            else:
                imgui.text(icon + " ")
                
            imgui.same_line()
            
            # Selectable mesh name
            clicked, mesh.selected = imgui.selectable(f"{mesh.name}", mesh.selected)
            if clicked:
                self.logger.debug(f"Mesh '{mesh.name}' selected: {mesh.selected}")
                
        except Exception as e:
            self.handle_error(e, f"rendering mesh item {index}")
            
    def set_callbacks(self, load_callback: Callable = None, 
                     delete_callback: Callable = None, 
                     reset_callback: Callable = None) -> None:
        """
        Set callback functions for button actions.
        
        Args:
            load_callback: Function to call when Load button is clicked
            delete_callback: Function to call when Delete button is clicked
            reset_callback: Function to call when Reset button is clicked
        """
        self._load_callback = load_callback
        self._delete_callback = delete_callback
        self._reset_callback = reset_callback
        
    def set_view_options(self, view_options: Dict[str, Any]) -> None:
        """
        Set the view options dictionary.
        
        Args:
            view_options: Dictionary containing view settings
        """
        self._view_options = view_options
        
    def get_view_options(self) -> Dict[str, Any]:
        """
        Get the current view options.
        
        Returns:
            Dictionary containing current view settings
        """
        return self._view_options
        
    def set_title_font(self, font) -> None:
        """
        Set the font to use for titles.
        
        Args:
            font: The ImGui font object to use for titles
        """
        self.font_title = font
        
    def get_selected_mesh_count(self) -> int:
        """
        Get the number of currently selected meshes.
        
        Returns:
            Number of selected meshes
        """
        return sum(1 for mesh in self.scene.meshes if mesh.selected)
        
    def get_visible_mesh_count(self) -> int:
        """
        Get the number of currently visible meshes.
        
        Returns:
            Number of visible meshes
        """
        return sum(1 for mesh in self.scene.meshes if mesh.visible)