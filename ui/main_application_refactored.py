"""
Refactored Main Application for the Mesh Viewer.

This module contains the refactored MainApplication class that uses focused UI components
instead of monolithic rendering methods. This improves maintainability, testability,
and separation of concerns.
"""

import os
import time
import trimesh
from typing import Dict, Any
from imgui_bundle import hello_imgui, imgui, ImVec2
from pathlib import Path

# Core modules
from core.scene import Scene
from core.renderer import Renderer
from core.camera import ArcballCamera
from core.input_handler import InputHandler

# Utility modules
from utils.file_io import prompt_load_mesh_paths
from utils.async_task import TaskManager, TaskStatus
from utils.logging import get_logger

# UI components and managers
from ui.components import (
    MenuBarComponent, ControlsPanelComponent, 
    InfoPanelComponent, ViewportComponent
)
from ui.managers import UIStateManager, ThemeManager
from ui.progress_overlay import ProgressOverlay


class MainApplication:
    """
    Refactored main application class using focused UI components.
    
    This class orchestrates the UI components and manages the overall application
    lifecycle while delegating specific UI responsibilities to focused components.
    """
    
    def __init__(self, task_manager: TaskManager):
        """
        Initialize the main application with all components.
        
        Args:
            task_manager: Manager for background tasks
        """
        self.logger = get_logger("main_application")
        
        # Core systems
        self.scene = Scene()
        self.camera = ArcballCamera(800, 600)
        self.input_handler = InputHandler()
        self.renderer = None  # Initialized in post_init
        
        # Managers
        self.ui_state_manager = UIStateManager()
        self.theme_manager = ThemeManager()
        self.task_manager = task_manager
        self.progress_overlay = ProgressOverlay()
        
        # UI Components
        self._initialize_components()
        
        # Setup component interactions
        self._setup_component_callbacks()
        
        self.logger.info("MainApplication initialized with component architecture")
        
    def _initialize_components(self) -> None:
        """Initialize all UI components."""
        # Create components
        self.menu_bar = MenuBarComponent()
        self.controls_panel = ControlsPanelComponent(self.scene)
        self.info_panel = InfoPanelComponent(self.scene)
        self.viewport = ViewportComponent(
            None,  # Renderer will be set in post_init
            self.camera,
            self.input_handler,
            self.scene
        )
        
        self.logger.debug("UI components initialized")
        
    def _setup_component_callbacks(self) -> None:
        """Setup callback functions between components and main application."""
        # Menu bar callbacks
        self.menu_bar.set_callbacks(
            load_callback=self._load_meshes,
            clear_callback=self._clear_all_meshes,
            reset_view_callback=self.reset_view
        )
        
        # Controls panel callbacks  
        self.controls_panel.set_callbacks(
            load_callback=self._load_meshes,
            delete_callback=self._delete_selected_meshes,
            reset_callback=self.reset_view
        )
        
        # Viewport callbacks
        self.viewport.set_delete_callback(self._delete_selected_meshes)
        
        # Initial state synchronization (one-time setup)
        self._initial_sync_view_options()
        
        self.logger.debug("Component callbacks configured")
        
    def _initial_sync_view_options(self) -> None:
        """Initial synchronization of view options to all components."""
        view_options = self.ui_state_manager.view_options
        
        self.menu_bar.set_view_options(view_options)
        self.controls_panel.set_view_options(view_options)
        self.viewport.set_view_options(view_options)
        
    def _sync_view_options(self) -> None:
        """Synchronize view options between components and state manager."""
        # Get current view options from the state manager
        current_state_options = self.ui_state_manager.view_options.copy()
        
        # Get view options from components (they may have been changed by user)
        menu_options = self.menu_bar.get_view_options()
        controls_options = self.controls_panel.get_view_options()
        
        # Check if any component has different options
        if menu_options != current_state_options:
            # Update state manager with menu changes
            self.ui_state_manager.view_options = menu_options
            # Sync to other components
            self.controls_panel.set_view_options(menu_options)
            self.viewport.set_view_options(menu_options)
        elif controls_options != current_state_options:
            # Update state manager with controls changes
            self.ui_state_manager.view_options = controls_options
            # Sync to other components
            self.menu_bar.set_view_options(controls_options)
            self.viewport.set_view_options(controls_options)
        
    def _post_init(self) -> None:
        """Post-initialization callback called by hello_imgui."""
        try:
            # Initialize renderer with viewport size
            viewport_size = self.ui_state_manager.viewport_size
            self.renderer = Renderer(*viewport_size)
            
            # Update viewport component with renderer
            self.viewport.renderer = self.renderer
            
            # Setup fonts for components
            title_font = self.theme_manager.get_title_font()
            self.controls_panel.set_title_font(title_font)
            self.info_panel.set_title_font(title_font)
            
            # Reset view to initial state
            self.reset_view()
            
            self.logger.info("Post-initialization completed")
            
        except Exception as e:
            self.logger.error(f"Error in post-initialization: {e}")
            
    def _load_meshes(self) -> None:
        """Load meshes using file dialog."""
        try:
            filepaths = prompt_load_mesh_paths()
            if not filepaths:
                return
                
            # Create and start background task
            task_id = f"load_meshes_{int(time.time())}"
            task = self.task_manager.create_task(
                task_id, 
                self._load_meshes_task, 
                filepaths
            )
            task.start()
            
            # Show progress overlay
            self.progress_overlay.show(
                "Loading Meshes", 
                f"Loading {len(filepaths)} mesh(es)...", 
                0.0,
                True,
                lambda: self.task_manager.cancel_task(task_id),
                task_id
            )
            
            self.logger.info(f"Started loading {len(filepaths)} meshes")
            
        except Exception as e:
            self.logger.error(f"Error initiating mesh loading: {e}")
            
    def _load_meshes_task(self, filepaths, report_progress=None, is_canceled=None):
        """Background task for loading meshes."""
        new_mesh_loaded = False
        results = []
        
        for i, path in enumerate(filepaths):
            # Check for cancellation
            if is_canceled and is_canceled():
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
            if abs_path in self.ui_state_manager.loaded_mesh_paths:
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
        
    def _process_mesh_loading_results(self, task_id: str) -> None:
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
                        self.ui_state_manager.add_mesh_path(mesh_result["abs_path"])
                        
                except Exception as e:
                    hello_imgui.log(hello_imgui.LogLevel.error, f"Error creating mesh: {e}")
        
        # Reset view if any meshes were loaded
        if result["success"]:
            self.reset_view()
            
        # Hide the progress overlay
        self.progress_overlay.hide()
        
        # Clean up the task
        self.task_manager.remove_task(task_id)
        
    def _clear_all_meshes(self) -> None:
        """Clear all loaded meshes."""
        try:
            self.scene.clear()
            self.ui_state_manager.clear_mesh_paths()
            self.reset_view()
            hello_imgui.log(hello_imgui.LogLevel.info, "Cleared all meshes.")
            self.logger.info("All meshes cleared")
            
        except Exception as e:
            self.logger.error(f"Error clearing meshes: {e}")
            
    def _delete_selected_meshes(self) -> None:
        """Delete currently selected meshes."""
        try:
            if not self.scene.meshes:
                return
                
            selected_indices = [i for i, mesh in enumerate(self.scene.meshes) if mesh.selected]
            if not selected_indices:
                return
                
            # Remove meshes in reverse order to maintain indices
            for idx in sorted(selected_indices, reverse=True):
                mesh = self.scene.meshes[idx]
                
                # Remove from loaded paths
                for path in list(self.ui_state_manager.loaded_mesh_paths):
                    if mesh.name in path:
                        self.ui_state_manager.remove_mesh_path(path)
                        
                # Release resources and remove from scene
                mesh.release()
                del self.scene.meshes[idx]
            
            hello_imgui.log(hello_imgui.LogLevel.info, f"Deleted {len(selected_indices)} mesh(es).")
            self.logger.info(f"Deleted {len(selected_indices)} selected meshes")
            self.reset_view()
            
        except Exception as e:
            self.logger.error(f"Error deleting selected meshes: {e}")
            
    def reset_view(self) -> None:
        """Reset the camera view to fit all meshes."""
        try:
            from config import get_camera_config
            camera_config = get_camera_config()
            
            scale = self.scene.fit_to_view()
            self.camera.set_zoom(scale * camera_config.RESET_ZOOM_MULTIPLIER)
            self.scene.reset_transformations()
            
            self.logger.debug("View reset completed")
            
        except Exception as e:
            self.logger.error(f"Error resetting view: {e}")
            
    def _update_tasks(self) -> None:
        """Update all background tasks and process completed ones."""
        try:
            # Check if cancel was requested in the UI
            if self.progress_overlay.visible and self.progress_overlay.cancel_requested:
                self.progress_overlay.cancel_requested = False
                if self.progress_overlay.active_task_id and self.progress_overlay.on_cancel:
                    self.task_manager.cancel_task(self.progress_overlay.active_task_id)
            
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
                    
        except Exception as e:
            self.logger.error(f"Error updating tasks: {e}")
            
    def _before_imgui_render(self) -> None:
        """Callback called before ImGui rendering each frame."""
        try:
            self._update_tasks()
            self._sync_view_options()  # Keep view options synchronized
            self.progress_overlay.render()
            
            # Render menu bar (since show_menu_bar is True, ImGui will expect menu content)
            if imgui.begin_main_menu_bar():
                self.menu_bar.render()
                imgui.end_main_menu_bar()
            
        except Exception as e:
            self.logger.error(f"Error in before_imgui_render: {e}")
            
    def run(self) -> None:
        """Run the main application."""
        try:
            # Setup hello_imgui runner parameters
            runner_params = hello_imgui.RunnerParams()
            runner_params.app_window_params.window_title = "Mesh Viewer (Refactored)"
            runner_params.app_window_params.window_geometry.size = (1600, 900)
            
            # Docking configuration
            runner_params.docking_params.main_dock_space_node_flags |= (
                imgui.DockNodeFlags_.auto_hide_tab_bar
            )
            runner_params.imgui_window_params.default_imgui_window_type = (
                hello_imgui.DefaultImGuiWindowType.provide_full_screen_dock_space
            )
            runner_params.imgui_window_params.show_menu_bar = True
            runner_params.imgui_window_params.show_status_bar = False
            runner_params.fps_idling.enable_idling = False
            
            # Setup callbacks
            runner_params.callbacks.load_additional_fonts = self.theme_manager.create_font_callback()
            runner_params.callbacks.setup_imgui_style = self.theme_manager.create_theme_callback()
            runner_params.callbacks.post_init = self._post_init
            runner_params.callbacks.before_imgui_render = self._before_imgui_render
            
            # Docking layout
            main_split = hello_imgui.DockingSplit("MainDockSpace", "ControlsSpace", imgui.Dir.right, 0.2)
            controls_split = hello_imgui.DockingSplit("ControlsSpace", "LogSpace", imgui.Dir.down, 0.6)
            log_split = hello_imgui.DockingSplit("LogSpace", "InfoSpace", imgui.Dir.down, 0.5)

            runner_params.docking_params.docking_splits = [main_split, controls_split, log_split]
            runner_params.docking_params.dockable_windows = [
                hello_imgui.DockableWindow("Viewport", "MainDockSpace", self.viewport.render, can_be_closed_=False),
                hello_imgui.DockableWindow("Controls", "ControlsSpace", self.controls_panel.render, can_be_closed_=False),
                hello_imgui.DockableWindow("Info", "InfoSpace", self.info_panel.render, can_be_closed_=False),
                hello_imgui.DockableWindow("Log", "LogSpace", hello_imgui.log_gui, can_be_closed_=False),
            ]
            
            # Menu bar will be handled in before_imgui_render
            
            self.logger.info("Starting main application loop")
            hello_imgui.run(runner_params)
            
        except Exception as e:
            self.logger.error(f"Error running application: {e}")
            raise
