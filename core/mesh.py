import moderngl
import trimesh
import numpy as np
import os

from trimesh.ray.ray_triangle import RayMeshIntersector
from config import get_mesh_config

class Mesh:
    """Encapsulates a single mesh's data, including trimesh object and OpenGL resources."""
    def __init__(self, ctx: moderngl.Context, prog: moderngl.Program, trimesh_mesh: trimesh.Trimesh, name: str):
        self.ctx = ctx
        self.prog = prog
        self.trimesh_mesh = trimesh_mesh
        self.name = name

        self.visible = True
        self.selected = False
        
        # Validate and prepare mesh data
        self._validate_mesh_data(trimesh_mesh)
        
        vertices = self.trimesh_mesh.vertices.astype('f4')
        indices = self.trimesh_mesh.faces.flatten().astype('i4') if hasattr(trimesh_mesh, 'faces') else np.arange(len(vertices)).astype('i4')
        normals = self.trimesh_mesh.vertex_normals.astype('f4')

        # Optimize vertex data layout by interleaving vertices and normals
        # This improves cache performance by keeping related data together
        interleaved_data = np.column_stack((vertices, normals)).astype('f4')
        
        # Create OpenGL resources with interleaved data
        self.vbo = self.ctx.buffer(interleaved_data.tobytes())
        self.ibo = self.ctx.buffer(indices.tobytes())

        self.vao = self.ctx.vertex_array(
            self.prog,
            [
                (self.vbo, '3f 3f', 'in_position', 'in_normal'),
            ],
            self.ibo
        )

        # Create the ray-mesh intersector and pre-compute acceleration structures
        self.intersector = RayMeshIntersector(self.trimesh_mesh)
        # Force initialization of the BVH tree by performing a dummy ray test
        self._initialize_intersector()

    def _validate_mesh_data(self, trimesh_mesh: trimesh.Trimesh):
        """Validate mesh data to prevent crashes and ensure data integrity."""
        if trimesh_mesh is None:
            raise ValueError("Mesh object cannot be None")
        
        # Check vertices
        if not hasattr(trimesh_mesh, 'vertices') or len(trimesh_mesh.vertices) == 0:
            raise ValueError("Mesh has no vertices")
        
        vertices = trimesh_mesh.vertices
        if len(vertices.shape) != 2 or vertices.shape[1] != 3:
            raise ValueError(f"Invalid vertex data shape: {vertices.shape}, expected (N, 3)")
        
        # Check for invalid values in vertices
        if np.any(np.isnan(vertices)) or np.any(np.isinf(vertices)):
            raise ValueError("Mesh contains invalid vertex data (NaN or Inf values)")
        
        # Check vertex bounds to prevent extreme values
        mesh_config = get_mesh_config()
        max_coord = np.max(np.abs(vertices))
        if max_coord > mesh_config.MAX_COORDINATE_VALUE:
            raise ValueError(f"Mesh coordinates too large: max={max_coord:.2e}, limit={mesh_config.MAX_COORDINATE_VALUE}")
        
        # Check faces if they exist
        if hasattr(trimesh_mesh, 'faces'):
            faces = trimesh_mesh.faces 
            if len(faces) > 0:
                if len(faces.shape) != 2 or faces.shape[1] != 3:
                    raise ValueError(f"Invalid face data shape: {faces.shape}, expected (N, 3)")
                
                # Check that face indices are valid
                max_vertex_index = len(vertices) - 1
                if np.max(faces) > max_vertex_index:
                    raise ValueError("Face indices reference non-existent vertices")
                
                if np.min(faces) < 0:
                    raise ValueError("Face indices cannot be negative")
        
        # Check normals
        if hasattr(trimesh_mesh, 'vertex_normals'):
            normals = trimesh_mesh.vertex_normals
            if len(normals) != len(vertices):
                raise ValueError(f"Normal count ({len(normals)}) doesn't match vertex count ({len(vertices)})")
            
            if np.any(np.isnan(normals)) or np.any(np.isinf(normals)):
                raise ValueError("Mesh contains invalid normal data (NaN or Inf values)")

    def render(self, color: tuple):
        """Renders the mesh."""
        self.prog['object_color'].value = color
        self.vao.render()

    def _initialize_intersector(self):
        """Pre-compute the BVH tree for ray intersection by performing a dummy ray test."""
        try:
            # Use a dummy ray far away from the mesh to avoid actual intersections
            # This will force the BVH tree to be built
            mesh_config = get_mesh_config()
            dummy_origin = np.array([mesh_config.DUMMY_RAY_ORIGIN])
            dummy_direction = np.array([mesh_config.DUMMY_RAY_DIRECTION])
            self.intersector.intersects_any(dummy_origin, dummy_direction)
        except Exception:
            # Ignore any errors during initialization
            pass

    def release(self):
        """Releases OpenGL resources."""
        self.vbo.release()
        self.ibo.release()
        self.vao.release()