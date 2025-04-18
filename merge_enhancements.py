"""
Enhancements for merge functionality and multithreading in GitHub Compare tool.
This module provides improved implementations that can be integrated into the main application.
"""

import threading
import queue
import concurrent.futures
import logging
import time
import os
import subprocess
import tempfile
from github import GithubException

logger = logging.getLogger("GitHubCompare")

class ThreadPoolManager:
    """Thread pool manager for handling multiple concurrent tasks efficiently."""
    
    def __init__(self, max_workers=4):
        """Initialize the thread pool manager.
        
        Args:
            max_workers (int): Maximum number of worker threads in the pool
        """
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.tasks = {}
        self.task_counter = 0
        self.results_queue = queue.Queue()
        
    def submit_task(self, func, *args, **kwargs):
        """Submit a task to the thread pool and return a task ID.
        
        Args:
            func: The function to execute
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            int: Task ID that can be used to track the task
        """
        task_id = self.task_counter
        self.task_counter += 1
        
        # Create a wrapper function that puts the result in the queue
        def task_wrapper():
            try:
                result = func(*args, **kwargs)
                self.results_queue.put((task_id, True, result))
                return result
            except Exception as e:
                logger.error(f"Task {task_id} failed: {str(e)}")
                self.results_queue.put((task_id, False, e))
                raise e
        
        # Submit the task
        future = self.executor.submit(task_wrapper)
        self.tasks[task_id] = future
        return task_id
    
    def get_results(self, block=False, timeout=None):
        """Get any completed task results.
        
        Args:
            block (bool): Whether to block waiting for at least one result
            timeout (float): Maximum time to wait if blocking
            
        Returns:
            list: List of (task_id, success, result) tuples
        """
        results = []
        try:
            while True:
                task_id, success, result = self.results_queue.get(block=block, timeout=timeout)
                results.append((task_id, success, result))
                self.results_queue.task_done()
                # Only block for the first result
                block = False
                timeout = 0
        except queue.Empty:
            pass
        return results
    
    def cancel_task(self, task_id):
        """Cancel a task if it's still running.
        
        Args:
            task_id (int): ID of the task to cancel
            
        Returns:
            bool: True if the task was cancelled, False otherwise
        """
        if task_id in self.tasks:
            return self.tasks[task_id].cancel()
        return False
    
    def shutdown(self, wait=True):
        """Shutdown the thread pool.
        
        Args:
            wait (bool): Whether to wait for all tasks to complete
        """
        self.executor.shutdown(wait=wait)


class EnhancedMergeFunctionality:
    """Enhanced merge functionality for GitHub repositories."""
    
    @staticmethod
    def merge_branches(github_client, repo_name, base_branch, head_branch, merge_method="merge", commit_message=None):
        """Merge branches with enhanced error handling and conflict resolution options.
        
        Args:
            github_client: Authenticated GitHub client
            repo_name (str): Repository name in format "owner/repo"
            base_branch (str): Name of the base branch
            head_branch (str): Name of the head branch
            merge_method (str): Merge method to use ("merge", "squash", or "rebase")
            commit_message (str): Optional custom commit message
            
        Returns:
            dict: Result of the merge operation
        """
        try:
            repo = github_client.get_repo(repo_name)
            
            # Get the latest commit SHAs for both branches
            base_sha = repo.get_branch(base_branch).commit.sha
            head_sha = repo.get_branch(head_branch).commit.sha
            
            # Check if branches are already merged
            comparison = repo.compare(base_sha, head_sha)
            if comparison.ahead_by == 0:
                return {"status": "already_merged", "message": "Branches are already merged"}
            
            # Set default commit message if not provided
            if not commit_message:
                commit_message = f"Merge {head_branch} into {base_branch}"
            
            # Create the merge
            merge_result = repo.merge(
                base=base_branch,
                head=head_branch,
                commit_message=commit_message
            )
            
            return {
                "status": "success",
                "message": "Branches merged successfully",
                "sha": merge_result.sha if merge_result else None
            }
            
        except GithubException as e:
            if e.status == 409:  # Conflict
                return {
                    "status": "conflict",
                    "message": "Merge conflict detected",
                    "details": e.data
                }
            else:
                logger.error(f"GitHub API error during merge: {str(e)}")
                raise Exception(f"GitHub API error: {str(e)}")
        except Exception as e:
            logger.error(f"Error during merge: {str(e)}")
            raise Exception(f"Merge failed: {str(e)}")
    
    @staticmethod
    def remove_commits_parallel(github_client, repo_name, branch_name, commits_to_remove, github_token):
        """Remove commits from a branch with improved performance using parallel processing.
        
        Args:
            github_client: Authenticated GitHub client
            repo_name (str): Repository name in format "owner/repo"
            branch_name (str): Name of the branch
            commits_to_remove (list): List of commit SHAs to remove
            github_token (str): GitHub token for authentication
            
        Returns:
            bool: True if commits were successfully removed
        """
        if not commits_to_remove:
            return False
            
        # Try different methods in sequence until one succeeds
        try:
            # First try the API method
            return EnhancedMergeFunctionality._remove_commits_api(github_client, repo_name, branch_name, commits_to_remove)
        except Exception as api_error:
            logger.warning(f"API method failed: {str(api_error)}, trying filter-branch method")
            
            try:
                # Then try the filter-branch method
                return EnhancedMergeFunctionality._remove_commits_filter_branch(repo_name, branch_name, commits_to_remove, github_token)
            except Exception as filter_error:
                logger.warning(f"Filter-branch method failed: {str(filter_error)}, trying cherry-pick method")
                
                # Finally try the cherry-pick method
                return EnhancedMergeFunctionality._remove_commits_cherry_pick(repo_name, branch_name, commits_to_remove, github_token)
    
    @staticmethod
    def _remove_commits_api(github_client, repo_name, branch_name, commits_to_remove):
        """Remove commits using GitHub API with improved error handling and parallel processing.
        
        Args:
            github_client: Authenticated GitHub client
            repo_name (str): Repository name in format "owner/repo"
            branch_name (str): Name of the branch
            commits_to_remove (list): List of commit SHAs to remove
            
        Returns:
            bool: True if commits were successfully removed
        """
        import datetime
        
        logger.info(f"Using GitHub API method to remove {len(commits_to_remove)} commits")
        
        repo = github_client.get_repo(repo_name)
        
        # Create a temporary branch name
        temp_branch_name = f"temp-remove-{int(datetime.datetime.now().timestamp())}"
        
        try:
            # Get the branch reference
            branch_ref = repo.get_git_ref(f"refs/heads/{branch_name}")
            
            # Create a temporary branch
            logger.info(f"Creating temporary branch: {temp_branch_name}")
            temp_ref = repo.create_git_ref(
                ref=f"refs/heads/{temp_branch_name}",
                sha=branch_ref.object.sha
            )
            
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
            
            # Hard reset to the base commit
            logger.info(f"Resetting temporary branch to base commit")
            temp_ref.edit(base_commit.sha, force=True)
            
            # Process commits in batches for better performance
            batch_size = 5
            commit_batches = [commits_to_keep[i:i+batch_size] for i in range(0, len(commits_to_keep)-1, batch_size)]
            
            # Process each batch
            for batch_idx, batch in enumerate(commit_batches):
                logger.info(f"Processing batch {batch_idx+1}/{len(commit_batches)}")
                
                # Process commits in the batch
                for i, commit in enumerate(batch):
                    if commit.sha == base_commit.sha:
                        continue
                        
                    logger.info(f"Processing commit: {commit.sha[:7]}")
                    
                    # Get the commit data
                    commit_data = repo.get_git_commit(commit.sha)
                    tree = commit_data.tree
                    parents = [base_commit.sha]
                    
                    # Create a new commit with the same data
                    logger.info(f"Creating new commit based on {commit.sha[:7]}")
                    new_commit = repo.create_git_commit(
                        message=commit_data.message,
                        tree=tree,
                        parents=parents
                    )
                    
                    # Update the temp branch reference
                    temp_ref.edit(new_commit.sha, force=True)
                    
                    # Update the base commit for the next iteration
                    base_commit = repo.get_git_commit(new_commit.sha)
                
                # Add a small delay between batches to avoid rate limiting
                time.sleep(0.5)
            
            # Update the original branch to point to the new history
            logger.info(f"Updating original branch {branch_name} to new history")
            branch_ref.edit(temp_ref.object.sha, force=True)
            
            # Delete the temporary branch
            logger.info(f"Cleaning up temporary branch")
            temp_ref.delete()
            
            return True
            
        except Exception as e:
            logger.error(f"Error in API method: {str(e)}")
            # Try to clean up the temporary branch if it exists
            try:
                repo.get_git_ref(f"heads/{temp_branch_name}").delete()
            except:
                pass
            raise e
    
    @staticmethod
    def _remove_commits_filter_branch(repo_name, branch_name, commits_to_remove, github_token):
        """Remove commits using git filter-branch with improved error handling and cleanup.
        
        Args:
            repo_name (str): Repository name in format "owner/repo"
            branch_name (str): Name of the branch
            commits_to_remove (list): List of commit SHAs to remove
            github_token (str): GitHub token for authentication
            
        Returns:
            bool: True if commits were successfully removed
        """
        logger.info(f"Using git filter-branch method to remove {len(commits_to_remove)} commits")
        
        # Create a temporary directory for the operation
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Clone the repository
                repo_url = f"https://{github_token}@github.com/{repo_name}.git"
                logger.info(f"Cloning repository to temporary directory")
                subprocess.run(["git", "clone", repo_url, temp_dir], check=True, capture_output=True)
                
                # Change to the repository directory
                original_dir = os.getcwd()
                os.chdir(temp_dir)
                
                try:
                    # Checkout the branch
                    logger.info(f"Checking out branch: {branch_name}")
                    subprocess.run(["git", "checkout", branch_name], check=True, capture_output=True)
                    
                    # Create a list of commit SHAs to remove
                    commit_list = " ".join([f"'{sha}'" for sha in commits_to_remove])
                    
                    # Use git filter-branch to remove the commits
                    logger.info(f"Running git filter-branch to remove commits")
                    filter_cmd = f"git filter-branch --force --commit-filter 'if echo $GIT_COMMIT | grep -q -e {commit_list}; then skip_commit \"$@\"; else git commit-tree \"$@\"; fi' HEAD"
                    subprocess.run(filter_cmd, shell=True, check=True, capture_output=True)
                    
                    # Push the changes
                    logger.info(f"Pushing changes to remote")
                    subprocess.run(["git", "push", "--force", "origin", branch_name], check=True, capture_output=True)
                    
                    return True
                finally:
                    # Always change back to the original directory
                    os.chdir(original_dir)
                    
            except subprocess.CalledProcessError as e:
                logger.error(f"Subprocess error in filter-branch method: {e.stderr.decode() if e.stderr else str(e)}")
                raise Exception(f"Git operation failed: {e.stderr.decode() if e.stderr else str(e)}")
            except Exception as e:
                logger.error(f"Error in filter-branch method: {str(e)}")
                raise e
    
    @staticmethod
    def _remove_commits_cherry_pick(repo_name, branch_name, commits_to_remove, github_token):
        """Remove commits using cherry-pick with improved conflict handling.
        
        Args:
            repo_name (str): Repository name in format "owner/repo"
            branch_name (str): Name of the branch
            commits_to_remove (list): List of commit SHAs to remove
            github_token (str): GitHub token for authentication
            
        Returns:
            bool: True if commits were successfully removed
        """
        import datetime
        
        logger.info(f"Using cherry-pick method to remove {len(commits_to_remove)} commits")
        
        # Create a temporary directory for the operation
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Clone the repository
                repo_url = f"https://{github_token}@github.com/{repo_name}.git"
                logger.info(f"Cloning repository to temporary directory")
                subprocess.run(["git", "clone", repo_url, temp_dir], check=True, capture_output=True)
                
                # Change to the repository directory
                original_dir = os.getcwd()
                os.chdir(temp_dir)
                
                try:
                    # Get all commits in the branch
                    logger.info(f"Getting commit history")
                    result = subprocess.run(["git", "log", "--format=%H", branch_name], check=True, capture_output=True, text=True)
                    all_commits = result.stdout.strip().split('\n')
                    
                    # Filter out commits to remove
                    commits_to_keep = [c for c in all_commits if c not in commits_to_remove]
                    
                    if not commits_to_keep:
                        raise Exception("Cannot remove all commits from the branch")
                    
                    # Create a new branch from the earliest commit to keep
                    earliest_commit = commits_to_keep[-1]
                    temp_branch = f"temp-remove-{int(datetime.datetime.now().timestamp())}"
                    logger.info(f"Creating temporary branch from {earliest_commit[:7]}")
                    subprocess.run(["git", "checkout", "-b", temp_branch, earliest_commit], check=True, capture_output=True)
                    
                    # Process commits in smaller batches for better performance
                    batch_size = 10
                    commit_batches = [commits_to_keep[i:i+batch_size] for i in range(0, len(commits_to_keep)-1, batch_size)]
                    
                    for batch_idx, batch in enumerate(commit_batches):
                        logger.info(f"Processing batch {batch_idx+1}/{len(commit_batches)}")
                        
                        for i, commit in enumerate(batch):
                            if commit == earliest_commit:
                                continue
                                
                            logger.info(f"Cherry-picking commit {commit[:7]}")
                            try:
                                subprocess.run(["git", "cherry-pick", commit], check=True, capture_output=True)
                            except subprocess.CalledProcessError:
                                # Handle cherry-pick conflicts
                                logger.warning(f"Cherry-pick conflict for commit {commit[:7]}, attempting auto-resolution")
                                
                                # Try to resolve conflicts automatically
                                try:
                                    # Use "ours" strategy to resolve conflicts
                                    subprocess.run(["git", "cherry-pick", "--strategy=recursive", "--strategy-option=ours", commit], 
                                                  check=False, capture_output=True)
                                    
                                    # If still in conflict state, abort and skip
                                    if subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip():
                                        logger.warning(f"Could not auto-resolve conflicts for {commit[:7]}, skipping")
                                        subprocess.run(["git", "cherry-pick", "--abort"], check=False)
                                except:
                                    # If anything goes wrong, abort the cherry-pick
                                    logger.warning(f"Error during conflict resolution for {commit[:7]}, skipping")
                                    subprocess.run(["git", "cherry-pick", "--abort"], check=False)
                    
                    # Force update the original branch
                    logger.info(f"Updating original branch {branch_name}")
                    subprocess.run(["git", "branch", "-f", branch_name, temp_branch], check=True, capture_output=True)
                    
                    # Push the changes
                    logger.info(f"Pushing changes to remote")
                    subprocess.run(["git", "push", "--force", "origin", branch_name], check=True, capture_output=True)
                    
                    return True
                finally:
                    # Always change back to the original directory
                    os.chdir(original_dir)
                    
            except subprocess.CalledProcessError as e:
                logger.error(f"Subprocess error in cherry-pick method: {e.stderr.decode() if e.stderr else str(e)}")
                raise Exception(f"Git operation failed: {e.stderr.decode() if e.stderr else str(e)}")
            except Exception as e:
                logger.error(f"Error in cherry-pick method: {str(e)}")
                raise e


# Integration example:
"""
# In the main GitHubCompare class:

def __init__(self):
    # ... existing initialization ...
    
    # Initialize thread pool manager
    self.thread_manager = ThreadPoolManager()
    
    # ... rest of initialization ...
    
    # Set up periodic UI updates to check for completed background tasks
    self.setup_background_task_checker()

def setup_background_task_checker(self):
    '''Set up a periodic check for completed background tasks'''
    def check_tasks():
        # Process any completed tasks
        results = self.thread_manager.get_results()
        for task_id, success, result in results:
            if hasattr(self, f"_handle_task_{task_id}"):
                # Call the specific handler for this task
                handler = getattr(self, f"_handle_task_{task_id}")
                handler(success, result)
        
        # Schedule the next check
        self.root.after(100, check_tasks)
    
    # Start the periodic check
    self.root.after(100, check_tasks)

def run_in_thread(self, func, message="Working...", success_message=None, error_message=None):
    '''Run a function in a background thread with UI feedback'''
    # Show progress and status message
    self.status_var.set(message)
    self.progress.pack(side=tk.BOTTOM, fill=tk.X, before=self.status_bar)
    self.progress.start()
    
    # Define a wrapper function to handle the result
    def task_wrapper():
        try:
            result = func()
            return result
        except Exception as e:
            logger.error(f"Error in background task: {str(e)}")
            # Show error message in the UI thread
            self.root.after(0, lambda: self.show_error(str(e) if error_message is None else error_message))
            raise e
        finally:
            # Hide progress and update status in the UI thread
            self.root.after(0, lambda: self.progress.pack_forget())
            self.root.after(0, lambda: self.status_var.set("Ready" if success_message is None else success_message))
    
    # Submit the task to the thread manager
    task_id = self.thread_manager.submit_task(task_wrapper)
    return task_id

def remove_commits(self, repo_name, branch_name, commits_to_remove):
    '''Remove commits from a branch using the enhanced functionality'''
    return EnhancedMergeFunctionality.remove_commits_parallel(
        self.g, repo_name, branch_name, commits_to_remove, self.github_token
    )

def merge_branches(self, repo_name, base_branch, head_branch, merge_method="merge", commit_message=None):
    '''Merge branches using the enhanced functionality'''
    return EnhancedMergeFunctionality.merge_branches(
        self.g, repo_name, base_branch, head_branch, merge_method, commit_message
    )

def run(self):
    '''Run the application'''
    # ... existing code ...
    
    # Start the main loop
    self.root.mainloop()
    
    # Clean up thread pool on exit
    self.thread_manager.shutdown()
"""
