import trimesh
import glm
from config import get_geometry_config

def make_axis_arrow(axis: str) -> tuple:
    """Creates a cylinder + cone arrow along given axis."""
    geometry_config = get_geometry_config()
    
    # Use configurable parameters for arrow geometry
    shaft_radius = geometry_config.ARROW_RADIUS
    shaft_height = geometry_config.ARROW_LENGTH * 0.9
    cone_radius = shaft_radius * 3
    cone_height = geometry_config.ARROW_LENGTH * 0.1
    
    shaft = trimesh.creation.cylinder(radius=shaft_radius, height=shaft_height, sections=geometry_config.ARROW_SECTIONS)
    shaft.apply_translation([0, 0, shaft_height / 2])

    cone = trimesh.creation.cone(radius=cone_radius, height=cone_height, sections=geometry_config.ARROW_SECTIONS)
    cone.apply_translation([0, 0, shaft_height])

    # Use configurable axis colors
    color_map = {
        "X": geometry_config.X_AXIS_COLOR, 
        "Y": geometry_config.Y_AXIS_COLOR, 
        "Z": geometry_config.Z_AXIS_COLOR
    }
    color = color_map[axis]
    
    transform = glm.mat4(1.0)
    if axis == "X":
        transform = glm.rotate(transform, glm.radians(90), glm.vec3(0, 1, 0))
    elif axis == "Y":
        transform = glm.rotate(transform, glm.radians(-90), glm.vec3(1, 0, 0))

    return shaft + cone, transform, color