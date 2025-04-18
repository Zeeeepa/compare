    def _setup_callback_timer(self):
        """Set up a timer to process callbacks from the thread pool"""
        def process_callbacks():
            self.thread_pool.process_callbacks()
            self.root.after(100, process_callbacks)
        
        self.root.after(100, process_callbacks)
    
    def _on_close(self):
        """Clean up resources when the window is closed"""
        logger.info("Shutting down...")
        self.thread_pool.shutdown()
        self.root.destroy()
