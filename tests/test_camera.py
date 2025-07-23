"""
Tests for the camera module.
"""

import pytest
import glm
import numpy as np
from core.camera import ArcballCamera


class TestArcballCamera:
    """Test the ArcballCamera class."""
    
    def test_camera_initialization(self):
        """Test camera initialization with default values."""
        camera = ArcballCamera(800, 600)
        
        assert camera.width == 800
        assert camera.height == 600
        assert camera.zoom == 5.0  # From config
        assert camera._view_dirty == True  # Should be dirty initially
    
    def test_viewport_setting(self):
        """Test setting viewport dimensions."""
        camera = ArcballCamera(800, 600)
        
        camera.set_viewport(1024, 768)
        assert camera.width == 1024
        assert camera.height == 768
        assert not camera._projection_dirty  # Should be clean after calculation
    
    def test_view_matrix_caching(self):
        """Test that view matrix is cached properly."""
        camera = ArcballCamera(800, 600)
        
        # First call should calculate
        assert camera._view_dirty == True
        view1 = camera.get_view_matrix()
        assert camera._view_dirty == False
        
        # Second call should use cache
        view2 = camera.get_view_matrix()
        assert camera._view_dirty == False
        
        # Matrices should be identical
        assert np.allclose(np.array(view1), np.array(view2))
    
    def test_zoom_invalidates_cache(self):
        """Test that changing zoom invalidates cache."""
        camera = ArcballCamera(800, 600)
        
        # Get initial view matrix
        view1 = camera.get_view_matrix()
        assert camera._view_dirty == False
        
        # Change zoom
        camera.set_zoom(10.0)
        assert camera._view_dirty == True
        assert camera.zoom == 10.0
        
        # Get new view matrix
        view2 = camera.get_view_matrix()
        assert camera._view_dirty == False
        
        # Matrices should be different
        assert not np.allclose(np.array(view1), np.array(view2))
    
    def test_position_caching(self):
        """Test that camera position is cached."""
        camera = ArcballCamera(800, 600)
        
        # First call should calculate
        pos1 = camera.position
        
        # Second call should use cache (same object)
        pos2 = camera.position
        assert pos1 == pos2
        
        # Changing zoom should invalidate position cache
        camera.set_zoom(10.0)
        pos3 = camera.position
        assert pos1 != pos3
    
    def test_screen_ray(self):
        """Test screen ray generation."""
        camera = ArcballCamera(800, 600)
        
        # Test ray generation doesn't crash
        ray = camera.screen_ray(400, 300, 800, 600)
        assert isinstance(ray, glm.vec3)
        
        # Ray should be normalized
        length = glm.length(ray)
        assert abs(length - 1.0) < 1e-6
    
    def test_view_direction(self):
        """Test view direction calculation."""
        camera = ArcballCamera(800, 600)
        
        view_dir = camera.view_direction()
        assert isinstance(view_dir, glm.vec3)
        
        # Should be normalized
        length = glm.length(view_dir)
        assert abs(length - 1.0) < 1e-6
    
    def test_projection_matrix(self):
        """Test projection matrix generation."""
        camera = ArcballCamera(800, 600)
        
        proj = camera.get_projection_matrix()
        assert isinstance(proj, glm.mat4)
        
        # Test aspect ratio handling
        camera.set_viewport(800, 400)  # 2:1 aspect ratio
        proj2 = camera.get_projection_matrix()
        assert not np.allclose(np.array(proj), np.array(proj2))
    
    def test_zero_height_handling(self):
        """Test handling of zero height in viewport."""
        camera = ArcballCamera(800, 600)
        
        # Should not crash with zero height
        camera.set_viewport(800, 0)
        proj = camera.get_projection_matrix()
        assert isinstance(proj, glm.mat4)
    
    def test_cache_invalidation(self):
        """Test manual cache invalidation."""
        camera = ArcballCamera(800, 600)
        
        # Get initial state
        view1 = camera.get_view_matrix()
        pos1 = camera.position
        assert camera._view_dirty == False
        
        # Manually invalidate
        camera.invalidate_cache()
        assert camera._view_dirty == True
        assert camera._cached_position is None
        
        # New calculations should work
        view2 = camera.get_view_matrix()
        pos2 = camera.position
        
        # Values should be the same (nothing actually changed)
        assert np.allclose(np.array(view1), np.array(view2))
        assert pos1 == pos2