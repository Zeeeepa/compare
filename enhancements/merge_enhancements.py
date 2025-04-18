import os
import tempfile
import subprocess
import logging
import datetime
import time
import threading
from github import Github, GithubException

# Set up logging
logger = logging.getLogger("MergeEnhancements")

class MergeManager:
    """Enhanced merge functionality for GitHub repositories"""
    
    def __init__(self, github_token, root_widget=None):
        self.github_token = github_token
        self.g = Github(github_token)
        self.root_widget = root_widget
        self.lock = threading.Lock()
        
    def merge_commit(self, repo_name, branch_name, commit_sha, 
                     merge_strategy="merge", 
                     message=None, 
                     batch_size=10):
        """
        Merge a specific commit with enhanced error handling and performance
        
        Args:
            repo_name: Full repository name (owner/repo)
            branch_name: Target branch name
            commit_sha: SHA of the commit to merge
            merge_strategy: Strategy to use (merge, squash, rebase)
            message: Custom commit message
            batch_size: Number of commits to process in a batch
        
        Returns:
            dict: Result of the merge operation
        """
        logger.info(f"Merging commit {commit_sha[:7]} into {repo_name}:{branch_name} using {merge_strategy} strategy")
        
        # Default commit message if not provided
        if not message:
            message = f"Merge commit {commit_sha[:7]} using {merge_strategy} strategy"
        
        # Try GitHub API method first
        try:
            return self._merge_api_method(repo_name, branch_name, commit_sha, 
                                         merge_strategy, message)
        except Exception as e:
            logger.error(f"GitHub API merge failed: {str(e)}")
            
            # Try Git CLI method as fallback
            try:
                return self._merge_git_method(repo_name, branch_name, commit_sha, 
                                             merge_strategy, message, batch_size)
            except Exception as e2:
                logger.error(f"Git CLI merge failed: {str(e2)}")
                
                # Try cherry-pick method as final fallback
                try:
                    return self._merge_cherry_pick_method(repo_name, branch_name, commit_sha, message)
                except Exception as e3:
                    logger.error(f"Cherry-pick merge failed: {str(e3)}")
                    raise Exception(f"All merge methods failed: {str(e)}, {str(e2)}, {str(e3)}")
    
    def _merge_api_method(self, repo_name, branch_name, commit_sha, merge_strategy, message):
        """Merge using GitHub API"""
        repo = self.g.get_repo(repo_name)
        
        # Create a temporary branch for the operation
        temp_branch = f"temp-merge-{commit_sha[:7]}-{int(datetime.datetime.now().timestamp())}"
        logger.info(f"Creating temporary branch: {temp_branch}")
        
        # Get the current branch reference
        branch_ref = repo.get_git_ref(f"heads/{branch_name}")
        
        # Create the temporary branch
        repo.create_git_ref(f"refs/heads/{temp_branch}", branch_ref.object.sha)
        
        try:
            # Get the commit to merge
            commit = repo.get_commit(commit_sha)
            
            # Merge the commit into the temporary branch
            if merge_strategy == "merge":
                merge_result = repo.merge(temp_branch, commit_sha, message)
            elif merge_strategy == "squash":
                # For squash, we need to use a different approach
                base_commit = repo.get_git_commit(branch_ref.object.sha)
                tree = repo.get_git_tree(commit.commit.tree.sha)
                squash_commit = repo.create_git_commit(message, tree, [base_commit])
                temp_ref = repo.get_git_ref(f"heads/{temp_branch}")
                temp_ref.edit(squash_commit.sha, force=True)
                merge_result = {"sha": squash_commit.sha}
            elif merge_strategy == "rebase":
                # For rebase, we need to cherry-pick the commit
                cherry_pick = repo.merge(temp_branch, commit_sha, message)
                merge_result = {"sha": cherry_pick.sha}
            else:
                raise ValueError(f"Unsupported merge strategy: {merge_strategy}")
            
            # Merge the temporary branch back to the target branch
            merge_to_target = repo.merge(branch_name, temp_branch, 
                                        f"Merge {merge_strategy} of {commit_sha[:7]}")
            
            # Clean up the temporary branch
            repo.get_git_ref(f"heads/{temp_branch}").delete()
            
            return {
                "success": True,
                "sha": merge_to_target.sha,
                "message": f"Successfully merged commit {commit_sha[:7]} using {merge_strategy} strategy",
                "method": "api"
            }
        except Exception as e:
            # Clean up the temporary branch in case of error
            try:
                repo.get_git_ref(f"heads/{temp_branch}").delete()
            except:
                pass
            raise e
    
    def _merge_git_method(self, repo_name, branch_name, commit_sha, merge_strategy, message, batch_size):
        """Merge using Git CLI commands"""
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
                
                # Create a temporary branch
                temp_branch = f"temp-merge-{commit_sha[:7]}-{int(datetime.datetime.now().timestamp())}"
                logger.info(f"Creating temporary branch: {temp_branch}")
                subprocess.run(["git", "checkout", "-b", temp_branch], check=True, capture_output=True)
                
                # Perform the merge based on strategy
                if merge_strategy == "merge":
                    logger.info(f"Merging commit {commit_sha[:7]} with merge strategy")
                    subprocess.run(["git", "merge", commit_sha, "--no-ff", "-m", message], 
                                  check=True, capture_output=True)
                elif merge_strategy == "squash":
                    logger.info(f"Merging commit {commit_sha[:7]} with squash strategy")
                    subprocess.run(["git", "merge", "--squash", commit_sha], 
                                  check=True, capture_output=True)
                    subprocess.run(["git", "commit", "-m", message], 
                                  check=True, capture_output=True)
                elif merge_strategy == "rebase":
                    logger.info(f"Merging commit {commit_sha[:7]} with rebase strategy")
                    subprocess.run(["git", "cherry-pick", commit_sha], 
                                  check=True, capture_output=True)
                else:
                    raise ValueError(f"Unsupported merge strategy: {merge_strategy}")
                
                # Get the new commit SHA
                result = subprocess.run(["git", "rev-parse", "HEAD"], 
                                      check=True, capture_output=True, text=True)
                new_sha = result.stdout.strip()
                
                # Checkout the original branch
                subprocess.run(["git", "checkout", branch_name], check=True, capture_output=True)
                
                # Merge the temporary branch
                subprocess.run(["git", "merge", temp_branch, "--no-ff", "-m", 
                              f"Merge {merge_strategy} of {commit_sha[:7]}"], 
                              check=True, capture_output=True)
                
                # Push the changes
                logger.info(f"Pushing changes to remote")
                subprocess.run(["git", "push", "origin", branch_name], check=True, capture_output=True)
                
                return {
                    "success": True,
                    "sha": new_sha,
                    "message": f"Successfully merged commit {commit_sha[:7]} using {merge_strategy} strategy",
                    "method": "git"
                }
            except Exception as e:
                raise e
    
    def _merge_cherry_pick_method(self, repo_name, branch_name, commit_sha, message):
        """Merge using cherry-pick as a fallback method"""
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
                
                # Cherry-pick the commit
                logger.info(f"Cherry-picking commit {commit_sha[:7]}")
                subprocess.run(["git", "cherry-pick", commit_sha], check=True, capture_output=True)
                
                # Get the new commit SHA
                result = subprocess.run(["git", "rev-parse", "HEAD"], 
                                      check=True, capture_output=True, text=True)
                new_sha = result.stdout.strip()
                
                # Push the changes
                logger.info(f"Pushing changes to remote")
                subprocess.run(["git", "push", "origin", branch_name], check=True, capture_output=True)
                
                return {
                    "success": True,
                    "sha": new_sha,
                    "message": f"Successfully cherry-picked commit {commit_sha[:7]}",
                    "method": "cherry-pick"
                }
            except Exception as e:
                raise e
    
    def check_for_conflicts(self, repo_name, branch_name, commit_sha):
        """Check if merging a commit would cause conflicts"""
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
                
                # Try to merge the commit without committing
                try:
                    subprocess.run(["git", "merge", "--no-commit", "--no-ff", commit_sha], 
                                  check=True, capture_output=True)
                    
                    # If we get here, there are no conflicts
                    # Abort the merge to clean up
                    subprocess.run(["git", "merge", "--abort"], check=True, capture_output=True)
                    
                    return {
                        "has_conflicts": False,
                        "message": "No conflicts detected"
                    }
                except subprocess.CalledProcessError as e:
                    # Check if the error is due to conflicts
                    if "CONFLICT" in e.stderr.decode():
                        # Get the list of conflicting files
                        result = subprocess.run(["git", "diff", "--name-only", "--diff-filter=U"], 
                                              check=False, capture_output=True, text=True)
                        conflicting_files = result.stdout.strip().split('\n')
                        
                        # Abort the merge to clean up
                        subprocess.run(["git", "merge", "--abort"], check=False, capture_output=True)
                        
                        return {
                            "has_conflicts": True,
                            "conflicting_files": conflicting_files,
                            "message": f"Conflicts detected in {len(conflicting_files)} files"
                        }
                    else:
                        raise e
            except Exception as e:
                raise e
    
    def auto_resolve_conflicts(self, repo_name, branch_name, commit_sha, strategy="ours"):
        """
        Attempt to automatically resolve merge conflicts
        
        Args:
            repo_name: Full repository name (owner/repo)
            branch_name: Target branch name
            commit_sha: SHA of the commit to merge
            strategy: Conflict resolution strategy ('ours', 'theirs', or 'union')
        
        Returns:
            dict: Result of the conflict resolution
        """
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
                
                # Try to merge the commit
                try:
                    subprocess.run(["git", "merge", "--no-commit", "--no-ff", commit_sha], 
                                  check=True, capture_output=True)
                    
                    # If we get here, there are no conflicts, so just commit
                    subprocess.run(["git", "commit", "-m", f"Merge {commit_sha[:7]} without conflicts"], 
                                  check=True, capture_output=True)
                except subprocess.CalledProcessError:
                    # Get the list of conflicting files
                    result = subprocess.run(["git", "diff", "--name-only", "--diff-filter=U"], 
                                          check=False, capture_output=True, text=True)
                    conflicting_files = result.stdout.strip().split('\n')
                    
                    # Resolve conflicts based on strategy
                    if strategy == "ours":
                        for file in conflicting_files:
                            if file:  # Skip empty lines
                                subprocess.run(["git", "checkout", "--ours", file], 
                                              check=True, capture_output=True)
                                subprocess.run(["git", "add", file], check=True, capture_output=True)
                    elif strategy == "theirs":
                        for file in conflicting_files:
                            if file:  # Skip empty lines
                                subprocess.run(["git", "checkout", "--theirs", file], 
                                              check=True, capture_output=True)
                                subprocess.run(["git", "add", file], check=True, capture_output=True)
                    elif strategy == "union":
                        # This is more complex and would require parsing the conflict markers
                        # For simplicity, we'll use the merge-file command with the union option
                        for file in conflicting_files:
                            if file:  # Skip empty lines
                                # Get the base, ours, and theirs versions
                                base = f"{file}.base"
                                ours = f"{file}.ours"
                                theirs = f"{file}.theirs"
                                
                                # Extract the versions
                                subprocess.run(["git", "show", ":1:" + file, ">", base], 
                                              shell=True, check=False)
                                subprocess.run(["git", "show", ":2:" + file, ">", ours], 
                                              shell=True, check=False)
                                subprocess.run(["git", "show", ":3:" + file, ">", theirs], 
                                              shell=True, check=False)
                                
                                # Merge with union strategy
                                subprocess.run(["git", "merge-file", "-p", "--union", 
                                              ours, base, theirs, ">", file], 
                                              shell=True, check=False)
                                
                                # Add the resolved file
                                subprocess.run(["git", "add", file], check=True, capture_output=True)
                    else:
                        raise ValueError(f"Unsupported conflict resolution strategy: {strategy}")
                    
                    # Commit the resolved conflicts
                    subprocess.run(["git", "commit", "-m", 
                                  f"Merge {commit_sha[:7]} with auto-resolved conflicts using {strategy} strategy"], 
                                  check=True, capture_output=True)
                
                # Push the changes
                logger.info(f"Pushing changes to remote")
                subprocess.run(["git", "push", "origin", branch_name], check=True, capture_output=True)
                
                # Get the new commit SHA
                result = subprocess.run(["git", "rev-parse", "HEAD"], 
                                      check=True, capture_output=True, text=True)
                new_sha = result.stdout.strip()
                
                return {
                    "success": True,
                    "sha": new_sha,
                    "message": f"Successfully merged {commit_sha[:7]} with auto-resolved conflicts",
                    "strategy": strategy
                }
            except Exception as e:
                raise e
