import os
import time
import trimesh
from imgui_bundle import hello_imgui, imgui, ImVec2, ImVec4, icons_fontawesome_6
from pathlib import Path

from core.scene import Scene
from core.renderer import Renderer
from core.camera import ArcballCamera
from core.input_handler import InputHandler
from utils.file_io import prompt_load_mesh_paths
from utils.async_task import TaskManager, TaskStatus
from ui.progress_overlay import ProgressOverlay


class MainApplication:
    def __init__(self, task_manager: TaskManager):
        self.scene = Scene()
        self.camera = ArcballCamera(800, 600)
        self.input_handler = InputHandler()
        self.renderer = None  
        self.view_options = {'wireframe': False, 'show_axes': True}
        self.viewport_size = (800, 600)
        self.last_mouse_pos = (0, 0)
        self.loaded_mesh_paths = set()
        self.font_title = None  # For title fonts
        
        # Task management
        self.task_manager = task_manager
        self.progress_overlay = ProgressOverlay()

    def _post_init(self):
        self.renderer = Renderer(*self.viewport_size)
        self.reset_view()

    def _load_meshes(self):
        filepaths = prompt_load_mesh_paths()
        if not filepaths: return
        
        # Create and start a background task for loading meshes
        task_id = f"load_meshes_{int(time.time())}"
        task = self.task_manager.create_task(
            task_id, 
            self._load_meshes_task, 
            filepaths
        )
        task.start()
        
        # Show the progress overlay
        self.progress_overlay.show(
            "Loading Meshes", 
            f"Loading {len(filepaths)} mesh(es)...", 
            0.0,
            True,
            lambda: self.task_manager.cancel_task(task_id),
            task_id
        )
    
    def _load_meshes_task(self, filepaths, report_progress=None, is_canceled=None):
        """Background task for loading meshes."""
        new_mesh_loaded = False
        results = []
        
        for i, path in enumerate(filepaths):
            # Check for cancellation
            if is_canceled and is_canceled():
                # Return what we have so far when canceled
                return {
                    "success": new_mesh_loaded,
                    "results": results,
                    "canceled": True
                }
                
            # Report progress
            if report_progress:
                progress = (i / len(filepaths))
                report_progress(progress, f"Loading {os.path.basename(path)}...")
                
            # Skip duplicates
            abs_path = os.path.abspath(path)
            if abs_path in self.loaded_mesh_paths:
                results.append({
                    "path": path,
                    "success": False,
                    "message": f"Skipping duplicate mesh: {os.path.basename(path)}",
                    "level": hello_imgui.LogLevel.warning
                })
                continue
            
            try:
                # Load the mesh with trimesh first to validate it
                trimesh_mesh = trimesh.load(path)
                name = trimesh_mesh.metadata.get('file_name', path.split('/')[-1])
                
                # Store result for processing in the main thread
                results.append({
                    "path": path,
                    "abs_path": abs_path,
                    "trimesh_mesh": trimesh_mesh,
                    "name": name,
                    "success": True,
                    "message": f"Loaded mesh: {name}",
                    "level": hello_imgui.LogLevel.info
                })
                new_mesh_loaded = True
                
            except Exception as e:
                results.append({
                    "path": path,
                    "success": False,
                    "message": f"Failed to load mesh {path}: {e}",
                    "level": hello_imgui.LogLevel.error
                })
        
        # Report completion
        if report_progress:
            report_progress(1.0, "Finalizing...")
            
        return {
            "success": new_mesh_loaded,
            "results": results,
            "canceled": False
        }
    
    def _process_mesh_loading_results(self, task_id):
        """Process the results of a mesh loading task."""
        task = self.task_manager.get_task(task_id)
        if not task or task.status != TaskStatus.COMPLETED:
            return
            
        result = task.result
        if not result:
            return
            
        # If the task was canceled, just log it and clean up
        if result.get("canceled", False):
            hello_imgui.log(hello_imgui.LogLevel.warning, "Mesh loading was canceled")
            self.progress_overlay.hide()
            self.task_manager.remove_task(task_id)
            return
            
        # Update progress overlay to show we're initializing meshes
        self.progress_overlay.update(1.0, "Initializing meshes...")
            
        # Process each mesh result
        for mesh_result in result["results"]:
            # Log the result
            hello_imgui.log(mesh_result["level"], mesh_result["message"])
            
            # If successful, add the mesh to the scene
            if mesh_result["success"]:
                try:
                    # Create the mesh in the main thread with OpenGL context
                    mesh = self.scene.create_mesh(
                        self.renderer.ctx, 
                        self.renderer.prog, 
                        mesh_result["trimesh_mesh"], 
                        mesh_result["name"]
                    )
                    
                    if mesh:
                        self.scene.meshes.append(mesh)
                        self.loaded_mesh_paths.add(mesh_result["abs_path"])
                except Exception as e:
                    hello_imgui.log(hello_imgui.LogLevel.error, f"Error creating mesh: {e}")
        
        # Reset view if any meshes were loaded
        if result["success"]:
            self.reset_view()
            
        # Hide the progress overlay
        self.progress_overlay.hide()
        
        # Clean up the task
        self.task_manager.remove_task(task_id)

    def reset_view(self):
        from config import get_camera_config
        camera_config = get_camera_config()
        scale = self.scene.fit_to_view()
        self.camera.set_zoom(scale * camera_config.RESET_ZOOM_MULTIPLIER)
        self.scene.reset_transformations()

    def _render_menu_bar(self):
        if imgui.begin_menu("File"):
            if imgui.menu_item("Load Mesh...", "Ctrl+O")[0]: 
                self._load_meshes()
            if imgui.menu_item("Clear All Meshes")[0]:
                self.scene.clear()
                self.loaded_mesh_paths.clear()
                self.reset_view()
                hello_imgui.log(hello_imgui.LogLevel.info, "Cleared all meshes.")
            imgui.separator()
            if imgui.menu_item("Exit")[0]: 
                hello_imgui.get_runner_params().app_shall_exit = True
            imgui.end_menu()
        
        if imgui.begin_menu("View"):
            _, self.view_options['wireframe'] = imgui.menu_item("Wireframe", "", self.view_options['wireframe'])
            _, self.view_options['show_axes'] = imgui.menu_item("Show Axes", "", self.view_options['show_axes'])
            if imgui.menu_item("Reset View")[0]: 
                self.reset_view()
            imgui.end_menu()

    def _delete_selected_meshes(self):
        if not self.scene.meshes:
            return
            
        selected_indices = [i for i, mesh in enumerate(self.scene.meshes) if mesh.selected]
        if not selected_indices:
            return
            
        for idx in sorted(selected_indices, reverse=True):
            mesh = self.scene.meshes[idx]
            for path in list(self.loaded_mesh_paths):
                if mesh.name in path:
                    self.loaded_mesh_paths.remove(path)
            mesh.release()
            del self.scene.meshes[idx]
        
        hello_imgui.log(hello_imgui.LogLevel.info, f"Deleted {len(selected_indices)} mesh(es).")
        self.reset_view()
        
    def _render_controls_panel(self):
        # Title with styling
        if self.font_title:
            imgui.push_font(self.font_title)
        imgui.text("Controls")
        if self.font_title:
            imgui.pop_font()
        imgui.separator()

        # Styled buttons with icons
        if imgui.button(f"{icons_fontawesome_6.ICON_FA_FOLDER_OPEN} Load Mesh...", imgui.ImVec2(-1, 0)): 
            self._load_meshes()
        
        if imgui.button(f"{icons_fontawesome_6.ICON_FA_TRASH} Delete Selected", imgui.ImVec2(-1, 0)) and any(mesh.selected for mesh in self.scene.meshes): 
            self._delete_selected_meshes()
            
        if imgui.button(f"{icons_fontawesome_6.ICON_FA_ARROWS_ROTATE} Reset View", imgui.ImVec2(-1, 0)): 
            self.reset_view()

        # Checkboxes with consistent styling
        _, self.view_options['wireframe'] = imgui.checkbox("Wireframe", self.view_options['wireframe'])
        _, self.view_options['show_axes'] = imgui.checkbox("Show Axes", self.view_options['show_axes'])

        imgui.separator()
        
        # Meshes list
        if self.font_title:
            imgui.push_font(self.font_title)
        imgui.text("Meshes")
        if self.font_title:
            imgui.pop_font()
        imgui.separator()
            
        if not self.scene.meshes:
            imgui.text("No meshes loaded.")
        else:
            for i, mesh in enumerate(self.scene.meshes):
                clicked, mesh.visible = imgui.checkbox(f"##vis_{i}", mesh.visible)
                imgui.same_line()
                
                # Use text_colored instead of push/pop style
                icon = icons_fontawesome_6.ICON_FA_CUBE
                if mesh.selected:
                    imgui.text_colored(imgui.ImVec4(0.4, 0.7, 1.0, 1.0), icon + " ")
                else:
                    imgui.text(icon + " ")
                    
                imgui.same_line()
                clicked, mesh.selected = imgui.selectable(f"{mesh.name}", mesh.selected)

    def _render_info_panel(self):
        # Title with styling
        if self.font_title:
            imgui.push_font(self.font_title)
        imgui.text("Info")
        if self.font_title:
            imgui.pop_font()
        imgui.separator()
        
        selected_meshes = [m for m in self.scene.meshes if m.selected]
        if not selected_meshes:
            imgui.text("No mesh selected.")
        else:
            for mesh in selected_meshes:
                if imgui.tree_node(f"{mesh.name}"):
                    imgui.text(f"Vertices: {len(mesh.trimesh_mesh.vertices)}")
                    imgui.text(f"Faces: {len(mesh.trimesh_mesh.faces)}")
                    imgui.tree_pop()
                    
    def _render_viewport(self):
        size = imgui.get_content_region_avail()
        width, height = max(1, int(size.x)), max(1, int(size.y))

        if (width, height) != self.viewport_size:
            self.viewport_size = (width, height)
            self.renderer.resize(width, height)
            self.camera.set_viewport(width, height)

        self.renderer.render(self.scene, self.camera, self.view_options)
        
        imgui.image(self.renderer.texture.glo, ImVec2(*self.viewport_size), ImVec2(0, 1), ImVec2(1, 0))
        
        # Check for delete key press
        io = imgui.get_io()
        if imgui.is_key_pressed(imgui.Key.delete) and any(mesh.selected for mesh in self.scene.meshes):
            self._delete_selected_meshes()
        
        if imgui.is_item_hovered():
            mouse_pos = imgui.get_mouse_pos()
            item_pos = imgui.get_item_rect_min()
            x, y = mouse_pos.x - item_pos.x, mouse_pos.y - item_pos.y
            
            if io.mouse_wheel != 0:
                self.input_handler.handle_wheel(self.scene, self.camera, -io.mouse_wheel)

            for btn in [0, 1]:
                if imgui.is_mouse_clicked(btn):
                    if io.key_ctrl and btn == 0:
                        msg = self.input_handler.handle_pick(self.scene, self.camera, width, height, x, y)
                        if msg: hello_imgui.log(hello_imgui.LogLevel.info, msg)
                    else:
                        self.input_handler.handle_press(btn, True, x, y)

                if imgui.is_mouse_released(btn):
                    self.input_handler.handle_press(btn, False, x, y)
            
            if imgui.is_mouse_dragging(0) or imgui.is_mouse_dragging(1):
                self.input_handler.handle_drag(self.scene, self.camera, x, y)

    def _update_tasks(self):
        """Update all background tasks and process completed ones."""
        # Check if cancel was requested in the UI
        if self.progress_overlay.visible and self.progress_overlay.cancel_requested:
            self.progress_overlay.cancel_requested = False
            if self.progress_overlay.active_task_id and self.progress_overlay.on_cancel:
                # Cancel the task safely from the main thread
                try:
                    self.task_manager.cancel_task(self.progress_overlay.active_task_id)
                except Exception as e:
                    hello_imgui.log(hello_imgui.LogLevel.error, f"Error canceling task: {e}")
        
        # Update all tasks
        changed_tasks = self.task_manager.update_all()
        
        for task_id in changed_tasks:
            task = self.task_manager.get_task(task_id)
            if not task:
                continue
                
            # Update progress overlay if this is the active task
            if task.status == TaskStatus.RUNNING and self.progress_overlay.visible:
                if task_id == self.progress_overlay.active_task_id:
                    self.progress_overlay.update(task.progress)
                
            # Process completed mesh loading tasks
            if task_id.startswith("load_meshes_") and task.status == TaskStatus.COMPLETED:
                self._process_mesh_loading_results(task_id)
                
            # Handle failed tasks
            elif task.status == TaskStatus.FAILED:
                hello_imgui.log(hello_imgui.LogLevel.error, f"Task {task_id} failed: {task.error}")
                if task_id == self.progress_overlay.active_task_id:
                    self.progress_overlay.hide()
                self.task_manager.remove_task(task_id)
                
            # Handle canceled tasks
            elif task.status == TaskStatus.CANCELED:
                hello_imgui.log(hello_imgui.LogLevel.warning, f"Task {task_id} was canceled")
                if task_id == self.progress_overlay.active_task_id:
                    self.progress_overlay.hide()
                self.task_manager.remove_task(task_id)
    
    def run(self):
        runner_params = hello_imgui.RunnerParams()
        runner_params.app_window_params.window_title = "Mesh Viewer"
        runner_params.app_window_params.window_geometry.size = (1600, 900)


        runner_params.docking_params.main_dock_space_node_flags |= (
            imgui.DockNodeFlags_.auto_hide_tab_bar
        )
        
        runner_params.imgui_window_params.default_imgui_window_type = hello_imgui.DefaultImGuiWindowType.provide_full_screen_dock_space
        runner_params.imgui_window_params.show_menu_bar = True
        runner_params.imgui_window_params.show_status_bar = False
        runner_params.fps_idling.enable_idling = False
        
        # Font loading callback
        def load_fonts():
            # Load default font with Font Awesome icons
            hello_imgui.imgui_default_settings.load_default_font_with_font_awesome_icons()
            
            # Load title font
            font_loading_params = hello_imgui.FontLoadingParams()
            font_loading_params.merge_font_awesome = True
            self.font_title = hello_imgui.load_font("fonts/Roboto/Roboto-Regular.ttf", 18.0, font_loading_params)
        
        runner_params.callbacks.load_additional_fonts = load_fonts
        
        # Theme setup callback
        def setup_theme():
            style = imgui.get_style()
            
            # General
            style.window_padding = imgui.ImVec2(8, 8)
            style.frame_padding = imgui.ImVec2(6, 4)
            style.item_spacing = imgui.ImVec2(6, 4)
            style.item_inner_spacing = imgui.ImVec2(4, 4)
            style.window_rounding = 5.0
            style.frame_rounding = 3.0
            style.scrollbar_rounding = 3.0
            style.grab_rounding = 3.0

            # Set colors
            style.set_color_(imgui.Col_.window_bg, imgui.ImVec4(0.08, 0.08, 0.10, 1.00))
            style.set_color_(imgui.Col_.child_bg, imgui.ImVec4(0.10, 0.10, 0.12, 1.00))
            style.set_color_(imgui.Col_.frame_bg, imgui.ImVec4(0.15, 0.15, 0.18, 1.00))
            style.set_color_(imgui.Col_.frame_bg_hovered, imgui.ImVec4(0.20, 0.20, 0.25, 1.00))
            style.set_color_(imgui.Col_.frame_bg_active, imgui.ImVec4(0.25, 0.25, 0.30, 1.00))
            style.set_color_(imgui.Col_.title_bg, imgui.ImVec4(0.10, 0.10, 0.12, 1.00))
            style.set_color_(imgui.Col_.title_bg_active, imgui.ImVec4(0.12, 0.12, 0.15, 1.00))
            style.set_color_(imgui.Col_.check_mark, imgui.ImVec4(0.40, 0.70, 1.00, 1.00))
            style.set_color_(imgui.Col_.slider_grab, imgui.ImVec4(0.40, 0.70, 1.00, 1.00))
            style.set_color_(imgui.Col_.slider_grab_active, imgui.ImVec4(0.50, 0.80, 1.00, 1.00))
            style.set_color_(imgui.Col_.button, imgui.ImVec4(0.20, 0.20, 0.25, 1.00))
            style.set_color_(imgui.Col_.button_hovered, imgui.ImVec4(0.30, 0.30, 0.35, 1.00))
            style.set_color_(imgui.Col_.button_active, imgui.ImVec4(0.25, 0.25, 0.30, 1.00))
            style.set_color_(imgui.Col_.header, imgui.ImVec4(0.20, 0.20, 0.25, 1.00))
            style.set_color_(imgui.Col_.header_hovered, imgui.ImVec4(0.30, 0.30, 0.35, 1.00))
            style.set_color_(imgui.Col_.header_active, imgui.ImVec4(0.25, 0.25, 0.30, 1.00))
            style.set_color_(imgui.Col_.separator, imgui.ImVec4(0.30, 0.30, 0.35, 1.00))
            style.set_color_(imgui.Col_.separator_hovered, imgui.ImVec4(0.40, 0.40, 0.45, 1.00))
            style.set_color_(imgui.Col_.separator_active, imgui.ImVec4(0.50, 0.50, 0.60, 1.00))
            style.set_color_(imgui.Col_.text_selected_bg, imgui.ImVec4(0.40, 0.70, 1.00, 0.35))

            # hello_imgui.apply_theme( hello_imgui.ImGuiTheme_.so_dark_accent_blue)
            # tweaked_theme = hello_imgui.get_runner_params().imgui_window_params.tweaked_theme
            # tweaked_theme.theme = hello_imgui.ImGuiTheme_.darcula_darker
            # tweaked_theme.tweaks.rounding = 4.0
            
            # tweaked_theme.tweaks.value_multiplier_bg = 0.5
            # tweaked_theme.tweaks.value_multiplier_frame_bg = 0.5
            
            # hello_imgui.apply_tweaked_theme(tweaked_theme=tweaked_theme)
            
            # imgui.get_style().disabled_alpha     = 0.4000000238418579
            # imgui.get_style().window_rounding    = 0
            # imgui.get_style().window_border_size = 0.2
            # imgui.get_style().window_menu_button_position =  imgui.Dir.right
            # imgui.get_style().window_padding = (10, 10)
            # imgui.get_style().frame_rounding      = 4
            # imgui.get_style().popup_rounding      = 4
            # imgui.get_style().tab_rounding        = 4
            # imgui.get_style().tab_bar_border_size = 0
            # imgui.get_style().frame_padding = (10, 8)
        
            # imgui.get_style().set_color_(imgui.Col_.text,                         ImVec4(0.8, 0.8, 0.85, 1.0))
            # imgui.get_style().set_color_(imgui.Col_.text,                         ImVec4(1.000, 1.000, 1.000, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.text_disabled,                ImVec4(0.500, 0.500, 0.500, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.window_bg,                    ImVec4(0.149, 0.149, 0.149, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.child_bg,                     ImVec4(0.280, 0.280, 0.280, 0.000))
            # imgui.get_style().set_color_(imgui.Col_.popup_bg,                     ImVec4(0.106, 0.106, 0.106, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.border,                       ImVec4(0.077, 0.077, 0.077, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.border_shadow,                ImVec4(0.000, 0.000, 0.000, 0.000))
            # imgui.get_style().set_color_(imgui.Col_.frame_bg,                     ImVec4(0.105, 0.105, 0.105, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.frame_bg_hovered,             ImVec4(1.000, 1.000, 1.000, 0.127)) #new System.Numerics.Vector4(0.271f, 0.251f, 0.197f, 1.000f);
            # imgui.get_style().set_color_(imgui.Col_.frame_bg_active,              ImVec4(0.280, 0.280, 0.280, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.title_bg,                     ImVec4(0.082, 0.082, 0.082, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.title_bg_active,              ImVec4(0.082, 0.082, 0.082, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.title_bg_collapsed,           ImVec4(0.082, 0.082, 0.082, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.menu_bar_bg,                  ImVec4(0.102, 0.102, 0.102, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.scrollbar_bg,                 ImVec4(0.129, 0.129, 0.129, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.scrollbar_grab,               ImVec4(0.277, 0.277, 0.277, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.scrollbar_grab_hovered,       ImVec4(0.391, 0.391, 0.391, 1.000)) # //new System.Numerics.Vector4(0.300f, 0.300f, 0.300f, 1.000f); 
            # imgui.get_style().set_color_(imgui.Col_.scrollbar_grab_active,        ImVec4(1.000, 0.391, 0.000, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.check_mark,                   ImVec4(1.000, 1.000, 1.000, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.slider_grab,                  ImVec4(0.391, 0.391, 0.391, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.slider_grab_active,           ImVec4(1.000, 0.391, 0.000, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.button,                       ImVec4(1.000, 1.000, 1.000, 0.065))
            # imgui.get_style().set_color_(imgui.Col_.button_hovered,               imgui.get_style().color_(imgui.Col_.frame_bg_hovered)) 
            # imgui.get_style().set_color_(imgui.Col_.header,                       ImVec4(0.188, 0.188, 0.188, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.header_hovered,               imgui.get_style().color_(imgui.Col_.frame_bg_hovered)) 
            # imgui.get_style().set_color_(imgui.Col_.header_active,                ImVec4(0.469, 0.469, 0.469, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.separator,                    ImVec4(0.129, 0.129, 0.129, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.separator_hovered,            imgui.get_style().color_(imgui.Col_.scrollbar_grab_hovered))
            # imgui.get_style().set_color_(imgui.Col_.separator_active,             ImVec4(1.000, 0.391, 0.000, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.resize_grip,                  ImVec4(1.000, 1.000, 1.000, 0.250))
            # imgui.get_style().set_color_(imgui.Col_.resize_grip_hovered,          imgui.get_style().color_(imgui.Col_.scrollbar_grab_hovered)) 
            # imgui.get_style().set_color_(imgui.Col_.resize_grip_active,           ImVec4(1.000, 0.391, 0.000, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.tab,                          ImVec4(0.098, 0.098, 0.098, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.tab_hovered,                  imgui.get_style().color_(imgui.Col_.frame_bg_hovered))
            # imgui.get_style().set_color_(imgui.Col_.tab_dimmed,                   imgui.get_style().color_(imgui.Col_.tab_dimmed_selected_overline)) 
            # imgui.get_style().set_color_(imgui.Col_.tab_dimmed_selected,          ImVec4(0.149, 0.149, 0.149, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.tab_dimmed_selected_overline, ImVec4(0.195, 0.195, 0.195, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.tab_selected,                 ImVec4(0.149, 0.149, 0.149, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.tab_selected_overline,        ImVec4(0.949, 0.149, 0.149, 0.300))
            # imgui.get_style().set_color_(imgui.Col_.docking_preview,              ImVec4(1.000, 0.391, 0.000, 0.781))
            # imgui.get_style().set_color_(imgui.Col_.docking_empty_bg,             ImVec4(0.180, 0.180, 0.180, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.plot_lines,                   ImVec4(0.469, 0.469, 0.469, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.plot_lines_hovered,           ImVec4(1.000, 0.391, 0.000, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.plot_histogram,               ImVec4(0.586, 0.586, 0.586, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.plot_histogram_hovered,       ImVec4(1.000, 0.391, 0.000, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.text_selected_bg,             ImVec4(1.000, 1.000, 1.000, 0.156))
            # imgui.get_style().set_color_(imgui.Col_.drag_drop_target,             ImVec4(1.000, 0.391, 0.000, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.nav_windowing_highlight,      ImVec4(1.000, 0.391, 0.000, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.nav_windowing_highlight,      ImVec4(1.000, 0.391, 0.000, 1.000))
            # imgui.get_style().set_color_(imgui.Col_.nav_windowing_dim_bg,         ImVec4(0.000, 0.000, 0.000, 0.586))
            # imgui.get_style().set_color_(imgui.Col_.modal_window_dim_bg,          ImVec4(0.000, 0.000, 0.000, 0.586))
        
        runner_params.callbacks.setup_imgui_style = setup_theme
        
        runner_params.callbacks.post_init = self._post_init
        
        # Add a frame callback to update tasks
        def before_imgui_render():
            self._update_tasks()
            self.progress_overlay.render()
            
        runner_params.callbacks.before_imgui_render = before_imgui_render

        # Docking layout
        main_split = hello_imgui.DockingSplit("MainDockSpace", "ControlsSpace", imgui.Dir.right, 0.2)
        controls_split = hello_imgui.DockingSplit("ControlsSpace", "LogSpace", imgui.Dir.down, 0.6)
        log_split = hello_imgui.DockingSplit("LogSpace", "InfoSpace", imgui.Dir.down, 0.5)

        runner_params.docking_params.docking_splits = [main_split, controls_split, log_split]
        runner_params.docking_params.dockable_windows = [
            hello_imgui.DockableWindow("Viewport", "MainDockSpace", self._render_viewport, can_be_closed_=False),
            hello_imgui.DockableWindow("Controls", "ControlsSpace", self._render_controls_panel, can_be_closed_=False),
            hello_imgui.DockableWindow("Info", "InfoSpace", self._render_info_panel, can_be_closed_=False),
            hello_imgui.DockableWindow("Log", "LogSpace", hello_imgui.log_gui, can_be_closed_=False),
        ]
        
        hello_imgui.run(runner_params)