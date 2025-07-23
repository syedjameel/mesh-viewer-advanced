import glm
import numpy as np

from .scene import Scene
from .camera import ArcballCamera
from config import get_input_config

class InputHandler:
    """
    Translates user input into scene transformations (rotation, translation).
    The camera remains fixed while the scene's objects move.
    """
    def __init__(self):
        self.is_left_mouse_pressed = False
        self.is_right_mouse_pressed = False
        self.last_mouse_pos = glm.vec2(0, 0)
        
    def handle_press(self, button: int, pressed: bool, x: float, y: float):
        if button == 0:  # Left
            self.is_left_mouse_pressed = pressed
        elif button == 1: # Right
            self.is_right_mouse_pressed = pressed
        
        if pressed:
            self.last_mouse_pos = glm.vec2(x, y)

    def handle_drag(self, scene: Scene, camera: ArcballCamera, x: float, y: float):
        current_pos = glm.vec2(x, y)
        delta = current_pos - self.last_mouse_pos
        self.last_mouse_pos = current_pos

        # We need the camera's orientation to define the correct axes for interaction
        view_mat = camera.get_view_matrix()
        cam_right_vec = glm.vec3(view_mat[0][0], view_mat[1][0], view_mat[2][0])
        cam_up_vec = glm.vec3(view_mat[0][1], view_mat[1][1], view_mat[2][1])
        
        if self.is_left_mouse_pressed:  # Rotate Scene
            input_config = get_input_config()
            sensitivity = input_config.ROTATION_SENSITIVITY

            # NEW, CORRECTED CODE uses camera's axes:
            # For horizontal mouse movement (delta.x), we rotate around the camera's "up" vector.
            rot_horizontal = glm.angleAxis(delta.x * sensitivity, cam_up_vec)
            
            # For vertical mouse movement (delta.y), we rotate around the camera's "right" vector.
            rot_vertical = glm.angleAxis(delta.y * sensitivity, cam_right_vec)

            # Combine the new rotations and apply them to the existing scene rotation.
            # This order ensures the rotation feels like a virtual trackball.
            scene.rotation = rot_horizontal * rot_vertical * scene.rotation
            
        elif self.is_right_mouse_pressed:  # Pan Scene (Translate)
            input_config = get_input_config()
            sensitivity = scene.scale * input_config.PAN_SENSITIVITY_FACTOR
            scene.translation += cam_right_vec * delta.x * sensitivity
            scene.translation -= cam_up_vec * delta.y * sensitivity

    def handle_wheel(self, scene: Scene, camera: ArcballCamera, delta: float):
        """Zooms by moving the scene towards/away from the fixed camera."""
        input_config = get_input_config()
        sensitivity = scene.scale * input_config.ZOOM_SENSITIVITY_FACTOR
        scene.translation += camera.view_direction() * delta * sensitivity

    def handle_pick(self, scene: Scene, camera: ArcballCamera, width: int, height: int, x: float, y: float):
        """Handles picking by transforming the ray into the scene's local space."""
        ray_dir_ws = camera.screen_ray(x, y, width, height)
        ray_origin_ws = camera.position

        # Build the model matrix exactly as in the renderer
        trans_mat = glm.translate(glm.mat4(1.0), scene.translation)
        rot_mat = glm.mat4_cast(scene.rotation)
        center_offset = glm.translate(glm.mat4(1.0), -scene.center)
        model_mat = trans_mat * rot_mat * center_offset
        
        # Calculate the inverse model matrix for transforming the ray
        # Add safety check to prevent crashes from singular matrices
        try:
            input_config = get_input_config()
            det = glm.determinant(model_mat)
            if abs(det) < input_config.MATRIX_DETERMINANT_THRESHOLD:
                # Matrix is singular/near-singular, cannot invert safely
                return None
            inv_model_mat = glm.inverse(model_mat)
        except Exception:
            # Fallback if inverse operation fails
            return None
        
        # Transform ray origin and direction to model space
        origin_ms = glm.vec3(inv_model_mat * glm.vec4(ray_origin_ws, 1.0))
        dir_ms = glm.normalize(glm.vec3(inv_model_mat * glm.vec4(ray_dir_ws, 0.0)))

        closest_hit = None
        closest_distance = float('inf')
        closest_mesh = None

        for mesh in scene.meshes:
            if not mesh.visible: continue
            
            # Use numpy arrays for trimesh ray intersection
            locs, idx, rays = mesh.intersector.intersects_location(
                np.array([[origin_ms.x, origin_ms.y, origin_ms.z]]), 
                np.array([[dir_ms.x, dir_ms.y, dir_ms.z]])
            )
            
            if len(locs):
                # Find the closest intersection point
                for i, loc in enumerate(locs):
                    # Calculate distance from ray origin to hit point
                    hit_vec = glm.vec3(loc[0], loc[1], loc[2]) - origin_ms
                    distance = glm.length(hit_vec)
                    
                    # Check if this is the closest hit so far
                    if distance < closest_distance:
                        closest_distance = distance
                        closest_hit = loc
                        closest_mesh = mesh
        
        if closest_mesh:
            closest_mesh.selected = not closest_mesh.selected
            
            # Model space coordinates (mesh's local coordinates)
            model_coords = closest_hit
            
            # World space coordinates (transform back to world space)
            hit_point_ms = glm.vec4(closest_hit[0], closest_hit[1], closest_hit[2], 1.0)
            hit_point_ws = glm.vec3(model_mat * hit_point_ms)
            world_coords = (hit_point_ws.x, hit_point_ws.y, hit_point_ws.z)
            
            return (f"Toggled selection on {closest_mesh.name}.\n"
                   f"Model coords: {model_coords[0]:.3f}, {model_coords[1]:.3f}, {model_coords[2]:.3f}\n"
                   f"World coords: {world_coords[0]:.3f}, {world_coords[1]:.3f}, {world_coords[2]:.3f}")
            
        return None