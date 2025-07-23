import glm
import numpy as np
import trimesh
from typing import List

from .mesh import Mesh

class Scene:
    """Manages all objects, transformations, and properties of the 3D scene."""
    def __init__(self):
        self.meshes: List[Mesh] = []
        self.rotation = glm.quat(1.0, 0.0, 0.0, 0.0)  # Identity
        self.translation = glm.vec3(0.0, 0.0, 0.0)
        self.center = glm.vec3(0.0, 0.0, 0.0)
        self.scale = 1.0

    def add_mesh(self, ctx, prog, filepath: str):
        """Loads a mesh from file and adds it to the scene."""
        try:
            trimesh_mesh = trimesh.load(filepath)
            name = trimesh_mesh.metadata.get('file_name', filepath.split('/')[-1])
            mesh = Mesh(ctx, prog, trimesh_mesh, name)
            self.meshes.append(mesh)
            return True, f"Loaded mesh: {name}"
        except Exception as e:
            return False, f"Failed to load mesh {filepath}: {e}"
            
    def create_mesh(self, ctx, prog, trimesh_mesh, name: str):
        """Creates a mesh from an already loaded trimesh object."""
        try:
            return Mesh(ctx, prog, trimesh_mesh, name)
        except Exception as e:
            return None

    def clear(self):
        """Releases all mesh resources and clears the scene."""
        for mesh in self.meshes:
            mesh.release()
        self.meshes.clear()
        self.reset_transformations()

    def get_bounds(self) -> tuple[np.ndarray, np.ndarray]:
        """Calculates the bounding box of all visible meshes."""
        if not self.meshes:
            return np.array([0, 0, 0]), np.array([0, 0, 0])

        min_bounds = np.array([np.inf] * 3)
        max_bounds = np.array([-np.inf] * 3)
        
        meshes_in_bounds = [m for m in self.meshes if m.visible]
        if not meshes_in_bounds:
            return np.array([0, 0, 0]), np.array([0, 0, 0])

        for mesh in meshes_in_bounds:
            bounds = mesh.trimesh_mesh.bounds
            min_bounds = np.minimum(min_bounds, bounds[0])
            max_bounds = np.maximum(max_bounds, bounds[1])
        
        return min_bounds, max_bounds

    def fit_to_view(self) -> float:
        """Calculates the center and scale needed to fit all meshes."""
        if not self.meshes:
            return 1.0

        min_bounds, max_bounds = self.get_bounds()
        center_point = (min_bounds + max_bounds) / 2.0
        size = np.max(max_bounds - min_bounds)

        self.center = glm.vec3(*center_point)
        # Use a small epsilon to avoid a scale of zero for a single point
        self.scale = max(size, 1e-6) 
        
        self.reset_transformations()
        return self.scale
        
    def reset_transformations(self):
        self.rotation = glm.quat(0.7071, 0.0, -0.7071, 0.0)     #isometric view
        self.translation = glm.vec3(0.0, 0.0, 0.0)