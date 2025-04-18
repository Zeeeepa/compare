    def run_in_thread(self, func, *args, message="Working...", success_message="Complete", **kwargs):
        """Run a function in a background thread with progress indication"""
        self.start_progress(message)
        
        def on_success(result):
            self.stop_progress(success_message)
            return result
        
        def on_error(error):
            self.handle_error(error)
            return None
        
        task_id, future = self.thread_pool.submit_task(
            func, *args, 
            callback=on_success,
            error_callback=on_error,
            **kwargs
        )
        
        return task_id, future
