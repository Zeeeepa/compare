import logging
import os
import datetime
import time
import tempfile
import subprocess

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.expanduser("~"), ".github_compare.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GitHubCompare")

def remove_selected_commits(self):
    """Remove selected commits from the branch with improved error handling and fallback methods"""
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
        f"Are you sure you want to remove {len(selected_commits)} commits from {branch_name}?\n\n"
        "This operation will rewrite the branch history and cannot be undone."
    )
    
    if not response:
        return
    
    def perform_removal():
        logger.info(f"Starting commit removal process for {len(selected_commits)} commits from {branch_name}")
        
        # Track failed commits for retry
        failed_commits = []
        success = False
        error_message = ""
        
        try:
            # Method 1: GitHub API approach
            logger.info("Attempting commit removal using GitHub API")
            success = self._remove_commits_api_method(repo_name, branch_name, selected_commits)
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"GitHub API method failed: {error_message}")
            failed_commits = selected_commits
            
            try:
                # Method 2: Git filter-branch fallback
                logger.info("Attempting commit removal using git filter-branch fallback")
                success = self._remove_commits_filter_branch(repo_name, branch_name, failed_commits)
                failed_commits = []
                
            except Exception as e2:
                error_message = f"{error_message}\nFilter-branch fallback failed: {str(e2)}"
                logger.error(f"Filter-branch fallback failed: {str(e2)}")
                
                try:
                    # Method 3: Cherry-pick fallback
                    logger.info("Attempting commit removal using cherry-pick fallback")
                    success = self._remove_commits_cherry_pick(repo_name, branch_name, failed_commits)
                    failed_commits = []
                    
                except Exception as e3:
                    error_message = f"{error_message}\nCherry-pick fallback failed: {str(e3)}"
                    logger.error(f"Cherry-pick fallback failed: {str(e3)}")
        
        # Update UI in main thread
        if success:
            self.root.after(0, lambda: self.after_commit_removal(len(selected_commits)))
            logger.info(f"Successfully removed {len(selected_commits)} commits")
        else:
            if failed_commits:
                error_msg = f"Failed to remove commits: {failed_commits}\nError details: {error_message}"
                logger.error(error_msg)
                self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to remove commits: {error_message}"))
    
    # Run in background thread
    self.run_in_thread(perform_removal, 
                    message=f"Removing {len(selected_commits)} commits...", 
                    success_message=f"Successfully removed {len(selected_commits)} commits")

def _remove_commits_api_method(self, repo_name, branch_name, commits_to_remove):
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
        
        # Hard reset to the base commit
        logger.info(f"Resetting temporary branch to base commit")
        temp_ref.edit(base_commit.sha, force=True)
        
        # Cherry-pick each commit to keep in reverse order (oldest to newest)
        logger.info(f"Cherry-picking {len(commits_to_keep)-1} commits to temporary branch")
        
        for i, commit in enumerate(reversed(commits_to_keep[:-1])):  # Skip the base commit
            logger.info(f"Processing commit {i+1}/{len(commits_to_keep)-1}: {commit.sha[:7]}")
            
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
            
            # Add a small delay to avoid rate limiting
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

def _remove_commits_filter_branch(self, repo_name, branch_name, commits_to_remove):
    """Remove commits using git filter-branch as a fallback method"""
    logger.info(f"Using git filter-branch method to remove {len(commits_to_remove)} commits")
    
    # Create a temporary directory for the operation
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Clone the repository
            repo_url = f"https://{self.github_token}@github.com/{repo_name}.git"
            logger.info(f"Cloning repository to temporary directory")
            subprocess.run(["git", "clone", repo_url, temp_dir], check=True, capture_output=True)
            
            # Change to the repository directory
            os.chdir(temp_dir)
            
            # Checkout the branch
            logger.info(f"Checking out branch: {branch_name}")
            subprocess.run(["git", "checkout", branch_name], check=True, capture_output=True)
            
            # Create a list of commit SHAs to remove
            commit_list = " ".join(commits_to_remove)
            
            # Use git filter-branch to remove the commits
            logger.info(f"Running git filter-branch to remove commits")
            filter_cmd = f"git filter-branch --force --commit-filter 'if echo $GIT_COMMIT | grep -q -e {commit_list}; then skip_commit \"$@\"; else git commit-tree \"$@\"; fi' HEAD"
            subprocess.run(filter_cmd, shell=True, check=True, capture_output=True)
            
            # Push the changes
            logger.info(f"Pushing changes to remote")
            subprocess.run(["git", "push", "--force", "origin", branch_name], check=True, capture_output=True)
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Subprocess error in filter-branch method: {e.stderr.decode()}")
            raise Exception(f"Git operation failed: {e.stderr.decode()}")
        except Exception as e:
            logger.error(f"Error in filter-branch method: {str(e)}")
            raise e

def _remove_commits_cherry_pick(self, repo_name, branch_name, commits_to_remove):
    """Remove commits using cherry-pick as a fallback method"""
    logger.info(f"Using cherry-pick method to remove {len(commits_to_remove)} commits")
    
    # Create a temporary directory for the operation
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Clone the repository
            repo_url = f"https://{self.github_token}@github.com/{repo_name}.git"
            logger.info(f"Cloning repository to temporary directory")
            subprocess.run(["git", "clone", repo_url, temp_dir], check=True, capture_output=True)
            
            # Change to the repository directory
            os.chdir(temp_dir)
            
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
            
            # Cherry-pick each commit to keep
            logger.info(f"Cherry-picking {len(commits_to_keep)-1} commits")
            for i, commit in enumerate(reversed(commits_to_keep[:-1])):
                logger.info(f"Cherry-picking commit {i+1}/{len(commits_to_keep)-1}: {commit[:7]}")
                try:
                    subprocess.run(["git", "cherry-pick", commit], check=True, capture_output=True)
                except subprocess.CalledProcessError:
                    # Handle cherry-pick conflicts
                    logger.warning(f"Cherry-pick conflict for commit {commit[:7]}, skipping")
                    subprocess.run(["git", "cherry-pick", "--abort"], check=False)
            
            # Force update the original branch
            logger.info(f"Updating original branch {branch_name}")
            subprocess.run(["git", "branch", "-f", branch_name, temp_branch], check=True, capture_output=True)
            
            # Push the changes
            logger.info(f"Pushing changes to remote")
            subprocess.run(["git", "push", "--force", "origin", branch_name], check=True, capture_output=True)
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Subprocess error in cherry-pick method: {e.stderr.decode() if e.stderr else str(e)}")
            raise Exception(f"Git operation failed: {e.stderr.decode() if e.stderr else str(e)}")
        except Exception as e:
            logger.error(f"Error in cherry-pick method: {str(e)}")
            raise e

def after_commit_removal(self, num_removed):
    """Update after commit removal"""
    # Refresh the commit list
    self.fetch_commit_list()
    
    # Show success message
    messagebox.showinfo("Success", f"Successfully removed {num_removed} commits")
