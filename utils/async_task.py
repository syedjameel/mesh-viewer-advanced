import threading
import time
import queue
from typing import Callable, Any, Dict, Optional, List, Tuple
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import weakref
from config import get_threading_config

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

class AsyncTask:
    """
    A class for executing functions asynchronously with progress reporting.
    """
    def __init__(self, task_id: str, func: Callable, args: tuple = (), kwargs: dict = None):
        """
        Initialize an async task.
        
        Args:
            task_id: Unique identifier for the task
            func: The function to execute asynchronously
            args: Positional arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
        """
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.status = TaskStatus.PENDING
        self.progress = 0.0
        self.result = None
        self.error = None
        self.thread = None
        self._future = None
        self._progress_queue = queue.Queue()
        self._result_queue = queue.Queue()
        self._cancel_event = threading.Event()
        
    def start(self):
        """Start the task in a background thread."""
        if self.status == TaskStatus.RUNNING:
            return
            
        self.status = TaskStatus.RUNNING
        self.progress = 0.0
        self.result = None
        self.error = None
        
        # Add progress reporting capability to kwargs
        self.kwargs['report_progress'] = self._report_progress
        self.kwargs['is_canceled'] = self._is_canceled
        
        self.thread = threading.Thread(target=self._run_task)
        self.thread.daemon = True
        self.thread.start()

    def start_with_executor(self, executor: ThreadPoolExecutor):
        """Start the task using a thread pool executor for better performance."""
        if self.status == TaskStatus.RUNNING:
            return
            
        self.status = TaskStatus.RUNNING
        self.progress = 0.0
        self.result = None
        self.error = None
        
        # Add progress reporting capability to kwargs
        self.kwargs['report_progress'] = self._report_progress
        self.kwargs['is_canceled'] = self._is_canceled
        
        # Submit to thread pool instead of creating new thread
        self._future = executor.submit(self._run_task)
        
    def _run_task(self):
        """Execute the task and handle results/errors."""
        try:
            result = self.func(*self.args, **self.kwargs)
            # Always put the result in the queue, even if canceled
            self._result_queue.put((True, result))
        except Exception as e:
            # Always put the error in the queue, even if canceled
            self._result_queue.put((False, e))
    
    def _report_progress(self, progress: float, message: str = ""):
        """Report progress from the worker thread."""
        if 0.0 <= progress <= 1.0:
            self._progress_queue.put((progress, message))
    
    def _is_canceled(self) -> bool:
        """Check if the task has been canceled."""
        return self._cancel_event.is_set()
    
    def cancel(self):
        """Request cancellation of the task."""
        if self.status == TaskStatus.RUNNING:
            # Just set the cancel flag, don't change status yet
            # Let the update method handle the status change
            self._cancel_event.set()
            
            # Cancel the future if it exists
            if self._future:
                self._future.cancel()
    
    def update(self) -> bool:
        """
        Update the task state, process progress reports and check for completion.
        
        Returns:
            bool: True if the task state changed, False otherwise
        """
        if self.status != TaskStatus.RUNNING:
            return False
            
        state_changed = False
        
        # Check for cancellation
        if self._cancel_event.is_set():
            # If we have a result already, process it
            if not self._result_queue.empty():
                success, result = self._result_queue.get()
                if success:
                    self.result = result
                self.status = TaskStatus.CANCELED
                return True
            # Otherwise just mark as canceled if thread is done
            if not self.thread.is_alive():
                self.status = TaskStatus.CANCELED
                return True
        
        # Process all available progress updates
        while not self._progress_queue.empty():
            try:
                progress, message = self._progress_queue.get(block=False)
                self.progress = progress
                state_changed = True
            except queue.Empty:
                break
            
        # Check if the task has completed
        if not self._result_queue.empty():
            try:
                success, result = self._result_queue.get(block=False)
                if self._cancel_event.is_set():
                    self.status = TaskStatus.CANCELED
                elif success:
                    self.result = result
                    self.status = TaskStatus.COMPLETED
                else:
                    self.error = result
                    self.status = TaskStatus.FAILED
                state_changed = True
            except queue.Empty:
                pass
            
        return state_changed


class TaskManager:
    """
    Manages multiple asynchronous tasks with thread pool optimization.
    """
    def __init__(self, max_workers: int = None):
        threading_config = get_threading_config()
        if max_workers is None:
            max_workers = threading_config.DEFAULT_MAX_WORKERS
            
        self.tasks: Dict[str, AsyncTask] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, 
            thread_name_prefix=threading_config.THREAD_NAME_PREFIX
        )
        self._active_task_count = 0
        
    def create_task(self, task_id: str, func: Callable, *args, **kwargs) -> AsyncTask:
        """
        Create and register a new task.
        
        Args:
            task_id: Unique identifier for the task
            func: The function to execute asynchronously
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            AsyncTask: The created task
        """
        task = AsyncTask(task_id, func, args, kwargs)
        self.tasks[task_id] = task
        return task
        
    def start_task(self, task_id: str) -> bool:
        """
        Start a registered task using the thread pool for better performance.
        
        Args:
            task_id: The ID of the task to start
            
        Returns:
            bool: True if the task was started, False if not found
        """
        if task_id in self.tasks:
            # Use thread pool for better performance and resource management
            self.tasks[task_id].start_with_executor(self._executor)
            self._active_task_count += 1
            return True
        return False
        
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_id: The ID of the task to cancel
            
        Returns:
            bool: True if the task was canceled, False if not found
        """
        if task_id in self.tasks:
            self.tasks[task_id].cancel()
            return True
        return False
        
    def update_all(self) -> List[str]:
        """
        Update all tasks and return IDs of tasks that changed state.
        
        Returns:
            List[str]: List of task IDs that had state changes
        """
        changed_tasks = []
        for task_id, task in list(self.tasks.items()):
            if task.update():
                changed_tasks.append(task_id)
                
            # Clean up completed/failed/canceled tasks after some time
            if task.status != TaskStatus.RUNNING and task.status != TaskStatus.PENDING:
                # In a real app, you might want to keep them around longer or log them
                pass
                
        return changed_tasks
        
    def get_task(self, task_id: str) -> Optional[AsyncTask]:
        """Get a task by ID."""
        return self.tasks.get(task_id)
        
    def remove_task(self, task_id: str) -> bool:
        """Remove a task from the manager."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            # Decrease active task count if task was running
            if task.status == TaskStatus.RUNNING:
                self._active_task_count = max(0, self._active_task_count - 1)
            del self.tasks[task_id]
            return True
        return False

    def shutdown(self):
        """Shutdown the thread pool and cleanup resources."""
        # Cancel all running tasks
        for task in self.tasks.values():
            if task.status == TaskStatus.RUNNING:
                task.cancel()
        
        # Shutdown the executor
        self._executor.shutdown(wait=False)

    @property 
    def active_task_count(self) -> int:
        """Get the number of currently running tasks."""
        return self._active_task_count