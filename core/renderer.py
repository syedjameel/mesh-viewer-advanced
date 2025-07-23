import moderngl
import glm
from pathlib import Path

from .scene import Scene
from .camera import ArcballCamera
from .mesh import Mesh
from utils.geometry import make_axis_arrow
from config import get_rendering_config, get_ui_config
from utils.logging import get_logger


class Renderer:
    """Handles all OpenGL rendering logic."""
    def __init__(self, width: int = None, height: int = None):
        self.logger = get_logger('renderer')
        
        ui_config = get_ui_config()
        if width is None:
            width = ui_config.DEFAULT_WINDOW_WIDTH
        if height is None:
            height = ui_config.DEFAULT_WINDOW_HEIGHT
            
        self.logger.info(f"Initializing renderer with dimensions {width}x{height}")
        
        self.ctx = moderngl.create_context()
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.CULL_FACE)
        
        self.prog = self._load_shaders()
        self.axis_arrows = self._create_axis_arrows()
        
        self.fbo = None
        self.texture = None
        self.resize(width, height)

    def _load_shaders(self):
        shader_dir = Path(__file__).parent.parent / "shaders"
        try:
            with open(shader_dir / "mesh.vert") as f:
                vertex_shader = f.read()
            with open(shader_dir / "mesh.frag") as f:
                fragment_shader = f.read()
        except (IOError, FileNotFoundError) as e:
            self.logger.warning(f"Could not load shader files: {e}")
            self.logger.info("Using fallback shaders")
            vertex_shader = self._get_fallback_vertex_shader()
            fragment_shader = self._get_fallback_fragment_shader()
            
        try:
            return self.ctx.program(
                vertex_shader=vertex_shader,
                fragment_shader=fragment_shader
            )
        except Exception as e:
            self.logger.error(f"Error creating shader program: {e}")
            raise RuntimeError("Failed to create shader program with both main and fallback shaders")

    def _get_fallback_vertex_shader(self) -> str:
        """Basic fallback vertex shader for when main shaders can't be loaded."""
        return """
        #version 330 core
        
        in vec3 in_position;
        in vec3 in_normal;
        
        uniform mat4 model;
        uniform mat4 view;
        uniform mat4 projection;
        uniform mat3 normal_matrix;
        
        out vec3 v_normal;
        out vec3 frag_pos;
        
        void main() {
            gl_Position = projection * view * model * vec4(in_position, 1.0);
            v_normal = normal_matrix * in_normal;
            frag_pos = vec3(model * vec4(in_position, 1.0));
        }
        """

    def _get_fallback_fragment_shader(self) -> str:
        """Basic fallback fragment shader for when main shaders can't be loaded."""
        return """
        #version 330 core
        
        in vec3 v_normal;
        in vec3 frag_pos;
        
        uniform vec3 light_pos;
        uniform vec3 view_pos;
        uniform vec3 color;
        
        out vec4 frag_color;
        
        void main() {
            // Simple diffuse lighting
            vec3 norm = normalize(v_normal);
            vec3 light_dir = normalize(light_pos - frag_pos);
            float diff = max(dot(norm, light_dir), 0.0);
            
            // Simple ambient + diffuse
            vec3 ambient = 0.3 * color;
            vec3 diffuse = diff * color;
            
            frag_color = vec4(ambient + diffuse, 1.0);
        }
        """
    
    def _create_axis_arrows(self) -> list:
        axis_data = []
        for axis in ["X", "Y", "Z"]:
            mesh, transform, color = make_axis_arrow(axis)
            axis_mesh = Mesh(self.ctx, self.prog, mesh, f"axis_{axis}")
            axis_data.append({"mesh": axis_mesh, "transform": transform, "color": color})
        return axis_data

    def resize(self, width: int, height: int):
        if self.fbo:
            self.fbo.release()
            self.texture.release()
            
        self.fbo = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture((width, height), 4)],
            depth_attachment=self.ctx.depth_texture((width, height))
        )
        self.texture = self.fbo.color_attachments[0]


    def render(self, scene: Scene, camera: ArcballCamera, view_options: dict):
        self.fbo.use()
        rendering_config = get_rendering_config()
        self.ctx.clear(*rendering_config.BACKGROUND_COLOR)
        
        view_mat = camera.get_view_matrix()
        proj_mat = camera.get_projection_matrix()
        
        self.prog['view'].write(view_mat)
        self.prog['projection'].write(proj_mat)
        self.prog['light_pos'].value = tuple(camera.position)
        self.prog['view_pos'].value = tuple(camera.position)

        trans_mat = glm.translate(glm.mat4(1.0), scene.translation)
        rot_mat = glm.mat4_cast(scene.rotation)
        center_offset = glm.translate(glm.mat4(1.0), -scene.center)
        model_mat = trans_mat * rot_mat * center_offset
        
        # Optimized rendering: batch meshes by render state to minimize state changes
        is_wireframe = view_options.get('wireframe', False)
        
        # Collect visible meshes
        visible_meshes = [mesh for mesh in scene.meshes if mesh.visible]
        
        if visible_meshes:
            self.prog['model'].write(model_mat)
            # Calculate normal matrix on CPU for better performance
            normal_matrix = glm.mat3(glm.transpose(glm.inverse(model_mat)))
            self.prog['normal_matrix'].write(normal_matrix)
            
            if is_wireframe:
                # Render all meshes in wireframe mode
                self.ctx.wireframe = True
                for mesh in visible_meshes:
                    color = rendering_config.SELECTED_MESH_COLOR if mesh.selected else rendering_config.DEFAULT_MESH_COLOR
                    mesh.render(color)
                self.ctx.wireframe = False
            else:
                # Render all meshes in solid mode (no state changes needed)
                for mesh in visible_meshes:
                    color = rendering_config.SELECTED_MESH_COLOR if mesh.selected else rendering_config.DEFAULT_MESH_COLOR
                    mesh.render(color)
            
        # Render axis arrows, which should also be affected by the scene's transformations
        if view_options.get('show_axes', True):
            # Make arrows bigger relative to the mesh
            arrow_scale_factor = scene.scale * rendering_config.AXIS_SCALE_MULTIPLIER 
            scale_mat = glm.scale(glm.mat4(1.0), glm.vec3(arrow_scale_factor))

            for axis in self.axis_arrows:
                axis_model_mat = model_mat * scale_mat * axis['transform']
                self.prog['model'].write(axis_model_mat)
                # Calculate normal matrix for each axis
                axis_normal_matrix = glm.mat3(glm.transpose(glm.inverse(axis_model_mat)))
                self.prog['normal_matrix'].write(axis_normal_matrix)
                axis['mesh'].render(axis['color'])

        self.ctx.screen.use()

    def release(self):
        """Release all OpenGL resources."""
        self.prog.release()
        for axis in self.axis_arrows:
            axis['mesh'].release()
        self.fbo.release()
        self.texture.release()