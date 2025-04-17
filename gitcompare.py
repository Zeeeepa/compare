import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import webbrowser
import threading
import json
import datetime
from github import Github, GithubException
from functools import partial

class CommitRemovalError(Exception):
    """Custom exception for commit removal errors"""
    pass

def remove_commits(repo, branch_name, selected_commits, status_callback=None):
    """
    Remove selected commits from a given branch.

    Parameters:
      repo: The repository object.
      branch_name: The name of the branch.
      selected_commits: List of commit SHAs to remove.
      status_callback: Optional function to update status.
    """
    try:
        # Get all commits in chronological order
        all_commits = list(repo.get_commits(sha=branch_name))
        commit_to_keep = [c for c in all_commits if c.sha not in selected_commits]
        
        if not commit_to_keep:
            raise CommitRemovalError("Cannot remove all commits from the branch")
            
        base_commit = commit_to_keep[-1]

        # Create a temporary branch for the operation
        temp_branch_name = f"temp-remove-commits-{int(datetime.datetime.now().timestamp())}"
        try:
            branch_ref = repo.get_git_ref(f"heads/{branch_name}")
        except GithubException as e:
            if e.status == 404:
                raise CommitRemovalError(f"Branch '{branch_name}' not found")
            raise CommitRemovalError(f"Error accessing branch: {str(e)}")

        try:
            temp_ref = repo.create_git_ref(f"refs/heads/{temp_branch_name}", branch_ref.object.sha)
        except GithubException as e:
            raise CommitRemovalError(f"Failed to create temporary branch: {str(e)}")

        # Reset the temporary branch to the base commit
        try:
            temp_ref.edit(base_commit.sha, force=True)
        except GithubException as e:
            temp_ref.delete()
            raise CommitRemovalError(f"Failed to reset temporary branch: {str(e)}")

        # Compute valid commit SHAs once for efficiency
        valid_commit_shas = {c.sha for c in commit_to_keep}

        # Cherry-pick each commit to keep in reverse order
        for i, commit in enumerate(reversed(commit_to_keep[:-1])):
            if status_callback:
                status_callback(f"Cherry-picking commit {i+1}/{len(commit_to_keep)-1}...")
                
            try:
                commit_data = repo.get_git_commit(commit.sha)
                tree = commit_data.tree
                parents = [base_commit.sha]
                
                # Handle merge commits efficiently using precomputed SHA set
                if len(commit_data.parents) > 1:
                    valid_parents = [p for p in commit_data.parents if p.sha in valid_commit_shas]
                    if valid_parents:
                        parents = [valid_parents[0].sha]
                    else:
                        continue

                new_commit = repo.create_git_commit(
                    message=commit_data.message,
                    tree=tree,
                    parents=parents
                )
                temp_ref.edit(new_commit.sha, force=True)
                base_commit = repo.get_git_commit(new_commit.sha)
            except GithubException as e:
                temp_ref.delete()
                raise CommitRemovalError(f"Failed during cherry-pick operation: {str(e)}")

        # Update the original branch to point to the new history
        try:
            branch_ref.edit(temp_ref.object.sha, force=True)
        except GithubException as e:
            temp_ref.delete()
            raise CommitRemovalError(f"Failed to update original branch: {str(e)}")

        # Delete the temporary branch
        try:
            temp_ref.delete()
        except GithubException as e:
            # Log but don't fail if cleanup fails
            print(f"Warning: Failed to delete temporary branch: {str(e)}")

    except Exception as e:
        raise CommitRemovalError(f"Failed to remove commits: {str(e)}")

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
                remove_commits(repo, branch_name, selected_commits, self.status_var.set)
                # Update UI in main thread
                self.root.after(0, lambda: self.after_commit_removal(len(selected_commits)))
            except CommitRemovalError as e:
                raise Exception(str(e))
        
        # Run in background thread
        self.run_in_thread(perform_removal, 
                        message=f"Removing {len(selected_commits)} commits...", 
                        success_message=f"Successfully removed {len(selected_commits)} commits")

    # ... rest of the class implementation ...

# Main entry point
if __name__ == "__main__":
    app = GitHubCompare()
    app.run()
