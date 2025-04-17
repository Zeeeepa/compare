import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import webbrowser
import threading
import json
import datetime
import logging
import time
from github import Github, GithubException
from functools import partial

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('GitHubCompare')

class GitHubCompare:
    def remove_selected_commits(self):
        """Remove selected commits from the branch with improved error handling and logging"""
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
            temp_branch_name = None
            temp_ref = None
            max_retries = 3
            retry_delay = 1  # seconds
            
            try:
                repo = self.g.get_repo(repo_name)
                logger.info(f"Starting commit removal process for {repo_name}/{branch_name}")
                
                # Get the current branch reference
                try:
                    branch_ref = repo.get_git_ref(f"heads/{branch_name}")
                    logger.info(f"Retrieved branch reference for {branch_name}")
                except GithubException as e:
                    logger.error(f"Failed to get branch reference: {e}")
                    raise Exception(f"Branch {branch_name} not found or inaccessible")
                
                # Create a temporary branch for the operation
                temp_branch_name = f"temp-remove-commits-{int(datetime.datetime.now().timestamp())}"
                try:
                    temp_ref = repo.create_git_ref(f"refs/heads/{temp_branch_name}", branch_ref.object.sha)
                    logger.info(f"Created temporary branch {temp_branch_name}")
                except GithubException as e:
                    logger.error(f"Failed to create temporary branch: {e}")
                    raise Exception("Failed to create temporary branch for commit removal")
                
                # Get all commits in chronological order with retry mechanism
                all_commits = None
                for attempt in range(max_retries):
                    try:
                        all_commits = list(repo.get_commits(sha=branch_name))
                        logger.info(f"Retrieved {len(all_commits)} commits from branch")
                        break
                    except GithubException as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"Attempt {attempt + 1} failed to get commits: {e}")
                            time.sleep(retry_delay)
                        else:
                            logger.error(f"Failed to get commits after {max_retries} attempts: {e}")
                            raise Exception("Failed to retrieve commits from branch")
                
                # Filter out selected commits to remove
                commit_to_keep = [c for c in all_commits if c.sha not in selected_commits]
                
                if not commit_to_keep:
                    logger.error("Attempted to remove all commits from branch")
                    raise Exception("Cannot remove all commits from the branch")
                    
                # Find the oldest commit to keep
                base_commit = commit_to_keep[-1]
                logger.info(f"Using {base_commit.sha[:7]} as base commit")
                
                # Hard reset to the base commit
                try:
                    temp_ref.edit(base_commit.sha, force=True)
                    logger.info(f"Reset temporary branch to {base_commit.sha[:7]}")
                except GithubException as e:
                    logger.error(f"Failed to reset temporary branch: {e}")
                    raise Exception("Failed to reset branch to base commit")
                
                # Cherry-pick each commit to keep in reverse order
                for commit in reversed(commit_to_keep[:-1]):
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
                        
                        # Update the temp branch reference
                        temp_ref.edit(new_commit.sha, force=True)
                        logger.info(f"Cherry-picked commit {commit.sha[:7]}")
                        
                        # Update the base commit for the next iteration
                        base_commit = repo.get_git_commit(new_commit.sha)
                        
                    except GithubException as e:
                        logger.error(f"Failed to cherry-pick commit {commit.sha[:7]}: {e}")
                        raise Exception(f"Failed to cherry-pick commit {commit.sha[:7]}")
                
                # Update the original branch to point to the new history
                try:
                    branch_ref.edit(temp_ref.object.sha, force=True)
                    logger.info("Updated original branch to new history")
                except GithubException as e:
                    logger.error(f"Failed to update original branch: {e}")
                    raise Exception("Failed to update branch with new history")
                
                # Delete the temporary branch
                try:
                    temp_ref.delete()
                    logger.info(f"Deleted temporary branch {temp_branch_name}")
                except GithubException as e:
                    logger.warning(f"Failed to delete temporary branch: {e}")
                    # Don't raise an exception here as the main operation succeeded
                
                # Update UI in main thread
                self.root.after(0, lambda: self.after_commit_removal(len(selected_commits)))
                logger.info("Commit removal completed successfully")
                
            except Exception as e:
                logger.error(f"Commit removal failed: {str(e)}")
                
                # Cleanup: Try to delete temporary branch if it exists
                if temp_ref:
                    try:
                        temp_ref.delete()
                        logger.info(f"Cleaned up temporary branch {temp_branch_name}")
                    except:
                        logger.warning(f"Failed to clean up temporary branch {temp_branch_name}")
                
                # Provide detailed error message with context
                error_msg = str(e)
                if "Failed to get branch reference" in error_msg:
                    error_msg += "\nPlease verify the branch exists and you have access to it."
                elif "Failed to create temporary branch" in error_msg:
                    error_msg += "\nPlease verify you have write permissions to the repository."
                elif "Failed to cherry-pick commit" in error_msg:
                    error_msg += "\nThere may be conflicts that need manual resolution."
                
                raise Exception(f"Failed to remove commits: {error_msg}")
        
        # Run in background thread
        self.run_in_thread(perform_removal, 
                        message=f"Removing {len(selected_commits)} commits...", 
                        success_message=f"Successfully removed {len(selected_commits)} commits")
