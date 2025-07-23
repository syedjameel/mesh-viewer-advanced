"""
Base UI Component class for the Mesh Viewer application.

This module provides the abstract base class that all UI components inherit from,
ensuring consistent interface and behavior across all components.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from utils.logging import get_logger


class BaseUIComponent(ABC):
    """
    Abstract base class for all UI components.
    
    Provides common functionality and ensures consistent interface
    across all UI components in the mesh viewer application.
    """
    
    def __init__(self, name: str):
        """
        Initialize the base UI component.
        
        Args:
            name: The name of the component for logging and identification
        """
        self.name = name
        self.logger = get_logger(f"ui.{name.lower()}")
        self._enabled = True
        
    @property
    def enabled(self) -> bool:
        """Whether this component is enabled for rendering."""
        return self._enabled
        
    @enabled.setter
    def enabled(self, value: bool):
        """Enable or disable this component."""
        self._enabled = value
        
    @abstractmethod
    def render(self) -> None:
        """
        Render the UI component.
        
        This method must be implemented by all concrete UI components
        to define their rendering behavior.
        """
        pass
        
    def setup(self) -> None:
        """
        Perform any setup required for this component.
        
        Called once during initialization. Override in subclasses
        if setup is needed.
        """
        pass
        
    def cleanup(self) -> None:
        """
        Perform any cleanup required for this component.
        
        Called when the component is being destroyed. Override in
        subclasses if cleanup is needed.
        """
        pass
        
    def handle_error(self, error: Exception, context: str = "") -> None:
        """
        Handle errors that occur within the component.
        
        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
        """
        error_msg = f"Error in {self.name} component"
        if context:
            error_msg += f" ({context})"
        error_msg += f": {error}"
        
        self.logger.error(error_msg, exc_info=True)