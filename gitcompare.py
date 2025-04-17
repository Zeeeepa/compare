import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import webbrowser
import threading
import json
import datetime
import logging
from github import Github, GithubException
from functools import partial

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gitcompare.log'),
        logging.StreamHandler()
    ]
)

class GitOperationError(Exception):
    """Custom exception for git operations"""
    pass

class GitHubCompare:
    def __init__(self):
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
        self.temp_resources = []  # Track temporary resources for cleanup
        
        # Load token from config file
        self.config_file = os.path.join(os.path.expanduser("~"), ".github_compare_config")
        self.load_config()
        
        # Create main frame with status bar
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create progress bar (hidden by default)
        self.progress = ttk.Progressbar(self.root, mode="indeterminate")
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(pady=10, expand=True, fill="both")
        
        # Create tabs
        self.local_tab = ttk.Frame(self.notebook)
        self.origin_tab = ttk.Frame(self.notebook)
        self.commit_list_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.local_tab, text="Local Compare")
        self.notebook.add(self.origin_tab, text="Origin Compare")
        self.notebook.add(self.commit_list_tab, text="Commit List")
        
        # Setup tabs
        self.setup_local_tab()
        self.setup_origin_tab()
        self.setup_commit_list_tab()
        
        # Add settings button and refresh button
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        settings_btn = ttk.Button(button_frame, text="⚙️ Settings", command=self.show_settings)
        settings_btn.pack(side=tk.LEFT, padx=5)
        
        refresh_btn = ttk.Button(button_frame, text="🔄 Refresh", command=self.refresh_data)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # Initialize GitHub client if token exists
        if self.github_token:
            self.init_github_client()

    def cleanup_temp_resources(self):
        """Clean up any temporary resources created during operations"""
        logging.info("Cleaning up temporary resources")
        for resource in self.temp_resources:
            try:
                if 'ref' in resource:
                    logging.info(f"Deleting temporary ref: {resource['ref']}")
                    resource['ref'].delete()
                # Add other resource cleanup as needed
            except Exception as e:
                logging.error(f"Failed to cleanup resource: {str(e)}")
        self.temp_resources.clear()

    def remove_selected_commits(self):
        """Remove selected commits from the branch"""
        repo_name = self.commit_list_repo_var.get()
        branch_name = self.commit_list_branch_var.get()
        
        if not repo_name or not branch_name:
            messagebox.showerror("Error", "Please select a repository and branch")
            return
            
        # Get selected commits
        selected_commits = [sha for sha, var in self.commit_checkboxes.items() if var.get()]
        
        if not selected_commits:
            messagebox.showinfo("Information", "No commits selected for removal")
            return
        
        # Confirmation dialog
        response = messagebox.askyesno(
            "Confirm Commit Removal", 
            f"Are you sure you want to remove {len(selected_commits)} selected commits from {branch_name}?\n\n"
            "This operation will rewrite the branch history and cannot be undone."
        )
        
        if not response:
            return
        
        def perform_removal():
            try:
                repo = self.g.get_repo(repo_name)
                logging.info(f"Starting commit removal for {repo_name}/{branch_name}")
                
                # Get the current branch reference
                try:
                    branch_ref = repo.get_git_ref(f"heads/{branch_name}")
                    logging.info(f"Got branch ref: {branch_ref.ref}, SHA: {branch_ref.object.sha}")
                except GithubException as e:
                    raise GitOperationError(f"Failed to get branch reference: {str(e)}")
                
                # Create a temporary branch for the operation
                temp_branch_name = f"temp-remove-commits-{int(datetime.datetime.now().timestamp())}"
                try:
                    temp_ref = repo.create_git_ref(f"refs/heads/{temp_branch_name}", branch_ref.object.sha)
                    self.temp_resources.append({'ref': temp_ref})
                    logging.info(f"Created temporary branch: {temp_branch_name}")
                except GithubException as e:
                    raise GitOperationError(f"Failed to create temporary branch: {str(e)}")
                
                # Get all commits in chronological order
                try:
                    all_commits = list(repo.get_commits(sha=branch_name))
                    logging.info(f"Found {len(all_commits)} total commits")
                except GithubException as e:
                    raise GitOperationError(f"Failed to get commits: {str(e)}")
                
                # Filter out selected commits to remove
                commit_to_keep = [c for c in all_commits if c.sha not in selected_commits]
                logging.info(f"Keeping {len(commit_to_keep)} commits")
                
                if not commit_to_keep:
                    raise GitOperationError("Cannot remove all commits from the branch")
                    
                # Find the oldest commit to keep
                base_commit = commit_to_keep[-1]
                logging.info(f"Base commit: {base_commit.sha}")
                
                try:
                    # Hard reset to the base commit
                    temp_ref.edit(base_commit.sha, force=True)
                    logging.info(f"Reset temp branch to base commit: {base_commit.sha}")
                except GithubException as e:
                    raise GitOperationError(f"Failed to reset to base commit: {str(e)}")
                
                # Cherry-pick each commit to keep in reverse order (oldest to newest)
                for commit in reversed(commit_to_keep[:-1]):  # Skip the base commit
                    try:
                        # Get the commit data
                        commit_data = repo.get_git_commit(commit.sha)
                        tree = commit_data.tree
                        parents = [base_commit.sha]
                        
                        # Create a new commit with the same data
                        new_commit = repo.create_git_commit(
                            message=commit_data.message,
                            tree=tree,
                            parents=parents
                        )
                        logging.info(f"Cherry-picked commit: {commit.sha} -> {new_commit.sha}")
                        
                        # Update the temp branch reference
                        temp_ref.edit(new_commit.sha, force=True)
                        
                        # Update the base commit for the next iteration
                        base_commit = repo.get_git_commit(new_commit.sha)
                    except GithubException as e:
                        raise GitOperationError(f"Failed to cherry-pick commit {commit.sha}: {str(e)}")
                
                try:
                    # Update the original branch to point to the new history
                    branch_ref.edit(temp_ref.object.sha, force=True)
                    logging.info(f"Updated original branch to new history: {temp_ref.object.sha}")
                except GithubException as e:
                    # Try fallback method - create backup and retry
                    try:
                        backup_name = f"backup-{branch_name}-{int(datetime.datetime.now().timestamp())}"
                        backup_ref = repo.create_git_ref(f"refs/heads/{backup_name}", branch_ref.object.sha)
                        self.temp_resources.append({'ref': backup_ref})
                        logging.info(f"Created backup branch: {backup_name}")
                        
                        # Retry update with force
                        branch_ref.edit(temp_ref.object.sha, force=True)
                        logging.info("Successfully updated branch using fallback method")
                    except GithubException as e2:
                        raise GitOperationError(f"Failed to update branch (with fallback): {str(e2)}")
                
                # Update UI in main thread
                self.root.after(0, lambda: self.after_commit_removal(len(selected_commits)))
                
            except GitOperationError as e:
                logging.error(f"Git operation failed: {str(e)}")
                raise
            except Exception as e:
                logging.error(f"Unexpected error: {str(e)}")
                raise GitOperationError(f"Unexpected error: {str(e)}")
            finally:
                # Always try to cleanup temporary resources
                self.cleanup_temp_resources()
        
        # Run in background thread
        self.run_in_thread(
            perform_removal, 
            message=f"Removing {len(selected_commits)} commits...", 
            success_message=f"Successfully removed {len(selected_commits)} commits",
            error_handler=lambda e: logging.error(f"Thread error: {str(e)}")
        )

    def run_in_thread(self, func, message, success_message, error_handler=None):
        """Run a function in a background thread with progress indication"""
        def thread_wrapper():
            try:
                self.status_var.set(message)
                self.progress.pack(fill=tk.X, padx=5, pady=5)
                self.progress.start()
                
                result = func()
                
                self.root.after(0, lambda: self.status_var.set(success_message))
                return result
                
            except Exception as e:
                error_msg = str(e)
                logging.error(f"Operation failed: {error_msg}")
                if error_handler:
                    error_handler(e)
                self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            finally:
                self.root.after(0, lambda: self.progress.stop())
                self.root.after(0, lambda: self.progress.pack_forget())
        
        thread = threading.Thread(target=thread_wrapper)
        thread.daemon = True
        thread.start()
