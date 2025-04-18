"""
Thread pool implementation for GitHub Compare tool.
This module provides a thread pool for managing concurrent operations.
"""
import threading
import queue
import logging
import time
from typing import Callable, Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("GitHubCompare.ThreadPool")

class Task:
    """Represents a task to be executed by the thread pool."""
    
    def __init__(self, func: Callable, args: Tuple = None, kwargs: Dict = None, 
                 on_success: Callable = None, on_error: Callable = None,
                 task_id: str = None):
        """
        Initialize a new task.
        
        Args:
            func: The function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            on_success: Callback to execute on successful completion
            on_error: Callback to execute on error
            task_id: Unique identifier for the task
        """
        self.func = func
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.on_success = on_success
        self.on_error = on_error
        self.task_id = task_id or f"task_{id(self)}"
        self.result = None
        self.error = None
        self.is_cancelled = False
        self.is_completed = False
        self.start_time = None
        self.end_time = None
        
    def execute(self) -> Any:
        """Execute the task and handle callbacks."""
        if self.is_cancelled:
            logger.info(f"Task {self.task_id} was cancelled before execution")
            return None
            
        self.start_time = time.time()
        try:
            logger.info(f"Executing task {self.task_id}")
            self.result = self.func(*self.args, **self.kwargs)
            if self.on_success and not self.is_cancelled:
                self.on_success(self.result)
            return self.result
        except Exception as e:
            logger.error(f"Error executing task {self.task_id}: {str(e)}")
            self.error = e
            if self.on_error and not self.is_cancelled:
                self.on_error(e)
            return None
        finally:
            self.end_time = time.time()
            self.is_completed = True
            duration = self.end_time - self.start_time
            logger.info(f"Task {self.task_id} completed in {duration:.2f} seconds")
            
    def cancel(self) -> bool:
        """
        Mark the task as cancelled.
        
        Returns:
            bool: True if the task was cancelled, False if it was already completed
        """
        if self.is_completed:
            return False
        self.is_cancelled = True
        logger.info(f"Task {self.task_id} cancelled")
        return True


class ThreadPool:
    """A thread pool for executing tasks concurrently."""
    
    def __init__(self, num_workers: int = 5, queue_size: int = 100):
        """
        Initialize the thread pool.
        
        Args:
            num_workers: Number of worker threads
            queue_size: Maximum size of the task queue
        """
        self.task_queue = queue.Queue(maxsize=queue_size)
        self.workers = []
        self.running = True
        self.active_tasks = {}  # task_id -> Task
        self.lock = threading.Lock()
        
        # Start worker threads
        for i in range(num_workers):
            worker = threading.Thread(target=self._worker_loop, name=f"ThreadPool-Worker-{i}")
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
            
        logger.info(f"Thread pool initialized with {num_workers} workers")
        
    def _worker_loop(self):
        """Worker thread function that processes tasks from the queue."""
        while self.running:
            try:
                task = self.task_queue.get(block=True, timeout=0.5)
                try:
                    with self.lock:
                        self.active_tasks[task.task_id] = task
                    
                    task.execute()
                    
                finally:
                    with self.lock:
                        if task.task_id in self.active_tasks:
                            del self.active_tasks[task.task_id]
                    self.task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in worker thread: {str(e)}")
                
    def submit(self, func: Callable, args: Tuple = None, kwargs: Dict = None,
               on_success: Callable = None, on_error: Callable = None,
               task_id: str = None) -> Task:
        """
        Submit a task to the thread pool.
        
        Args:
            func: The function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            on_success: Callback to execute on successful completion
            on_error: Callback to execute on error
            task_id: Unique identifier for the task
            
        Returns:
            Task: The submitted task
        """
        task = Task(func, args, kwargs, on_success, on_error, task_id)
        logger.info(f"Submitting task {task.task_id}")
        self.task_queue.put(task)
        return task
        
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task by its ID.
        
        Args:
            task_id: The ID of the task to cancel
            
        Returns:
            bool: True if the task was cancelled, False otherwise
        """
        with self.lock:
            if task_id in self.active_tasks:
                return self.active_tasks[task_id].cancel()
        return False
        
    def cancel_all_tasks(self) -> int:
        """
        Cancel all active tasks.
        
        Returns:
            int: Number of tasks cancelled
        """
        cancelled_count = 0
        with self.lock:
            for task_id, task in list(self.active_tasks.items()):
                if task.cancel():
                    cancelled_count += 1
        logger.info(f"Cancelled {cancelled_count} tasks")
        return cancelled_count
        
    def shutdown(self, wait: bool = True):
        """
        Shutdown the thread pool.
        
        Args:
            wait: If True, wait for all tasks to complete
        """
        logger.info("Shutting down thread pool")
        self.running = False
        
        if wait:
            self.task_queue.join()
            
        # Clear the queue
        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait()
                self.task_queue.task_done()
            except queue.Empty:
                break
                
        logger.info("Thread pool shutdown complete")
