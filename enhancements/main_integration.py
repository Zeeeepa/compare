#!/usr/bin/env python3
"""
Main integration script for GitHub Compare enhancements.
This script patches the original gitcompare.py file with our enhanced functionality.
"""

import os
import sys
import shutil
import logging
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MainIntegration")

def backup_original_file(filepath):
    """Create a backup of the original file"""
    backup_path = f"{filepath}.bak"
    if os.path.exists(backup_path):
        logger.info(f"Backup already exists at {backup_path}")
        return backup_path
    
    logger.info(f"Creating backup of {filepath} at {backup_path}")
    shutil.copy2(filepath, backup_path)
    return backup_path

def patch_gitcompare():
    """Patch the gitcompare.py file with our enhanced functionality"""
    # Get the path to the gitcompare.py file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.dirname(script_dir)
    gitcompare_path = os.path.join(repo_dir, "gitcompare.py")
    
    # Check if the file exists
    if not os.path.exists(gitcompare_path):
        logger.error(f"Could not find gitcompare.py at {gitcompare_path}")
        return False
    
    # Create a backup of the original file
    backup_path = backup_original_file(gitcompare_path)
    
    # Read the original file
    with open(gitcompare_path, "r") as f:
        content = f.read()
    
    # Apply our patches
    patched_content = apply_patches(content)
    
    # Write the patched file
    with open(gitcompare_path, "w") as f:
        f.write(patched_content)
    
    logger.info(f"Successfully patched {gitcompare_path}")
    logger.info(f"Original file backed up at {backup_path}")
    return True

def apply_patches(content):
    """Apply our patches to the content of gitcompare.py"""
    # Import our enhanced modules
    import_patch = """import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import webbrowser
import threading
import json
import datetime
import time
import logging
import tempfile
import subprocess
import queue
import concurrent.futures
import signal
import atexit
from github import Github, GithubException
from functools import partial

# Import our enhanced modules
from enhancements.thread_pool import ThreadPoolManager
from enhancements.merge_enhancements import MergeManager
"""
    
    # Replace the imports
    content = content.replace("""import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import webbrowser
import threading
import json
import datetime
import time
import logging
import tempfile
import subprocess
from github import Github, GithubException
from functools import partial
""", import_patch)
    
    # Add thread pool initialization
    init_patch = """    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Branch Comparison Tool")
        self.root.geometry("1000x700")  # Larger default window size
        
        # Initialize variables
        self.github_token = ""
        self.g = None
        self.cache = {
            "repos": [],
            "branches": {},
            "last_updated": None
        }
        
        # Initialize thread pool and merge manager
        self.thread_pool = ThreadPoolManager(max_workers=5)
        
        # Load token from config file
        self.config_file = os.path.join(os.path.expanduser("~"), ".github_compare_config")
        self.load_config()
        
        # Initialize merge manager after loading token
        self.merge_manager = MergeManager(self.github_token, self.root)
        
        # Set up a timer to process callbacks from the thread pool
        self._setup_callback_timer()
        
        # Register cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Create main frame with status bar
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)"""
    
    # Replace the __init__ method
    content = content.replace("""    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Branch Comparison Tool")
        self.root.geometry("1000x700")  # Larger default window size
        
        # Initialize variables
        self.github_token = ""
        self.g = None
        self.cache = {
            "repos": [],
            "branches": {},
            "last_updated": None
        }
        
        # Load token from config file
        self.config_file = os.path.join(os.path.expanduser("~"), ".github_compare_config")
        self.load_config()
        
        # Create main frame with status bar
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)""", init_patch)
    
    # Add callback timer and cleanup methods
    callback_patch = """    def _setup_callback_timer(self):
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
"""
    
    # Add the callback timer and cleanup methods after the __init__ method
    content = content.replace("    def load_config(self):", callback_patch + "    def load_config(self):")
    
    # Replace the run_in_thread method
    run_in_thread_patch = """    def run_in_thread(self, func, *args, message="Working...", success_message="Complete", **kwargs):
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
        
        return task_id, future"""
    
    # Replace the run_in_thread method
    content = content.replace("""    def run_in_thread(self, func, *args, message="Working...", success_message="Complete", **kwargs):
        """Run a function in a background thread with progress indication"""
        self.start_progress(message)
        
        def thread_func():
            try:
                result = func(*args, **kwargs)
                self.root.after(0, lambda: self.stop_progress(success_message))
                return result
            except Exception as e:
                error_message = str(e)  # Capture the error message
                self.root.after(0, lambda error_msg=error_message: 
                            self.handle_error(Exception(error_msg)))
                return None
                
        thread = threading.Thread(target=thread_func)
        thread.daemon = True
        thread.start()
        return thread""", run_in_thread_patch)
    
    # Replace the merge_commit method
    merge_commit_patch = """    def merge_commit(self, commit):
        """Merge a specific commit from parent repo into fork"""
        if not self.current_fork:
            messagebox.showerror("Error", "No fork selected")
            return
        
        # Confirm the merge
        if not messagebox.askyesno(
            "Confirm Merge",
            f"Are you sure you want to merge commit {commit.sha[:7]} into your fork?"
        ):
            return
        
        # Use our enhanced merge manager
        repo_name = self.current_fork.full_name
        branch_name = self.current_branch
        commit_sha = commit.sha
        
        def perform_merge():
            return self.merge_manager.merge_commit(
                repo_name, branch_name, commit_sha,
                merge_strategy="merge",
                message=f"Merge commit {commit_sha[:7]} from parent"
            )
        
        self.run_in_thread(
            perform_merge,
            message=f"Merging commit {commit.sha[:7]}...",
            success_message=f"Successfully merged commit {commit.sha[:7]}"
        )
        
        # Refresh the UI after merge
        self.root.after(1000, lambda: self.after_merge())"""
    
    # Replace the merge_commit method
    content = content.replace("""    def merge_commit(self, commit):
        """Merge a specific commit from parent repo into fork"""
        if not self.current_fork:
            messagebox.showerror("Error", "No fork selected")
            return
        
        # Confirm the merge
        if not messagebox.askyesno(
            "Confirm Merge",
            f"Are you sure you want to merge commit {commit.sha[:7]} into your fork?"
        ):
            return
        
        def perform_merge():
            try:
                # Create a temporary branch for the merge
                temp_branch = f"temp-merge-{commit.sha[:7]}"
                
                # Get the current branch reference
                branch_ref = self.current_fork.get_git_ref(f"heads/{self.current_branch}")
                
                # Create the temporary branch
                self.current_fork.create_git_ref(f"refs/heads/{temp_branch}", branch_ref.object.sha)
                
                # Merge the commit into the temporary branch
                cherry_pick = self.current_fork.merge(
                    temp_branch,
                    commit.sha,
                    f"Cherry-pick commit {commit.sha[:7]} from parent"
                )
                
                # Merge temp branch back to base
                merge_result = self.current_fork.merge(
                    self.current_branch,
                    temp_branch,
                    f"Merge commit {commit.sha[:7]} from parent"
                )
                
                # Clean up the temporary branch
                self.current_fork.get_git_ref(f"heads/{temp_branch}").delete()
                
                self.root.after(0, lambda: self.after_merge())
                
                return merge_result
            except Exception as e:
                raise Exception(f"Failed to merge commit: {str(e)}")
        
        self.run_in_thread(perform_merge,
                        message=f"Merging commit {commit.sha[:7]}...",
                        success_message=f"Commit {commit.sha[:7]} merged successfully")""", merge_commit_patch)
    
    # Add enhanced commit removal functionality
    remove_commits_patch = """    def _remove_commits_api_method(self, repo_name, branch_name, commits_to_remove):
        """Remove commits using the GitHub API method with enhanced error handling and performance"""
        logger.info(f"Using enhanced GitHub API method to remove {len(commits_to_remove)} commits")
        
        repo = self.g.get_repo(repo_name)
        
        # Create a temporary branch for the operation
        temp_branch_name = f"temp-remove-commits-{int(datetime.datetime.now().timestamp())}"
        logger.info(f"Creating temporary branch: {temp_branch_name}")
        
        # Get the current branch reference
        branch_ref = repo.get_git_ref(f"heads/{branch_name}")
        
        try:
            # Create the temporary branch
            temp_ref = repo.create_git_ref(f"refs/heads/{temp_branch_name}", branch_ref.object.sha)
            
            # Get all commits in chronological order
            logger.info(f"Fetching all commits from {branch_name}")
            all_commits = list(repo.get_commits(sha=branch_name))
            
            # Filter out selected commits to remove
            commits_to_keep = [c for c in all_commits if c.sha not in commits_to_remove]
            
            if not commits_to_keep:
                raise Exception("Cannot remove all commits from the branch")
                
            # Find the oldest commit to keep
            base_commit = commits_to_keep[-1]
            logger.info(f"Base commit for new history: {base_commit.sha[:7]}")
            
            # Process commits in batches for better performance
            batch_size = 20
            total_commits = len(commits_to_keep)
            
            # Hard reset to the base commit
            temp_ref.edit(base_commit.sha, force=True)
            
            # Apply the commits to keep in batches
            for i in range(0, total_commits - 1, batch_size):
                batch = commits_to_keep[i:i+batch_size]
                logger.info(f"Processing batch {i//batch_size + 1} of {(total_commits + batch_size - 1)//batch_size}")
                
                for commit in reversed(batch):
                    if commit.sha == base_commit.sha:
                        continue
                    
                    # Cherry-pick each commit
                    try:
                        repo.merge(temp_branch_name, commit.sha, f"Cherry-pick {commit.sha[:7]}")
                    except Exception as e:
                        logger.warning(f"Failed to cherry-pick commit {commit.sha[:7]}: {str(e)}")
                        # Try to continue with the next commit
            
            # Update the original branch to point to the new history
            logger.info(f"Updating {branch_name} to new history")
            branch_ref.edit(temp_ref.object.sha, force=True)
            
            # Clean up the temporary branch
            logger.info(f"Cleaning up temporary branch")
            repo.get_git_ref(f"heads/{temp_branch_name}").delete()
            
            return True
        except Exception as e:
            # Clean up the temporary branch in case of error
            try:
                repo.get_git_ref(f"heads/{temp_branch_name}").delete()
            except:
                pass
            raise e"""
    
    # Replace the _remove_commits_api_method method
    content = content.replace("""    def _remove_commits_api_method(self, repo_name, branch_name, commits_to_remove):
        """Remove commits using the GitHub API method"""
        logger.info(f"Using GitHub API method to remove {len(commits_to_remove)} commits")
        
        repo = self.g.get_repo(repo_name)
        
        # Get the current branch reference
        branch_ref = repo.get_git_ref(f"heads/{branch_name}")
        
        # Create a temporary branch for the operation
        temp_branch_name = f"temp-remove-commits-{int(datetime.datetime.now().timestamp())}"
        logger.info(f"Creating temporary branch: {temp_branch_name}")
        
        try:
            temp_ref = repo.create_git_ref(f"refs/heads/{temp_branch_name}", branch_ref.object.sha)
            
            # Get all commits in chronological order
            logger.info(f"Fetching all commits from {branch_name}")
            all_commits = list(repo.get_commits(sha=branch_name))
            
            # Filter out selected commits to remove
            commits_to_keep = [c for c in all_commits if c.sha not in commits_to_remove]
            
            if not commits_to_keep:
                raise Exception("Cannot remove all commits from the branch")
                
            # Find the oldest commit to keep
            base_commit = commits_to_keep[-1]
            logger.info(f"Base commit for new history: {base_commit.sha[:7]}")
            
            # Hard reset to the base commit""", remove_commits_patch)
    
    return content

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Integrate enhanced functionality into GitHub Compare")
    parser.add_argument("--no-backup", action="store_true", help="Skip creating a backup of the original file")
    args = parser.parse_args()
    
    logger.info("Starting integration of enhanced functionality")
    
    # Patch the gitcompare.py file
    if patch_gitcompare():
        logger.info("Integration complete!")
        logger.info("You can now run the original gitcompare.py with enhanced functionality")
    else:
        logger.error("Integration failed")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
