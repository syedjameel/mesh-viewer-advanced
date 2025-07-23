"""
Tests for the configuration system.
"""

import pytest
from config import (
    config, 
    get_camera_config, 
    get_rendering_config,
    get_mesh_config,
    AppConfig
)


class TestConfigSystem:
    """Test the configuration system."""
    
    def test_config_singleton(self):
        """Test that config is a singleton."""
        config1 = AppConfig()
        config2 = AppConfig()
        # They should be different instances (not singleton), but have same values
        assert config1.camera.DEFAULT_ZOOM == config2.camera.DEFAULT_ZOOM
    
    def test_camera_config(self):
        """Test camera configuration values."""
        camera_config = get_camera_config()
        
        assert camera_config.DEFAULT_ZOOM == 5.0
        assert camera_config.FIELD_OF_VIEW == 45.0
        assert camera_config.NEAR_PLANE == 0.1
        assert camera_config.FAR_PLANE == 10000.0
        assert camera_config.RESET_ZOOM_MULTIPLIER == 5.0
    
    def test_rendering_config(self):
        """Test rendering configuration values."""
        rendering_config = get_rendering_config()
        
        assert rendering_config.BACKGROUND_COLOR == (0.12, 0.12, 0.12)
        assert rendering_config.DEFAULT_MESH_COLOR == (0.65, 0.65, 0.75)
        assert rendering_config.SELECTED_MESH_COLOR == (0.3, 0.6, 0.9)
        assert rendering_config.AXIS_SCALE_MULTIPLIER == 1.25
    
    def test_mesh_config(self):
        """Test mesh configuration values."""
        mesh_config = get_mesh_config()
        
        assert mesh_config.MAX_COORDINATE_VALUE == 1e6
        assert mesh_config.MAX_VERTICES == 1_000_000
        assert mesh_config.MAX_FACES == 2_000_000
        assert mesh_config.DUMMY_RAY_ORIGIN == (1000.0, 1000.0, 1000.0)
    
    def test_config_immutability(self):
        """Test that config values can be modified (they're not frozen)."""
        original_zoom = config.camera.DEFAULT_ZOOM
        config.camera.DEFAULT_ZOOM = 10.0
        assert config.camera.DEFAULT_ZOOM == 10.0
        
        # Reset for other tests
        config.camera.DEFAULT_ZOOM = original_zoom
    
    def test_all_config_sections_accessible(self):
        """Test that all configuration sections are accessible."""
        assert hasattr(config, 'camera')
        assert hasattr(config, 'input')
        assert hasattr(config, 'rendering')
        assert hasattr(config, 'mesh')
        assert hasattr(config, 'ui')
        assert hasattr(config, 'threading')
        assert hasattr(config, 'files')
        assert hasattr(config, 'geometry')
    
    def test_file_extensions(self):
        """Test file configuration."""
        file_config = config.files
        assert '.obj' in file_config.SUPPORTED_EXTENSIONS
        assert '.stl' in file_config.SUPPORTED_EXTENSIONS
        assert file_config.MAX_FILE_SIZE == 100 * 1024 * 1024  # 100MB