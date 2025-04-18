"""
Integration example for the enhanced merge functionality and multithreading.
This file demonstrates how to integrate the enhancements into the main GitHubCompare application.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from merge_enhancements import ThreadPoolManager, EnhancedMergeFunctionality

logger = logging.getLogger("GitHubCompare")

def integrate_enhancements(github_compare_instance):
    """
    Integrate the enhanced merge functionality and multithreading into an existing GitHubCompare instance.
    
    Args:
        github_compare_instance: An instance of the GitHubCompare class
    """
    # Add thread manager to the instance
    github_compare_instance.thread_manager = ThreadPoolManager()
    
    # Set up periodic UI updates to check for completed background tasks
    setup_background_task_checker(github_compare_instance)
    
    # Override the run_in_thread method
    original_run_in_thread = github_compare_instance.run_in_thread
    github_compare_instance.run_in_thread = lambda *args, **kwargs: enhanced_run_in_thread(github_compare_instance, *args, **kwargs)
    
    # Override the remove_commits method
    original_remove_commits = github_compare_instance.remove_commits
    github_compare_instance.remove_commits = lambda *args, **kwargs: enhanced_remove_commits(github_compare_instance, *args, **kwargs)
    
    # Add a new merge_branches method
    github_compare_instance.merge_branches = lambda *args, **kwargs: enhanced_merge_branches(github_compare_instance, *args, **kwargs)
    
    # Override the run method to clean up thread pool on exit
    original_run = github_compare_instance.run
    github_compare_instance.run = lambda: enhanced_run(github_compare_instance, original_run)
    
    # Store original methods for reference
    github_compare_instance._original_run_in_thread = original_run_in_thread
    github_compare_instance._original_remove_commits = original_remove_commits
    github_compare_instance._original_run = original_run
    
    logger.info("Enhanced merge functionality and multithreading integrated successfully")

def setup_background_task_checker(github_compare_instance):
    """Set up a periodic check for completed background tasks"""
    def check_tasks():
        # Process any completed tasks
        results = github_compare_instance.thread_manager.get_results()
        for task_id, success, result in results:
            handler_name = f"_handle_task_{task_id}"
            if hasattr(github_compare_instance, handler_name):
                # Call the specific handler for this task
                handler = getattr(github_compare_instance, handler_name)
                handler(success, result)
        
        # Schedule the next check
        github_compare_instance.root.after(100, check_tasks)
    
    # Start the periodic check
    github_compare_instance.root.after(100, check_tasks)

def enhanced_run_in_thread(github_compare_instance, func, message="Working...", success_message=None, error_message=None):
    """Run a function in a background thread with UI feedback"""
    # Show progress and status message
    github_compare_instance.status_var.set(message)
    github_compare_instance.progress.pack(side=tk.BOTTOM, fill=tk.X, before=github_compare_instance.status_bar)
    github_compare_instance.progress.start()
    
    # Define a wrapper function to handle the result
    def task_wrapper():
        try:
            result = func()
            return result
        except Exception as e:
            logger.error(f"Error in background task: {str(e)}")
            # Show error message in the UI thread
            github_compare_instance.root.after(0, lambda: github_compare_instance.show_error(
                str(e) if error_message is None else error_message))
            raise e
        finally:
            # Hide progress and update status in the UI thread
            github_compare_instance.root.after(0, lambda: github_compare_instance.progress.pack_forget())
            github_compare_instance.root.after(0, lambda: github_compare_instance.status_var.set(
                "Ready" if success_message is None else success_message))
    
    # Submit the task to the thread manager
    task_id = github_compare_instance.thread_manager.submit_task(task_wrapper)
    
    # Create a handler for this task
    setattr(github_compare_instance, f"_handle_task_{task_id}", lambda success, result: None)
    
    return task_id

def enhanced_remove_commits(github_compare_instance, repo_name, branch_name, commits_to_remove):
    """Remove commits from a branch using the enhanced functionality"""
    return EnhancedMergeFunctionality.remove_commits_parallel(
        github_compare_instance.g, 
        repo_name, 
        branch_name, 
        commits_to_remove, 
        github_compare_instance.github_token
    )

def enhanced_merge_branches(github_compare_instance, repo_name, base_branch, head_branch, merge_method="merge", commit_message=None):
    """Merge branches using the enhanced functionality"""
    return EnhancedMergeFunctionality.merge_branches(
        github_compare_instance.g, 
        repo_name, 
        base_branch, 
        head_branch, 
        merge_method, 
        commit_message
    )

def enhanced_run(github_compare_instance, original_run):
    """Run the application and clean up thread pool on exit"""
    try:
        # Call the original run method
        original_run()
    finally:
        # Clean up thread pool on exit
        if hasattr(github_compare_instance, 'thread_manager'):
            github_compare_instance.thread_manager.shutdown()

# Example usage:
"""
# In the main application:
from integration_example import integrate_enhancements

# After initializing the GitHubCompare instance:
app = GitHubCompare()
integrate_enhancements(app)
app.run()
"""
