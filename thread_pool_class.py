# ThreadPoolManager class for enhanced thread management
class ThreadPoolManager:
    """Manages a pool of worker threads for background tasks"""
    def __init__(self, max_workers=None):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.tasks = {}
        self.task_counter = 0
        self.task_lock = threading.Lock()
        self.running = True
        self.results_queue = queue.Queue()
        
        # Register cleanup on exit
        atexit.register(self.shutdown)
        
    def submit_task(self, func, *args, callback=None, error_callback=None, **kwargs):
        """Submit a task to the thread pool and return a task ID"""
        with self.task_lock:
            task_id = self.task_counter
            self.task_counter += 1
            
            # Wrap the function to handle callbacks
            def wrapped_func(*args, **kwargs):
                try:
                    result = func(*args, **kwargs)
                    if callback:
                        self.results_queue.put((callback, result, None))
                    return result
                except Exception as e:
                    logger.error(f"Task {task_id} failed: {str(e)}")
                    if error_callback:
                        self.results_queue.put((error_callback, None, e))
                    raise
            
            future = self.executor.submit(wrapped_func, *args, **kwargs)
            self.tasks[task_id] = future
            
            # Add callback to clean up completed tasks
            future.add_done_callback(lambda f, tid=task_id: self._task_done(tid))
            
            return task_id, future
    
    def _task_done(self, task_id):
        """Remove completed task from the tasks dictionary"""
        with self.task_lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
    
    def cancel_task(self, task_id):
        """Cancel a running task by ID"""
        with self.task_lock:
            if task_id in self.tasks:
                future = self.tasks[task_id]
                return future.cancel()
            return False
    
    def cancel_all_tasks(self):
        """Cancel all running tasks"""
        with self.task_lock:
            for task_id, future in list(self.tasks.items()):
                future.cancel()
    
    def process_callbacks(self):
        """Process any pending callbacks in the results queue"""
        try:
            while not self.results_queue.empty():
                callback, result, error = self.results_queue.get_nowait()
                if error:
                    callback(error)
                else:
                    callback(result)
        except queue.Empty:
            pass
    
    def shutdown(self):
        """Shutdown the thread pool and cancel all tasks"""
        if not self.running:
            return
            
        logger.info("Shutting down thread pool")
        self.running = False
        self.cancel_all_tasks()
        self.executor.shutdown(wait=False)
        
    def get_active_task_count(self):
        """Return the number of active tasks"""
        with self.task_lock:
            return len(self.tasks)
