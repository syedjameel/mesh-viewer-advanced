"""
Configuration settings for the Mesh Viewer application.
This module centralizes all magic numbers and configurable parameters.
"""

from dataclasses import dataclass
from typing import Tuple
import glm


@dataclass
class CameraSettings:
    """Camera-related configuration."""
    # Default zoom distance from origin
    DEFAULT_ZOOM: float = 5.0
    
    # Fixed rotation angles for isometric view (in degrees)
    DEFAULT_ROTATION_X: float = -35.264
    DEFAULT_ROTATION_Y: float = -45.0
    
    # Projection parameters
    FIELD_OF_VIEW: float = 45.0  # degrees
    NEAR_PLANE: float = 0.1
    FAR_PLANE: float = 10000.0
    
    # Viewport reset scaling
    RESET_ZOOM_MULTIPLIER: float = 5.0


@dataclass
class InputSettings:
    """Input handling configuration."""
    # Mouse sensitivity values
    ROTATION_SENSITIVITY: float = 0.005
    PAN_SENSITIVITY_FACTOR: float = 0.01
    ZOOM_SENSITIVITY_FACTOR: float = 0.1
    
    # Matrix inversion safety threshold
    MATRIX_DETERMINANT_THRESHOLD: float = 1e-10


@dataclass
class RenderingSettings:
    """Rendering and graphics configuration."""
    # Default background color (RGB)
    BACKGROUND_COLOR: Tuple[float, float, float] = (0.12, 0.12, 0.12)
    
    # Mesh colors
    DEFAULT_MESH_COLOR: Tuple[float, float, float] = (0.65, 0.65, 0.75)
    SELECTED_MESH_COLOR: Tuple[float, float, float] = (0.3, 0.6, 0.9)
    
    # Axis arrows
    AXIS_SCALE_MULTIPLIER: float = 1.25
    
    # Lighting parameters
    AMBIENT_STRENGTH: float = 0.3
    

@dataclass
class MeshSettings:
    """Mesh processing configuration."""
    # Validation limits
    MAX_COORDINATE_VALUE: float = 1e6
    MAX_VERTICES: int = 1_000_000
    MAX_FACES: int = 2_000_000
    
    # BVH initialization
    DUMMY_RAY_ORIGIN: Tuple[float, float, float] = (1000.0, 1000.0, 1000.0)
    DUMMY_RAY_DIRECTION: Tuple[float, float, float] = (0.0, 0.0, -1.0)


@dataclass
class UISettings:
    """User interface configuration."""
    # Default window dimensions
    DEFAULT_WINDOW_WIDTH: int = 800
    DEFAULT_WINDOW_HEIGHT: int = 600
    
    # Progress overlay
    PROGRESS_WINDOW_WIDTH: float = 400.0
    PROGRESS_WINDOW_HEIGHT: float = 150.0
    
    # Viewport limits
    MAX_TEXTURE_SIZE: int = 8192
    MIN_VIEWPORT_SIZE: int = 1


@dataclass
class ThreadingSettings:
    """Threading and async operation configuration."""
    # Thread pool configuration
    DEFAULT_MAX_WORKERS: int = 4
    THREAD_NAME_PREFIX: str = "MeshViewer"
    
    # Task timeouts and delays
    TASK_UPDATE_INTERVAL: float = 0.016  # ~60 FPS
    PROGRESS_REPORT_INTERVAL: float = 0.1


@dataclass
class FileSettings:
    """File handling configuration."""
    # Supported mesh file extensions
    SUPPORTED_EXTENSIONS: Tuple[str, ...] = (
        '.obj', '.stl', '.ply', '.dae', '.gltf', '.glb', '.off', '.3mf'
    )
    
    # File size limits
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # Default directories (can be overridden)
    DEFAULT_MESH_DIRECTORIES: Tuple[str, ...] = (
        "~/Documents", 
        "~/Downloads",
        "./meshes"
    )


@dataclass
class GeometrySettings:
    """Geometry creation configuration."""
    # Axis arrow parameters
    ARROW_LENGTH: float = 1.0
    ARROW_RADIUS: float = 0.01
    ARROW_SECTIONS: int = 8
    
    # Axis colors (RGB)
    X_AXIS_COLOR: Tuple[float, float, float] = (1.0, 0.0, 0.0)  # Red
    Y_AXIS_COLOR: Tuple[float, float, float] = (0.0, 1.0, 0.0)  # Green
    Z_AXIS_COLOR: Tuple[float, float, float] = (0.0, 0.0, 1.0)  # Blue


class AppConfig:
    """Main application configuration container."""
    
    def __init__(self):
        self.camera = CameraSettings()
        self.input = InputSettings()
        self.rendering = RenderingSettings()
        self.mesh = MeshSettings()
        self.ui = UISettings()
        self.threading = ThreadingSettings()
        self.files = FileSettings()
        self.geometry = GeometrySettings()
    
    @classmethod
    def load_from_file(cls, config_path: str) -> 'AppConfig':
        """Load configuration from a file (future enhancement)."""
        # For now, return default configuration
        # TODO: Implement JSON/YAML config file loading
        return cls()
    
    def save_to_file(self, config_path: str) -> None:
        """Save configuration to a file (future enhancement)."""
        # TODO: Implement JSON/YAML config file saving
        pass


# Global configuration instance
config = AppConfig()


# Convenience functions for common config access
def get_camera_config() -> CameraSettings:
    """Get camera configuration."""
    return config.camera


def get_input_config() -> InputSettings:
    """Get input configuration."""
    return config.input


def get_rendering_config() -> RenderingSettings:
    """Get rendering configuration."""
    return config.rendering


def get_mesh_config() -> MeshSettings:
    """Get mesh configuration."""
    return config.mesh


def get_ui_config() -> UISettings:
    """Get UI configuration."""
    return config.ui


def get_threading_config() -> ThreadingSettings:
    """Get threading configuration."""
    return config.threading


def get_file_config() -> FileSettings:
    """Get file configuration."""
    return config.files


def get_geometry_config() -> GeometrySettings:
    """Get geometry configuration."""
    return config.geometry
