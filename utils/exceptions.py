"""
Custom exception classes and error handling utilities for the Mesh Viewer application.
"""

from typing import Optional, Any, Dict
from utils.logging import get_logger


class MeshViewerError(Exception):
    """Base exception class for all Mesh Viewer related errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}
        
        # Log the error
        logger = get_logger('exceptions')
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            logger.error(f"{self.__class__.__name__}: {message} (Context: {context_str})")
        else:
            logger.error(f"{self.__class__.__name__}: {message}")


class RenderingError(MeshViewerError):
    """Raised when rendering operations fail."""
    pass


class MeshError(MeshViewerError):
    """Raised when mesh operations fail."""
    pass


class ShaderError(RenderingError):
    """Raised when shader compilation or loading fails."""
    pass


class CameraError(MeshViewerError):
    """Raised when camera operations fail."""
    pass


class FileError(MeshViewerError):
    """Raised when file operations fail."""
    pass


class ConfigurationError(MeshViewerError):
    """Raised when configuration is invalid."""
    pass


class ValidationError(MeshViewerError):
    """Raised when data validation fails."""
    pass


def handle_error(error: Exception, context: str = "", fallback_action=None, **kwargs):
    """
    Centralized error handling utility.
    
    Args:
        error: The exception that occurred
        context: Description of where the error occurred
        fallback_action: Optional function to call for recovery
        **kwargs: Additional context information
    """
    logger = get_logger('error_handler')
    
    # Create context info
    context_info = {"context": context}
    context_info.update(kwargs)
    
    # Log the error with context
    if isinstance(error, MeshViewerError):
        # Already logged by the exception itself
        pass
    else:
        context_str = ", ".join(f"{k}={v}" for k, v in context_info.items())
        logger.error(f"Unhandled error in {context}: {error} (Context: {context_str})")
    
    # Try fallback action if provided
    if fallback_action:
        try:
            logger.info(f"Attempting fallback action for error in {context}")
            return fallback_action()
        except Exception as fallback_error:
            logger.error(f"Fallback action failed in {context}: {fallback_error}")
    
    # Re-raise the original error
    raise error


def safe_execute(func, fallback_value=None, context: str = "", **kwargs):
    """
    Safely execute a function with error handling.
    
    Args:
        func: Function to execute
        fallback_value: Value to return if function fails
        context: Description for error logging
        **kwargs: Additional context for error logging
        
    Returns:
        Function result or fallback_value if function fails
    """
    try:
        return func()
    except Exception as e:
        logger = get_logger('safe_execute')
        context_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        logger.warning(f"Safe execute failed in {context}: {e} (Context: {context_str}, using fallback)")
        return fallback_value


def validate_numeric_range(value: float, min_val: float, max_val: float, name: str):
    """Validate that a numeric value is within acceptable range."""
    if not (min_val <= value <= max_val):
        raise ValidationError(
            f"{name} value {value} is outside valid range [{min_val}, {max_val}]",
            context={"value": value, "min": min_val, "max": max_val, "parameter": name}
        )


def validate_not_none(value: Any, name: str):
    """Validate that a value is not None."""
    if value is None:
        raise ValidationError(f"{name} cannot be None", context={"parameter": name})


def validate_positive(value: float, name: str):
    """Validate that a numeric value is positive."""
    if value <= 0:
        raise ValidationError(
            f"{name} must be positive, got {value}",
            context={"value": value, "parameter": name}
        )


def validate_file_exists(file_path: str):
    """Validate that a file exists and is readable."""
    from pathlib import Path
    
    path = Path(file_path)
    if not path.exists():
        raise FileError(f"File does not exist: {file_path}", context={"path": file_path})
    
    if not path.is_file():
        raise FileError(f"Path is not a file: {file_path}", context={"path": file_path})
    
    try:
        with open(path, 'r') as f:
            pass
    except PermissionError:
        raise FileError(f"File is not readable: {file_path}", context={"path": file_path})


def create_error_context(**kwargs) -> Dict[str, Any]:
    """Create a standardized error context dictionary."""
    return {k: v for k, v in kwargs.items() if v is not None}


class ErrorRecovery:
    """Helper class for implementing error recovery strategies."""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 1.0):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.logger = get_logger('error_recovery')
    
    def retry_on_failure(self, func, *args, **kwargs):
        """Retry a function call with exponential backoff."""
        import time
        
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                
                if attempt < self.max_retries:
                    delay = self.backoff_factor * (2 ** attempt)
                    self.logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    time.sleep(delay)
                else:
                    self.logger.error(f"All {self.max_retries + 1} attempts failed")
        
        # If we get here, all retries failed
        raise last_error


# Global error recovery instance
error_recovery = ErrorRecovery()


# Decorator for automatic error handling
def with_error_handling(context: str = "", fallback_value=None):
    """
    Decorator to add automatic error handling to functions.
    
    Usage:
        @with_error_handling("loading mesh", fallback_value=None)
        def load_mesh(path):
            ...
    """
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handle_error(e, context or func.__name__, lambda: fallback_value)
        
        return wrapper
    return decorator


# Decorator for retry logic
def with_retry(max_retries: int = 3, backoff_factor: float = 1.0):
    """
    Decorator to add retry logic to functions.
    
    Usage:
        @with_retry(max_retries=3)
        def unreliable_function():
            ...
    """
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            recovery = ErrorRecovery(max_retries, backoff_factor)
            return recovery.retry_on_failure(func, *args, **kwargs)
        
        return wrapper
    return decorator