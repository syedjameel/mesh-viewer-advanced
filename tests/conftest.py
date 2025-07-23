"""
Pytest configuration and fixtures for the Mesh Viewer tests.
"""

import pytest
import numpy as np
import trimesh
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def simple_triangle_mesh():
    """Create a simple triangle mesh for testing."""
    vertices = np.array([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0], 
        [0.5, 1.0, 0.0]
    ], dtype=np.float32)
    
    faces = np.array([[0, 1, 2]], dtype=np.int32)
    
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    return mesh


@pytest.fixture
def cube_mesh():
    """Create a simple cube mesh for testing."""
    return trimesh.creation.box(extents=[1.0, 1.0, 1.0])


@pytest.fixture
def invalid_mesh():
    """Create an invalid mesh for testing error handling."""
    # Mesh with NaN values
    vertices = np.array([
        [0.0, 0.0, 0.0],
        [np.nan, 0.0, 0.0],
        [0.5, 1.0, 0.0]
    ], dtype=np.float32)
    
    faces = np.array([[0, 1, 2]], dtype=np.int32)
    
    # Note: trimesh will filter out NaN vertices, but we can test our validation
    return vertices, faces


@pytest.fixture
def mock_opengl_context():
    """Mock OpenGL context for testing without requiring actual OpenGL."""
    # This would need a proper mock implementation for full testing
    # For now, we'll skip tests that require OpenGL context
    pytest.skip("OpenGL context required for this test")


@pytest.fixture(scope="session")
def test_data_dir():
    """Path to test data directory."""
    return Path(__file__).parent / "fixtures"


# Configure logging for tests
import logging
logging.getLogger("mesh_viewer").setLevel(logging.WARNING)  # Reduce noise in tests