import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
import os
import sys

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our enhanced modules
from enhancements.thread_pool import ThreadPoolManager
from enhancements.merge_enhancements import MergeManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.expanduser("~"), ".github_compare_enhanced.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("IntegrationExample")

class EnhancedGitHubCompare:
    """Example class showing how to integrate the enhancements"""
    
    def __init__(self, root, github_token):
        self.root = root
        self.github_token = github_token
        
        # Initialize our enhanced components
        self.thread_pool = ThreadPoolManager(max_workers=5)
        self.merge_manager = MergeManager(github_token, root)
        
        # Set up a timer to process callbacks from the thread pool
        self._setup_callback_timer()
        
        # Register cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
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
    
    def start_progress(self, message):
        """Show progress indication"""
        logger.info(f"Starting task: {message}")
        # In a real implementation, this would update a progress bar or status message
        # For this example, we'll just log it
    
    def stop_progress(self, message):
        """Hide progress indication"""
        logger.info(f"Task completed: {message}")
        # In a real implementation, this would update a progress bar or status message
    
    def handle_error(self, error):
        """Handle errors from background threads"""
        error_message = str(error)
        logger.error(f"Error: {error_message}")
        messagebox.showerror("Error", error_message)
    
    def merge_commit(self, repo_name, branch_name, commit_sha, 
                    merge_strategy="merge", message=None):
        """Merge a commit using our enhanced merge functionality"""
        
        def perform_merge():
            return self.merge_manager.merge_commit(
                repo_name, branch_name, commit_sha,
                merge_strategy=merge_strategy,
                message=message
            )
        
        return self.run_in_thread(
            perform_merge,
            message=f"Merging commit {commit_sha[:7]}...",
            success_message=f"Successfully merged commit {commit_sha[:7]}"
        )
    
    def check_for_conflicts(self, repo_name, branch_name, commit_sha):
        """Check if merging a commit would cause conflicts"""
        
        def perform_check():
            return self.merge_manager.check_for_conflicts(
                repo_name, branch_name, commit_sha
            )
        
        return self.run_in_thread(
            perform_check,
            message=f"Checking for conflicts with commit {commit_sha[:7]}...",
            success_message=f"Conflict check completed for commit {commit_sha[:7]}"
        )
    
    def auto_resolve_conflicts(self, repo_name, branch_name, commit_sha, strategy="ours"):
        """Automatically resolve merge conflicts"""
        
        def perform_resolve():
            return self.merge_manager.auto_resolve_conflicts(
                repo_name, branch_name, commit_sha, strategy
            )
        
        return self.run_in_thread(
            perform_resolve,
            message=f"Resolving conflicts for commit {commit_sha[:7]}...",
            success_message=f"Successfully resolved conflicts for commit {commit_sha[:7]}"
        )

# Example usage
def example_usage():
    # Create a simple Tkinter window
    root = tk.Tk()
    root.title("GitHub Compare Enhanced Example")
    root.geometry("600x400")
    
    # Get GitHub token from environment or config
    github_token = os.environ.get("GITHUB_TOKEN", "")
    if not github_token:
        # In a real app, you would prompt for the token or load from config
        messagebox.showerror("Error", "GitHub token not found")
        root.destroy()
        return
    
    # Create our enhanced GitHub compare instance
    github_compare = EnhancedGitHubCompare(root, github_token)
    
    # Create a simple UI
    frame = ttk.Frame(root, padding=10)
    frame.pack(fill="both", expand=True)
    
    # Add a label
    label = ttk.Label(frame, text="GitHub Compare Enhanced Example")
    label.pack(pady=10)
    
    # Add some example buttons
    repo_name_var = tk.StringVar(value="owner/repo")
    branch_name_var = tk.StringVar(value="main")
    commit_sha_var = tk.StringVar(value="abcdef1234567890")
    
    # Repository input
    repo_frame = ttk.Frame(frame)
    repo_frame.pack(fill="x", pady=5)
    ttk.Label(repo_frame, text="Repository:").pack(side="left", padx=5)
    ttk.Entry(repo_frame, textvariable=repo_name_var, width=30).pack(side="left", padx=5, fill="x", expand=True)
    
    # Branch input
    branch_frame = ttk.Frame(frame)
    branch_frame.pack(fill="x", pady=5)
    ttk.Label(branch_frame, text="Branch:").pack(side="left", padx=5)
    ttk.Entry(branch_frame, textvariable=branch_name_var, width=30).pack(side="left", padx=5, fill="x", expand=True)
    
    # Commit input
    commit_frame = ttk.Frame(frame)
    commit_frame.pack(fill="x", pady=5)
    ttk.Label(commit_frame, text="Commit SHA:").pack(side="left", padx=5)
    ttk.Entry(commit_frame, textvariable=commit_sha_var, width=30).pack(side="left", padx=5, fill="x", expand=True)
    
    # Buttons frame
    buttons_frame = ttk.Frame(frame)
    buttons_frame.pack(fill="x", pady=10)
    
    # Merge button
    def on_merge():
        repo_name = repo_name_var.get()
        branch_name = branch_name_var.get()
        commit_sha = commit_sha_var.get()
        
        if not all([repo_name, branch_name, commit_sha]):
            messagebox.showerror("Error", "Please fill in all fields")
            return
        
        github_compare.merge_commit(repo_name, branch_name, commit_sha)
    
    merge_btn = ttk.Button(buttons_frame, text="Merge Commit", command=on_merge)
    merge_btn.pack(side="left", padx=5)
    
    # Check conflicts button
    def on_check_conflicts():
        repo_name = repo_name_var.get()
        branch_name = branch_name_var.get()
        commit_sha = commit_sha_var.get()
        
        if not all([repo_name, branch_name, commit_sha]):
            messagebox.showerror("Error", "Please fill in all fields")
            return
        
        github_compare.check_for_conflicts(repo_name, branch_name, commit_sha)
    
    check_btn = ttk.Button(buttons_frame, text="Check Conflicts", command=on_check_conflicts)
    check_btn.pack(side="left", padx=5)
    
    # Auto resolve conflicts button
    def on_resolve_conflicts():
        repo_name = repo_name_var.get()
        branch_name = branch_name_var.get()
        commit_sha = commit_sha_var.get()
        
        if not all([repo_name, branch_name, commit_sha]):
            messagebox.showerror("Error", "Please fill in all fields")
            return
        
        github_compare.auto_resolve_conflicts(repo_name, branch_name, commit_sha)
    
    resolve_btn = ttk.Button(buttons_frame, text="Auto Resolve Conflicts", command=on_resolve_conflicts)
    resolve_btn.pack(side="left", padx=5)
    
    # Start the Tkinter event loop
    root.mainloop()

if __name__ == "__main__":
    example_usage()
