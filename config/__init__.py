"""
Configuration package for the Mesh Viewer application.
"""

from .settings import (
    AppConfig,
    config,
    get_camera_config,
    get_input_config,
    get_rendering_config,
    get_mesh_config,
    get_ui_config,
    get_threading_config,
    get_file_config,
    get_geometry_config,
)

__all__ = [
    'AppConfig',
    'config',
    'get_camera_config',
    'get_input_config', 
    'get_rendering_config',
    'get_mesh_config',
    'get_ui_config',
    'get_threading_config',
    'get_file_config',
    'get_geometry_config',
]