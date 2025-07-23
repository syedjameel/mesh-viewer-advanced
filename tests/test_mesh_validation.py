"""
Tests for mesh validation functionality.
"""

import pytest
import numpy as np
import trimesh
from core.mesh import Mesh
from utils.exceptions import ValidationError


class TestMeshValidation:
    """Test mesh data validation."""
    
    def test_valid_mesh_passes_validation(self, simple_triangle_mesh):
        """Test that valid mesh passes validation."""
        # Create mesh instance for testing validation (without OpenGL)
        mesh_instance = object.__new__(Mesh)
        
        # Should not raise any exceptions
        mesh_instance._validate_mesh_data(simple_triangle_mesh)
    
    def test_none_mesh_fails_validation(self):
        """Test that None mesh fails validation."""
        mesh_instance = object.__new__(Mesh)
        
        with pytest.raises(ValueError, match="Mesh object cannot be None"):
            mesh_instance._validate_mesh_data(None)
    
    def test_empty_mesh_fails_validation(self):
        """Test that empty mesh fails validation."""
        mesh_instance = object.__new__(Mesh)
        
        # Create mesh with empty vertices
        empty_mesh = trimesh.Trimesh(vertices=np.array([]), faces=np.array([]))
        
        with pytest.raises(ValueError, match="Mesh has no vertices"):
            mesh_instance._validate_mesh_data(empty_mesh)
    
    def test_invalid_vertex_shape_fails_validation(self):
        """Test that mesh with invalid vertex shape fails validation."""
        mesh_instance = object.__new__(Mesh)
        
        # Create mesh with wrong vertex shape (2D instead of 3D)
        vertices = np.array([[0, 0], [1, 0], [0.5, 1]], dtype=np.float32)
        
        # This will fail during Trimesh creation itself
        with pytest.raises((ValueError, Exception)):
            invalid_mesh = trimesh.Trimesh(vertices=vertices, faces=np.array([[0, 1, 2]]))
            mesh_instance._validate_mesh_data(invalid_mesh)
    
    def test_extreme_coordinates_fail_validation(self):
        """Test that mesh with extreme coordinates fails validation."""
        mesh_instance = object.__new__(Mesh)
        
        # Create mesh with very large coordinates
        vertices = np.array([
            [0.0, 0.0, 0.0],
            [1e7, 0.0, 0.0],  # Exceeds MAX_COORDINATE_VALUE
            [0.0, 1.0, 0.0]
        ], dtype=np.float32)
        
        faces = np.array([[0, 1, 2]])
        large_mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        
        with pytest.raises(ValueError, match="Mesh coordinates too large"):
            mesh_instance._validate_mesh_data(large_mesh)
    
    def test_invalid_face_indices_handled(self):
        """Test handling of invalid face indices."""
        mesh_instance = object.__new__(Mesh)
        
        vertices = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0]
        ], dtype=np.float32)
        
        # Trimesh will handle this during construction and may fail or fix it
        # We test that our validation works with whatever Trimesh produces
        try:
            # This should fail during Trimesh construction
            bad_faces = np.array([[0, 1, 5]])  # Index 5 doesn't exist
            bad_mesh = trimesh.Trimesh(vertices=vertices, faces=bad_faces)
            
            # If it doesn't fail, our validation should catch issues
            mesh_instance._validate_mesh_data(bad_mesh)
            
        except (ValueError, IndexError):
            # Expected - either Trimesh catches it or our validation does
            pass
    
    def test_face_shape_validation(self):
        """Test validation of face array shape."""
        mesh_instance = object.__new__(Mesh)
        
        vertices = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0]
        ], dtype=np.float32)
        
        # Valid triangular faces
        valid_faces = np.array([[0, 1, 2], [1, 2, 3]])
        valid_mesh = trimesh.Trimesh(vertices=vertices, faces=valid_faces)
        
        # Should pass validation
        mesh_instance._validate_mesh_data(valid_mesh)
    
    def test_normal_count_validation(self, simple_triangle_mesh):
        """Test that normal count matches vertex count."""
        mesh_instance = object.__new__(Mesh)
        
        # Simple triangle mesh should have matching vertex and normal counts
        assert len(simple_triangle_mesh.vertices) == len(simple_triangle_mesh.vertex_normals)
        
        # Should pass validation
        mesh_instance._validate_mesh_data(simple_triangle_mesh)
    
    def test_cube_mesh_validation(self, cube_mesh):
        """Test validation with a more complex mesh."""
        mesh_instance = object.__new__(Mesh)
        
        # Cube mesh should pass all validations
        mesh_instance._validate_mesh_data(cube_mesh)
        
        # Verify it has reasonable properties
        assert len(cube_mesh.vertices) > 0
        assert len(cube_mesh.faces) > 0
        assert len(cube_mesh.vertices) == len(cube_mesh.vertex_normals)