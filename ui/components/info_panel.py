"""
Info Panel UI Component for the Mesh Viewer application.

This module contains the InfoPanelComponent class that displays information
about selected meshes including statistics and properties.
"""

from typing import List, Optional
from imgui_bundle import imgui
from .base_component import BaseUIComponent
from core.scene import Scene


class InfoPanelComponent(BaseUIComponent):
    """
    UI component responsible for displaying mesh information.
    
    This component handles:
    - Display of selected mesh statistics
    - Mesh properties (vertex count, face count)
    - Expandable tree view for multiple selected meshes
    """
    
    def __init__(self, scene: Scene):
        """
        Initialize the info panel component.
        
        Args:
            scene: The 3D scene containing meshes
        """
        super().__init__("InfoPanel")
        self.scene = scene
        self.font_title = None
        
    def render(self) -> None:
        """Render the info panel with mesh information."""
        if not self.enabled:
            return
            
        try:
            self._render_title()
            self._render_mesh_info()
            
        except Exception as e:
            self.handle_error(e, "info panel rendering")
            
    def _render_title(self) -> None:
        """Render the panel title with styling."""
        if self.font_title:
            imgui.push_font(self.font_title)
        imgui.text("Info")
        if self.font_title:
            imgui.pop_font()
        imgui.separator()
        
    def _render_mesh_info(self) -> None:
        """Render information about selected meshes."""
        selected_meshes = self._get_selected_meshes()
        
        if not selected_meshes:
            imgui.text("No mesh selected.")
            return
            
        if len(selected_meshes) == 1:
            self._render_single_mesh_info(selected_meshes[0])
        else:
            self._render_multiple_mesh_info(selected_meshes)
            
    def _get_selected_meshes(self) -> List:
        """
        Get the list of currently selected meshes.
        
        Returns:
            List of selected mesh objects
        """
        try:
            return [mesh for mesh in self.scene.meshes if mesh.selected]
        except Exception as e:
            self.handle_error(e, "getting selected meshes")
            return []
            
    def _render_single_mesh_info(self, mesh) -> None:
        """
        Render detailed information for a single selected mesh.
        
        Args:
            mesh: The selected mesh object
        """
        try:
            # Mesh name as header
            imgui.text(f"Selected: {mesh.name}")
            imgui.separator()
            
            # Basic statistics
            if hasattr(mesh, 'trimesh_mesh') and mesh.trimesh_mesh is not None:
                vertex_count = len(mesh.trimesh_mesh.vertices)
                face_count = len(mesh.trimesh_mesh.faces)
                
                imgui.text(f"Vertices: {vertex_count:,}")
                imgui.text(f"Faces: {face_count:,}")
                
                # Additional properties if available
                if hasattr(mesh.trimesh_mesh, 'bounds'):
                    bounds = mesh.trimesh_mesh.bounds
                    size = bounds[1] - bounds[0]
                    
                    imgui.separator()
                    imgui.text("Bounding Box:")
                    imgui.text(f"  Size: {size[0]:.3f} × {size[1]:.3f} × {size[2]:.3f}")
                    
                if hasattr(mesh.trimesh_mesh, 'area'):
                    imgui.text(f"Surface Area: {mesh.trimesh_mesh.area:.3f}")
                    
                if hasattr(mesh.trimesh_mesh, 'volume') and mesh.trimesh_mesh.volume > 0:
                    imgui.text(f"Volume: {mesh.trimesh_mesh.volume:.3f}")
                    
            # Visibility and selection status
            imgui.separator()
            imgui.text(f"Visible: {'Yes' if mesh.visible else 'No'}")
            
        except Exception as e:
            self.handle_error(e, f"rendering single mesh info for {getattr(mesh, 'name', 'unknown')}")
            imgui.text("Error displaying mesh information")
            
    def _render_multiple_mesh_info(self, selected_meshes: List) -> None:
        """
        Render information for multiple selected meshes.
        
        Args:
            selected_meshes: List of selected mesh objects
        """
        try:
            imgui.text(f"Selected: {len(selected_meshes)} meshes")
            imgui.separator()
            
            # Summary statistics
            total_vertices = 0
            total_faces = 0
            
            for mesh in selected_meshes:
                if hasattr(mesh, 'trimesh_mesh') and mesh.trimesh_mesh is not None:
                    total_vertices += len(mesh.trimesh_mesh.vertices)
                    total_faces += len(mesh.trimesh_mesh.faces)
                    
            imgui.text(f"Total Vertices: {total_vertices:,}")
            imgui.text(f"Total Faces: {total_faces:,}")
            
            imgui.separator()
            
            # Individual mesh details in tree nodes
            for mesh in selected_meshes:
                if imgui.tree_node(f"{mesh.name}"):
                    self._render_mesh_tree_details(mesh)
                    imgui.tree_pop()
                    
        except Exception as e:
            self.handle_error(e, "rendering multiple mesh info")
            imgui.text("Error displaying mesh information")
            
    def _render_mesh_tree_details(self, mesh) -> None:
        """
        Render detailed information for a mesh within a tree node.
        
        Args:
            mesh: The mesh object to display details for
        """
        try:
            if hasattr(mesh, 'trimesh_mesh') and mesh.trimesh_mesh is not None:
                vertex_count = len(mesh.trimesh_mesh.vertices)
                face_count = len(mesh.trimesh_mesh.faces)
                
                imgui.text(f"Vertices: {vertex_count:,}")
                imgui.text(f"Faces: {face_count:,}")
                imgui.text(f"Visible: {'Yes' if mesh.visible else 'No'}")
            else:
                imgui.text("No mesh data available")
                
        except Exception as e:
            self.handle_error(e, f"rendering mesh tree details for {getattr(mesh, 'name', 'unknown')}")
            imgui.text("Error displaying mesh details")
            
    def set_title_font(self, font) -> None:
        """
        Set the font to use for titles.
        
        Args:
            font: The ImGui font object to use for titles
        """
        self.font_title = font
        
    def get_selected_count(self) -> int:
        """
        Get the number of currently selected meshes.
        
        Returns:
            Number of selected meshes
        """
        try:
            return len(self._get_selected_meshes())
        except Exception:
            return 0