import os
import time
import trimesh
from imgui_bundle import hello_imgui, imgui, ImVec2, ImVec4, icons_fontawesome_6, imgui_md, immapp
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
        self.font_title = None
        self.font_large = None
        self.task_manager = task_manager
        self.progress_overlay = ProgressOverlay()
        self.accent_color = ImVec4(0.26, 0.59, 0.98, 1.0)  # Modern blue accent

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
            if imgui.menu_item(f"{icons_fontawesome_6.ICON_FA_FOLDER_OPEN} Load Mesh...", "Ctrl+O")[0]: 
                self._load_meshes()
            if imgui.menu_item(f"{icons_fontawesome_6.ICON_FA_TRASH} Clear All Meshes")[0]:
                self.scene.clear()
                self.loaded_mesh_paths.clear()
                self.reset_view()
                hello_imgui.log(hello_imgui.LogLevel.info, "Cleared all meshes.")
            imgui.separator()
            if imgui.menu_item(f"{icons_fontawesome_6.ICON_FA_DOOR_OPEN} Exit")[0]: 
                hello_imgui.get_runner_params().app_shall_exit = True
            imgui.end_menu()
        
        if imgui.begin_menu("View"):
            _, self.view_options['wireframe'] = imgui.menu_item("Wireframe", "", self.view_options['wireframe'])
            _, self.view_options['show_axes'] = imgui.menu_item("Show Axes", "", self.view_options['show_axes'])
            if imgui.menu_item(f"{icons_fontawesome_6.ICON_FA_ARROWS_ROTATE} Reset View")[0]: 
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
        # Header with gradient background
        imgui.push_style_color(imgui.Col_.header, ImVec4(0.12, 0.12, 0.14, 1.0))
        imgui.push_style_color(imgui.Col_.header_hovered, ImVec4(0.14, 0.14, 0.16, 1.0))
        imgui.push_style_color(imgui.Col_.header_active, ImVec4(0.16, 0.16, 0.18, 1.0))
        
        if self.font_title:
            imgui.push_font(self.font_title)
        imgui.text(f"{icons_fontawesome_6.ICON_FA_SLIDERS} Controls")
        if self.font_title:
            imgui.pop_font()
            
        imgui.pop_style_color(3)
        imgui.separator()

        # Action buttons with icons
        imgui.begin_group()
        button_size = ImVec2(-1, 0)
        
        if imgui.button(f"{icons_fontawesome_6.ICON_FA_FOLDER_OPEN} Load Mesh...", button_size): 
            self._load_meshes()
        
        if imgui.button(f"{icons_fontawesome_6.ICON_FA_TRASH} Delete Selected", button_size) and any(mesh.selected for mesh in self.scene.meshes): 
            self._delete_selected_meshes()
            
        if imgui.button(f"{icons_fontawesome_6.ICON_FA_ARROWS_ROTATE} Reset View", button_size): 
            self.reset_view()
        imgui.end_group()

        imgui.spacing()
        imgui.spacing()

        # View options with toggle switches
        if self.font_title:
            imgui.push_font(self.font_title)
        imgui.text(f"{icons_fontawesome_6.ICON_FA_EYE} View Options")
        if self.font_title:
            imgui.pop_font()
            
        imgui.separator()
        imgui.begin_group()
        _, self.view_options['wireframe'] = imgui.checkbox("Wireframe", self.view_options['wireframe'])
        _, self.view_options['show_axes'] = imgui.checkbox("Show Axes", self.view_options['show_axes'])
        imgui.end_group()

        imgui.spacing()
        imgui.spacing()

        # Meshes list with custom styling
        if self.font_title:
            imgui.push_font(self.font_title)
        imgui.text(f"{icons_fontawesome_6.ICON_FA_LIST} Meshes")
        if self.font_title:
            imgui.pop_font()
            
        imgui.separator()
            
        if not self.scene.meshes:
            imgui.text_disabled("No meshes loaded")
        else:
            for i, mesh in enumerate(self.scene.meshes):
                imgui.push_id(f"mesh_{i}")
                
                # Row background with hover effect
                if imgui.is_item_hovered():
                    imgui.push_style_color(imgui.Col_.header, ImVec4(0.18, 0.18, 0.22, 1.0))
                else:
                    imgui.push_style_color(imgui.Col_.header, ImVec4(0.14, 0.14, 0.16, 1.0))
                    
                imgui.selectable(f"##mesh_row_{i}", False, 
                                 imgui.SelectableFlags_.span_all_columns | imgui.SelectableFlags_.allow_overlap,
                                 ImVec2(0, imgui.get_frame_height()))
                
                # Visibility toggle
                imgui.same_line(imgui.get_window_width() - immapp.em_size(8.0))
                _, mesh.visible = imgui.checkbox(f"##vis_{i}", mesh.visible)
                
                # Selection highlight
                imgui.same_line()
                if mesh.selected:
                    imgui.push_style_color(imgui.Col_.text, self.accent_color)
                
                # Mesh name with icon
                imgui.same_line(immapp.em_size(3.0))
                imgui.text(f"{icons_fontawesome_6.ICON_FA_CUBE} {mesh.name}")
                
                if mesh.selected:
                    imgui.pop_style_color()
                
                imgui.pop_style_color()
                imgui.pop_id()

    def _render_info_panel(self):
        # Header with gradient background
        imgui.push_style_color(imgui.Col_.header, ImVec4(0.12, 0.12, 0.14, 1.0))
        imgui.push_style_color(imgui.Col_.header_hovered, ImVec4(0.14, 0.14, 0.16, 1.0))
        imgui.push_style_color(imgui.Col_.header_active, ImVec4(0.16, 0.16, 0.18, 1.0))
        
        if self.font_title:
            imgui.push_font(self.font_title)
        imgui.text(f"{icons_fontawesome_6.ICON_FA_CIRCLE_INFO} Mesh Info")
        if self.font_title:
            imgui.pop_font()
            
        imgui.pop_style_color(3)
        imgui.separator()
        
        selected_meshes = [m for m in self.scene.meshes if m.selected]
        if not selected_meshes:
            imgui.text_disabled("Select a mesh to view details")
        else:
            for mesh in selected_meshes:
                flags = imgui.TreeNodeFlags_.default_open | imgui.TreeNodeFlags_.framed
                if imgui.tree_node_ex(f"{mesh.name}", flags):
                    imgui.begin_table("mesh_info", 2, 
                                     imgui.TableFlags_.borders_inner_v | imgui.TableFlags_.sizing_fixed_fit)
                    
                    imgui.table_next_row()
                    imgui.table_set_column_index(0)
                    imgui.text_disabled("Vertices:")
                    imgui.table_set_column_index(1)
                    imgui.text(f"{len(mesh.trimesh_mesh.vertices):,}")
                    
                    imgui.table_next_row()
                    imgui.table_set_column_index(0)
                    imgui.text_disabled("Faces:")
                    imgui.table_set_column_index(1)
                    imgui.text(f"{len(mesh.trimesh_mesh.faces):,}")
                    
                    imgui.table_next_row()
                    imgui.table_set_column_index(0)
                    imgui.text_disabled("Dimensions:")
                    imgui.table_set_column_index(1)
                    dims = mesh.trimesh_mesh.extents
                    imgui.text(f"{dims[0]:.2f} x {dims[1]:.2f} x {dims[2]:.2f}")
                    
                    imgui.table_next_row()
                    imgui.table_set_column_index(0)
                    imgui.text_disabled("Volume:")
                    imgui.table_set_column_index(1)
                    imgui.text(f"{mesh.trimesh_mesh.volume:.2f}")
                    
                    imgui.end_table()
                    imgui.tree_pop()
                    
    def _render_viewport(self):
        # Add border around viewport
        imgui.push_style_color(imgui.Col_.border, ImVec4(0.3, 0.3, 0.35, 1.0))
        imgui.push_style_var(imgui.StyleVar_.child_border_size, 1.0)
        imgui.push_style_var(imgui.StyleVar_.child_rounding, 6.0)
        
        imgui.begin_child("ViewportChild", imgui.get_content_region_avail(),
                          window_flags=imgui.WindowFlags_.no_move | imgui.WindowFlags_.no_scrollbar)
        
        size = imgui.get_content_region_avail()
        width, height = max(1, int(size.x)), max(1, int(size.y))

        if (width, height) != self.viewport_size:
            self.viewport_size = (width, height)
            self.renderer.resize(width, height)
            self.camera.set_viewport(width, height)

        self.renderer.render(self.scene, self.camera, self.view_options)
        
        # Render to ImGui image with subtle shadow
        draw_list = imgui.get_window_draw_list()
        rect_min = imgui.get_item_rect_min()
        rect_max = imgui.get_item_rect_max()

        # Simulate shadow by drawing a slightly offset darker rect behind
        shadow_offset = ImVec2(4, 4)
        draw_list.add_rect_filled(
            ImVec2(rect_min.x + shadow_offset.x, rect_min.y + shadow_offset.y),
            ImVec2(rect_max.x + shadow_offset.x, rect_max.y + shadow_offset.y),
            imgui.get_color_u32(ImVec4(0, 0, 0, 0.3))
        )
        
        imgui.image(self.renderer.texture.glo, ImVec2(*self.viewport_size), ImVec2(0, 1), ImVec2(1, 0))

        
        # Input handling (unchanged)
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
        
        imgui.end_child()
        imgui.pop_style_var(2)
        imgui.pop_style_color()

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
        runner_params.app_window_params.window_title = "Modern Mesh Viewer"
        runner_params.app_window_params.window_geometry.size = (1600, 900)
        runner_params.app_window_params.borderless = True
        runner_params.app_window_params.borderless_movable = True
        runner_params.app_window_params.borderless_resizable = True

        runner_params.docking_params.main_dock_space_node_flags |= (
            imgui.DockNodeFlags_.auto_hide_tab_bar
        )
        
        runner_params.imgui_window_params.default_imgui_window_type = hello_imgui.DefaultImGuiWindowType.provide_full_screen_dock_space
        runner_params.imgui_window_params.show_menu_bar = True
        runner_params.imgui_window_params.show_status_bar = True
        runner_params.fps_idling.enable_idling = False
        
        # Font loading
        def load_fonts():
            hello_imgui.imgui_default_settings.load_default_font_with_font_awesome_icons()
            
            # Load modern fonts
            font_loading_params = hello_imgui.FontLoadingParams()
            font_loading_params.merge_font_awesome = True
            
            # Title font (Roboto Bold)
            self.font_title = hello_imgui.load_font("fonts/Roboto/Roboto-Bold.ttf", 20.0, font_loading_params)
            
            # Large font for icons and headers
            self.font_large = hello_imgui.load_font("fonts/fontawesome-webfont.ttf", 18.0, font_loading_params)
        
        runner_params.callbacks.load_additional_fonts = load_fonts
        
        # Modern theme setup
        def setup_modern_theme():
            style = imgui.get_style()
            colors = imgui.get_style().color_
            
            # Global style settings
            style.window_padding = ImVec2(10, 10)
            style.frame_padding = ImVec2(8, 6)
            style.item_spacing = ImVec2(8, 6)
            style.item_inner_spacing = ImVec2(6, 4)
            style.window_rounding = 10.0
            style.frame_rounding = 6.0
            style.scrollbar_rounding = 6.0
            style.grab_rounding = 6.0
            style.tab_rounding = 6.0
            
            # Modern dark color palette

            style.set_color_(imgui.Col_.window_bg, imgui.ImVec4(0.09, 0.09, 0.11, 1.00))
            style.set_color_(imgui.Col_.child_bg, imgui.ImVec4(0.10, 0.10, 0.12, 1.00))
            style.set_color_(imgui.Col_.frame_bg, imgui.ImVec4(0.15, 0.15, 0.18, 1.00))
            style.set_color_(imgui.Col_.frame_bg_hovered, imgui.ImVec4(0.20, 0.20, 0.25, 1.00))
            style.set_color_(imgui.Col_.frame_bg_active, imgui.ImVec4(0.25, 0.25, 0.30, 1.00))
            style.set_color_(imgui.Col_.title_bg, imgui.ImVec4(0.08, 0.08, 0.10, 1.00))
            style.set_color_(imgui.Col_.title_bg_active, imgui.ImVec4(0.10, 0.10, 0.12, 1.00))
            style.set_color_(imgui.Col_.check_mark, self.accent_color)
            style.set_color_(imgui.Col_.slider_grab, self.accent_color)
            style.set_color_(imgui.Col_.slider_grab_active, imgui.ImVec4(0.35, 0.68, 1.00, 1.00))
            style.set_color_(imgui.Col_.button, imgui.ImVec4(0.18, 0.18, 0.22, 1.00))
            style.set_color_(imgui.Col_.button_hovered, imgui.ImVec4(0.22, 0.22, 0.27, 1.00))
            style.set_color_(imgui.Col_.button_active, imgui.ImVec4(0.25, 0.25, 0.30, 1.00))
            style.set_color_(imgui.Col_.header, imgui.ImVec4(0.20, 0.20, 0.25, 1.00))
            style.set_color_(imgui.Col_.header_hovered, imgui.ImVec4(0.25, 0.25, 0.30, 1.00))
            style.set_color_(imgui.Col_.header_active, imgui.ImVec4(0.30, 0.30, 0.35, 1.00))
            style.set_color_(imgui.Col_.separator, imgui.ImVec4(0.30, 0.30, 0.35, 1.00))
            style.set_color_(imgui.Col_.separator_hovered, imgui.ImVec4(0.35, 0.35, 0.40, 1.00))
            style.set_color_(imgui.Col_.separator_active, imgui.ImVec4(0.40, 0.40, 0.45, 1.00))
            style.set_color_(imgui.Col_.text_selected_bg, imgui.ImVec4(0.26, 0.59, 0.98, 0.35))

            style.set_color_(imgui.Col_.resize_grip, ImVec4(0.26, 0.59, 0.98, 0.25))
            style.set_color_(imgui.Col_.resize_grip_hovered, ImVec4(0.26, 0.59, 0.98, 0.67))
            style.set_color_(imgui.Col_.resize_grip_active, self.accent_color)
            style.set_color_(imgui.Col_.tab, ImVec4(0.15, 0.15, 0.18, 1.00))
            style.set_color_(imgui.Col_.tab_hovered, ImVec4(0.20, 0.20, 0.25, 1.00))
            style.set_color_(imgui.Col_.tab_selected, ImVec4(0.18, 0.18, 0.22, 1.00))
            style.set_color_(imgui.Col_.tab_dimmed_selected, ImVec4(0.15, 0.15, 0.18, 1.00))
            style.set_color_(imgui.Col_.tab_dimmed_selected, ImVec4(0.18, 0.18, 0.22, 1.00))
            style.set_color_(imgui.Col_.nav_cursor, self.accent_color)
            style.set_color_(imgui.Col_.nav_windowing_highlight, ImVec4(1.00, 1.00, 1.00, 0.70))
            style.set_color_(imgui.Col_.modal_window_dim_bg, ImVec4(0.00, 0.00, 0.00, 0.60))

            
            # Apply subtle shadow to windows
            style.window_rounding = 10.0
            style.window_padding = ImVec2(0, 3)
        
        runner_params.callbacks.setup_imgui_style = setup_modern_theme
        
        runner_params.callbacks.post_init = self._post_init
        
        # Add frame callback to update tasks
        def before_imgui_render():
            self._update_tasks()
            self.progress_overlay.render()
            
        runner_params.callbacks.before_imgui_render = before_imgui_render

        # Enhanced docking layout
        main_split = hello_imgui.DockingSplit("MainDockSpace", "ControlsSpace", imgui.Dir.right, 0.22)
        controls_split = hello_imgui.DockingSplit("ControlsSpace", "InfoSpace", imgui.Dir.down, 0.5)
        info_split = hello_imgui.DockingSplit("InfoSpace", "LogSpace", imgui.Dir.down, 0.4)

        runner_params.docking_params.docking_splits = [main_split, controls_split, info_split]
        runner_params.docking_params.dockable_windows = [
            hello_imgui.DockableWindow("Viewport", "MainDockSpace", self._render_viewport, 
                                       can_be_closed_=False),
            hello_imgui.DockableWindow("Controls", "ControlsSpace", self._render_controls_panel, 
                                       can_be_closed_=False),
            hello_imgui.DockableWindow("Mesh Info", "InfoSpace", self._render_info_panel, 
                                       can_be_closed_=False),
            hello_imgui.DockableWindow("Console", "LogSpace", hello_imgui.log_gui, 
                                       can_be_closed_=False),
        ]
        
        # Add status bar callback
        def status_bar():
            imgui.text(f"{icons_fontawesome_6.ICON_FA_CUBE} {len(self.scene.meshes)} meshes")
            imgui.same_line()
            imgui.text(f"{icons_fontawesome_6.ICON_FA_EYE} {sum(m.visible for m in self.scene.meshes)} visible")
            imgui.same_line()
            imgui.text(f"{icons_fontawesome_6.ICON_FA_DIAMOND} {sum(m.selected for m in self.scene.meshes)} selected")
            
        runner_params.callbacks.show_status = status_bar
        
        hello_imgui.run(runner_params)