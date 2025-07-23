"""
Viewport UI Component for the Mesh Viewer application.

This module contains the ViewportComponent class that handles 3D viewport rendering,
user input processing, and viewport management.
"""

from typing import Tuple, Dict, Any
from imgui_bundle import imgui, ImVec2, hello_imgui
from .base_component import BaseUIComponent
from core.scene import Scene
from core.camera import ArcballCamera
from core.renderer import Renderer
from core.input_handler import InputHandler


class ViewportComponent(BaseUIComponent):
    """
    UI component responsible for 3D viewport rendering and interaction.
    
    This component handles:
    - 3D scene rendering through the viewport
    - Mouse and keyboard input processing
    - Viewport sizing and management
    - Object picking and selection
    """
    
    def __init__(self, renderer: Renderer, camera: ArcballCamera, 
                 input_handler: InputHandler, scene: Scene):
        """
        Initialize the viewport component.
        
        Args:
            renderer: The OpenGL renderer for 3D graphics
            camera: The camera controller for view transformations
            input_handler: Handler for mouse/keyboard input
            scene: The 3D scene containing meshes
        """
        super().__init__("Viewport")
        self.renderer = renderer
        self.camera = camera
        self.input_handler = input_handler
        self.scene = scene
        self.viewport_size = (800, 600)
        self.last_mouse_pos = (0, 0)
        
    def render(self) -> None:
        """Render the 3D viewport with scene content."""
        if not self.enabled:
            return
            
        try:
            self._update_viewport_size()
            self._render_scene()
            self._handle_input()
            
        except Exception as e:
            self.handle_error(e, "viewport rendering")
            
    def _update_viewport_size(self) -> None:
        """Update viewport size based on available ImGui content region."""
        size = imgui.get_content_region_avail()
        width, height = max(1, int(size.x)), max(1, int(size.y))

        if (width, height) != self.viewport_size:
            self.viewport_size = (width, height)
            self.renderer.resize(width, height)
            self.camera.set_viewport(width, height)
            self.logger.debug(f"Viewport resized to {width}x{height}")
            
    def _render_scene(self) -> None:
        """Render the 3D scene to the viewport texture."""
        # Get view options from external source (will be injected)
        view_options = getattr(self, '_view_options', {'wireframe': False, 'show_axes': True})
        
        # Render the scene
        self.renderer.render(self.scene, self.camera, view_options)
        
        # Display the rendered texture in ImGui
        imgui.image(
            self.renderer.texture.glo, 
            ImVec2(*self.viewport_size), 
            ImVec2(0, 1), 
            ImVec2(1, 0)
        )
        
    def _handle_input(self) -> None:
        """Handle mouse and keyboard input within the viewport."""
        if not imgui.is_item_hovered():
            return
            
        io = imgui.get_io()
        
        # Handle delete key for selected meshes
        if imgui.is_key_pressed(imgui.Key.delete):
            self._on_delete_key_pressed()
            
        # Get mouse position relative to viewport
        mouse_pos = imgui.get_mouse_pos()
        item_pos = imgui.get_item_rect_min()
        x, y = mouse_pos.x - item_pos.x, mouse_pos.y - item_pos.y
        
        # Handle mouse wheel (zoom)
        if io.mouse_wheel != 0:
            self.input_handler.handle_wheel(self.scene, self.camera, -io.mouse_wheel)
            
        # Handle mouse clicks and releases
        self._handle_mouse_input(x, y, io)
        
        # Handle mouse dragging
        if imgui.is_mouse_dragging(0) or imgui.is_mouse_dragging(1):
            self.input_handler.handle_drag(self.scene, self.camera, x, y)
            
    def _handle_mouse_input(self, x: float, y: float, io) -> None:
        """
        Handle mouse button clicks and releases.
        
        Args:
            x: Mouse X coordinate relative to viewport
            y: Mouse Y coordinate relative to viewport
            io: ImGui IO object for input state
        """
        for btn in [0, 1]:  # Left and right mouse buttons
            if imgui.is_mouse_clicked(btn):
                if io.key_ctrl and btn == 0:
                    # Ctrl+Left click for object picking
                    self._handle_object_picking(x, y)
                else:
                    # Regular mouse press
                    self.input_handler.handle_press(btn, True, x, y)
                    
            elif imgui.is_mouse_released(btn):
                self.input_handler.handle_press(btn, False, x, y)
                
    def _handle_object_picking(self, x: float, y: float) -> None:
        """
        Handle object picking with Ctrl+Left click.
        
        Args:
            x: Mouse X coordinate relative to viewport
            y: Mouse Y coordinate relative to viewport
        """
        try:
            width, height = self.viewport_size
            msg = self.input_handler.handle_pick(
                self.scene, self.camera, width, height, x, y
            )
            if msg:
                hello_imgui.log(hello_imgui.LogLevel.info, msg)
                self.logger.info(f"Object picking: {msg}")
                
        except Exception as e:
            self.handle_error(e, "object picking")
            
    def _on_delete_key_pressed(self) -> None:
        """Handle delete key press for removing selected meshes."""
        try:
            selected_meshes = [mesh for mesh in self.scene.meshes if mesh.selected]
            if selected_meshes and hasattr(self, '_delete_callback'):
                self._delete_callback()
                self.logger.info(f"Delete key pressed with {len(selected_meshes)} selected meshes")
                
        except Exception as e:
            self.handle_error(e, "delete key handling")
            
    def set_view_options(self, view_options: Dict[str, Any]) -> None:
        """
        Set the view options for rendering.
        
        Args:
            view_options: Dictionary containing view settings like wireframe, show_axes
        """
        self._view_options = view_options
        
    def set_delete_callback(self, callback) -> None:
        """
        Set the callback function for handling mesh deletion.
        
        Args:
            callback: Function to call when delete key is pressed
        """
        self._delete_callback = callback
        
    def get_viewport_size(self) -> Tuple[int, int]:
        """
        Get the current viewport size.
        
        Returns:
            Tuple of (width, height) in pixels
        """
        return self.viewport_size