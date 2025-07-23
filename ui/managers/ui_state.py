"""
UI State Manager for the Mesh Viewer application.

This module provides centralized state management for the UI, reducing coupling
between components and providing a single source of truth for UI state.
"""

from typing import Dict, Any, Set, List, Optional
from dataclasses import dataclass, field
from utils.logging import get_logger


@dataclass
class ViewOptions:
    """Container for view-related options."""
    wireframe: bool = False
    show_axes: bool = True
    

@dataclass
class UIState:
    """Container for all UI state information."""
    view_options: ViewOptions = field(default_factory=ViewOptions)
    loaded_mesh_paths: Set[str] = field(default_factory=set)
    viewport_size: tuple = (800, 600)
    last_mouse_pos: tuple = (0, 0)


class UIStateManager:
    """
    Centralized manager for UI state across all components.
    
    This class provides a single source of truth for UI state, reducing
    coupling between components and making state management more predictable.
    """
    
    def __init__(self):
        """Initialize the UI state manager."""
        self.logger = get_logger("ui.state_manager")
        self._state = UIState()
        self._observers: Dict[str, List[callable]] = {}
        
    @property
    def view_options(self) -> Dict[str, Any]:
        """Get view options as a dictionary for backward compatibility."""
        return {
            'wireframe': self._state.view_options.wireframe,
            'show_axes': self._state.view_options.show_axes
        }
        
    @view_options.setter
    def view_options(self, options: Dict[str, Any]) -> None:
        """Set view options from a dictionary."""
        old_options = self.view_options.copy()
        
        if 'wireframe' in options:
            self._state.view_options.wireframe = options['wireframe']
        if 'show_axes' in options:
            self._state.view_options.show_axes = options['show_axes']
            
        # Notify observers if options changed
        if old_options != self.view_options:
            self._notify_observers('view_options', old_options, self.view_options)
            self.logger.debug(f"View options updated: {self.view_options}")
            
    def set_wireframe(self, enabled: bool) -> None:
        """
        Set wireframe rendering mode.
        
        Args:
            enabled: Whether to enable wireframe mode
        """
        if self._state.view_options.wireframe != enabled:
            old_value = self._state.view_options.wireframe
            self._state.view_options.wireframe = enabled
            self._notify_observers('wireframe', old_value, enabled)
            self.logger.debug(f"Wireframe mode: {enabled}")
            
    def set_show_axes(self, enabled: bool) -> None:
        """
        Set axes display mode.
        
        Args:
            enabled: Whether to show coordinate axes
        """
        if self._state.view_options.show_axes != enabled:
            old_value = self._state.view_options.show_axes
            self._state.view_options.show_axes = enabled
            self._notify_observers('show_axes', old_value, enabled)
            self.logger.debug(f"Show axes: {enabled}")
            
    @property
    def loaded_mesh_paths(self) -> Set[str]:
        """Get the set of loaded mesh file paths."""
        return self._state.loaded_mesh_paths
        
    def add_mesh_path(self, path: str) -> None:
        """
        Add a mesh file path to the loaded set.
        
        Args:
            path: The file path of the loaded mesh
        """
        if path not in self._state.loaded_mesh_paths:
            self._state.loaded_mesh_paths.add(path)
            self._notify_observers('mesh_added', None, path)
            self.logger.debug(f"Added mesh path: {path}")
            
    def remove_mesh_path(self, path: str) -> None:
        """
        Remove a mesh file path from the loaded set.
        
        Args:
            path: The file path to remove
        """
        if path in self._state.loaded_mesh_paths:
            self._state.loaded_mesh_paths.remove(path)
            self._notify_observers('mesh_removed', path, None)
            self.logger.debug(f"Removed mesh path: {path}")
            
    def clear_mesh_paths(self) -> None:
        """Clear all loaded mesh paths."""
        if self._state.loaded_mesh_paths:
            old_paths = self._state.loaded_mesh_paths.copy()
            self._state.loaded_mesh_paths.clear()
            self._notify_observers('meshes_cleared', old_paths, set())
            self.logger.debug("Cleared all mesh paths")
            
    @property
    def viewport_size(self) -> tuple:
        """Get the current viewport size."""
        return self._state.viewport_size
        
    @viewport_size.setter
    def viewport_size(self, size: tuple) -> None:
        """Set the viewport size."""
        if self._state.viewport_size != size:
            old_size = self._state.viewport_size
            self._state.viewport_size = size
            self._notify_observers('viewport_size', old_size, size)
            self.logger.debug(f"Viewport size changed: {size}")
            
    @property
    def last_mouse_pos(self) -> tuple:
        """Get the last recorded mouse position."""
        return self._state.last_mouse_pos
        
    @last_mouse_pos.setter
    def last_mouse_pos(self, pos: tuple) -> None:
        """Set the last mouse position."""
        self._state.last_mouse_pos = pos
        
    def register_observer(self, event_type: str, callback: callable) -> None:
        """
        Register an observer for state changes.
        
        Args:
            event_type: The type of event to observe
            callback: Function to call when the event occurs
        """
        if event_type not in self._observers:
            self._observers[event_type] = []
        self._observers[event_type].append(callback)
        self.logger.debug(f"Registered observer for {event_type}")
        
    def unregister_observer(self, event_type: str, callback: callable) -> None:
        """
        Unregister an observer for state changes.
        
        Args:
            event_type: The type of event to stop observing
            callback: The callback function to remove
        """
        if event_type in self._observers:
            if callback in self._observers[event_type]:
                self._observers[event_type].remove(callback)
                self.logger.debug(f"Unregistered observer for {event_type}")
                
    def _notify_observers(self, event_type: str, old_value: Any, new_value: Any) -> None:
        """
        Notify all observers of a state change.
        
        Args:
            event_type: The type of event that occurred
            old_value: The previous value
            new_value: The new value
        """
        if event_type in self._observers:
            for callback in self._observers[event_type]:
                try:
                    callback(event_type, old_value, new_value)
                except Exception as e:
                    self.logger.error(f"Error in observer callback for {event_type}: {e}")
                    
    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current UI state.
        
        Returns:
            Dictionary containing key state information
        """
        return {
            'view_options': self.view_options,
            'loaded_mesh_count': len(self._state.loaded_mesh_paths),
            'viewport_size': self._state.viewport_size,
            'last_mouse_pos': self._state.last_mouse_pos
        }
        
    def reset_to_defaults(self) -> None:
        """Reset UI state to default values."""
        old_state = self.get_state_summary()
        self._state = UIState()
        new_state = self.get_state_summary()
        
        self._notify_observers('state_reset', old_state, new_state)
        self.logger.info("UI state reset to defaults")