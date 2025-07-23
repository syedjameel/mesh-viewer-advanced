import glm
from config import get_camera_config

class ArcballCamera:
    """
    A simple camera that maintains a fixed orientation and zooms by moving along its Z-axis.
    It provides view and projection matrices for the renderer.
    """
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        
        # Load configuration
        camera_config = get_camera_config()
        self.zoom = camera_config.DEFAULT_ZOOM

        # Fixed rotation for a nice isometric-style view
        rot_x = glm.angleAxis(glm.radians(camera_config.DEFAULT_ROTATION_X), glm.vec3(1, 0, 0))
        rot_y = glm.angleAxis(glm.radians(camera_config.DEFAULT_ROTATION_Y), glm.vec3(0, 1, 0))
        self.rotation = rot_y * rot_x

        self._view = glm.mat4(1.0)
        self._projection = glm.mat4(1.0)
        self._view_dirty = True
        self._projection_dirty = True
        self._cached_position = None
        
        self.set_viewport(width, height)

    def set_viewport(self, width: int, height: int):
        self.width = width
        self.height = height
        
        camera_config = get_camera_config()
        aspect = width / float(height) if height > 0 else 1.0
        self._projection = glm.perspective(
            glm.radians(camera_config.FIELD_OF_VIEW), 
            aspect, 
            camera_config.NEAR_PLANE, 
            camera_config.FAR_PLANE
        )
        self._projection_dirty = False  # Just calculated

    def get_view_matrix(self) -> glm.mat4:
        """Get view matrix with caching for performance."""
        if self._view_dirty:
            # Recalculate view matrix only when camera has changed
            eye_pos = glm.vec3(0, 0, self.zoom)
            up = glm.vec3(0, 1, 0)
            
            # Apply the fixed rotation to the camera's position and up vector
            rot_mat = glm.mat4_cast(self.rotation)
            final_eye_pos = glm.vec3(rot_mat * glm.vec4(eye_pos, 1.0))
            final_up = glm.vec3(rot_mat * glm.vec4(up, 0.0))

            self._view = glm.lookAt(final_eye_pos, glm.vec3(0, 0, 0), final_up)
            self._view_dirty = False
            
        return self._view

    def get_projection_matrix(self) -> glm.mat4:
        return self._projection

    @property
    def position(self) -> glm.vec3:
        """Get camera's current world-space position with caching."""
        if self._cached_position is None or self._view_dirty:
            eye_pos = glm.vec3(0, 0, self.zoom)
            rot_mat = glm.mat4_cast(self.rotation)
            self._cached_position = glm.vec3(rot_mat * glm.vec4(eye_pos, 1.0))
        return self._cached_position
        
    def view_direction(self) -> glm.vec3:
        """Calculates the direction the camera is looking."""
        return glm.normalize(glm.vec3(0,0,0) - self.position)

    def screen_ray(self, x: float, y: float, width: int, height: int) -> glm.vec3:
        """Generates a ray from the camera through the specified screen coordinate."""
        view = self.get_view_matrix()
        proj = self.get_projection_matrix()
        viewport = glm.vec4(0, 0, width, height)

        p0 = glm.unProject(glm.vec3(x, height - y, 0.0), view, proj, viewport)
        p1 = glm.unProject(glm.vec3(x, height - y, 1.0), view, proj, viewport)
        return glm.normalize(p1 - p0)

    def set_zoom(self, zoom: float):
        """Set zoom and mark view as dirty."""
        if self.zoom != zoom:
            self.zoom = zoom
            self._view_dirty = True
            self._cached_position = None

    def set_rotation(self, rotation: glm.quat):
        """Set rotation and mark view as dirty."""
        self.rotation = rotation
        self._view_dirty = True
        self._cached_position = None

    def invalidate_cache(self):
        """Force recalculation of view matrix and position on next access."""
        self._view_dirty = True
        self._cached_position = None