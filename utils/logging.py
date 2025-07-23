"""
Logging utilities for the Mesh Viewer application.
Provides structured logging with different levels and formatters.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels for console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        # Get the original formatted message
        message = super().format(record)
        
        # Add color if outputting to terminal
        if hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            level_color = self.COLORS.get(record.levelname, '')
            reset_color = self.COLORS['RESET']
            return f"{level_color}{message}{reset_color}"
        
        return message


class MeshViewerLogger:
    """
    Centralized logging configuration for the Mesh Viewer application.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._setup_logging()
            MeshViewerLogger._initialized = True
    
    def _setup_logging(self):
        """Configure logging for the application."""
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Configure root logger
        self.logger = logging.getLogger("mesh_viewer")
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers
        if self.logger.handlers:
            return
        
        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        console_format = ColoredFormatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        
        # File handler for all logs
        log_file = log_dir / f"mesh_viewer_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        file_format = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        
        # Error file handler for warnings and errors only
        error_file = log_dir / f"mesh_viewer_errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = logging.FileHandler(error_file, encoding='utf-8')
        error_handler.setLevel(logging.WARNING)
        error_handler.setFormatter(file_format)
        
        # Add handlers to logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        
        # Log startup message
        self.logger.info("Mesh Viewer logging system initialized")
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance for a specific module."""
        return logging.getLogger(f"mesh_viewer.{name}")
    
    def set_level(self, level: str):
        """Set the logging level for console output."""
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        if level.upper() in level_map:
            # Only change console handler level
            for handler in self.logger.handlers:
                if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                    handler.setLevel(level_map[level.upper()])
                    self.logger.info(f"Console logging level set to {level.upper()}")
                    break


# Global logger instance
_logger_manager = MeshViewerLogger()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: The name of the module (e.g., 'renderer', 'mesh', 'ui')
        
    Returns:
        A configured logger instance
    """
    return _logger_manager.get_logger(name)


def set_log_level(level: str):
    """
    Set the console logging level.
    
    Args:
        level: Log level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    """
    _logger_manager.set_level(level)


def log_performance(func):
    """
    Decorator to log function performance.
    
    Usage:
        @log_performance
        def slow_function():
            pass
    """
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger('performance')
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.debug(f"{func.__name__} completed in {elapsed:.4f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"{func.__name__} failed after {elapsed:.4f}s: {e}")
            raise
    
    return wrapper


def log_exceptions(func):
    """
    Decorator to automatically log exceptions.
    
    Usage:
        @log_exceptions
        def risky_function():
            pass
    """
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger('exceptions')
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Exception in {func.__name__}: {e}")
            raise
    
    return wrapper


# Convenience functions for common logging operations
def log_mesh_load(mesh_name: str, vertex_count: int, face_count: int, load_time: float):
    """Log mesh loading information."""
    logger = get_logger('mesh')
    logger.info(f"Loaded mesh '{mesh_name}': {vertex_count:,} vertices, {face_count:,} faces in {load_time:.3f}s")


def log_render_stats(fps: float, frame_time: float, mesh_count: int):
    """Log rendering performance statistics."""
    logger = get_logger('render')
    logger.debug(f"FPS: {fps:.1f}, Frame time: {frame_time:.3f}ms, Meshes: {mesh_count}")


def log_user_action(action: str, details: str = ""):
    """Log user interactions."""
    logger = get_logger('user')
    if details:
        logger.info(f"User action: {action} - {details}")
    else:
        logger.info(f"User action: {action}")


def log_config_change(setting: str, old_value, new_value):
    """Log configuration changes."""
    logger = get_logger('config')
    logger.info(f"Config changed: {setting} from {old_value} to {new_value}")


def log_error_with_context(error: Exception, context: str, **kwargs):
    """Log an error with additional context information."""
    logger = get_logger('error')
    context_info = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    if context_info:
        logger.error(f"Error in {context}: {error} (Context: {context_info})")
    else:
        logger.error(f"Error in {context}: {error}")


# Example usage logging functions for different modules
class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = get_logger(self.__class__.__name__.lower())
    
    def log_debug(self, message: str):
        self._logger.debug(message)
    
    def log_info(self, message: str):
        self._logger.info(message)
    
    def log_warning(self, message: str):
        self._logger.warning(message)
    
    def log_error(self, message: str):
        self._logger.error(message)
    
    def log_exception(self, message: str):
        self._logger.exception(message)


# Initialize logging on import
_logger_manager = MeshViewerLogger()