"""
Enhanced merge operations for GitHub Compare tool.
This module provides advanced merging capabilities.
"""
import logging
import os
import tempfile
import subprocess
import time
from typing import Dict, List, Optional, Tuple, Union
from github import Github, GithubException, Repository, PullRequest

logger = logging.getLogger("GitHubCompare.MergeOperations")

class MergeStrategy:
    """Enum-like class for merge strategies."""
    MERGE = "merge"
    SQUASH = "squash"
    REBASE = "rebase"

class MergeOperations:
    """Provides enhanced merge operations for GitHub repositories."""
    
    def __init__(self, github_client: Github):
        """
        Initialize merge operations.
        
        Args:
            github_client: Authenticated GitHub client
        """
        self.github = github_client
        
    def create_pull_request(self, repo_name: str, title: str, body: str, 
                           head: str, base: str, draft: bool = False,
                           reviewers: List[str] = None) -> PullRequest.PullRequest:
        """
        Create a pull request with enhanced options.
        
        Args:
            repo_name: Full name of the repository (owner/repo)
            title: Title of the pull request
            body: Body/description of the pull request
            head: Head branch (can be in the format username:branch)
            base: Base branch to merge into
            draft: Whether to create a draft PR
            reviewers: List of GitHub usernames to request reviews from
            
        Returns:
            The created pull request
        """
        logger.info(f"Creating pull request in {repo_name}: {title}")
        
        # Get the repository
        repo = self.github.get_repo(repo_name)
        
        # Parse head branch if it contains a colon
        if ":" in head:
            # It's a cross-repository PR
            head_branch = head
        else:
            # It's a PR within the same repository
            head_branch = head
            
        # Create the pull request
        try:
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base,
                draft=draft
            )
            
            logger.info(f"Pull request created: #{pr.number}")
            
            # Request reviews if specified
            if reviewers:
                try:
                    pr.create_review_request(reviewers=reviewers)
                    logger.info(f"Requested reviews from: {', '.join(reviewers)}")
                except GithubException as e:
                    logger.warning(f"Failed to request reviews: {str(e)}")
                    
            return pr
            
        except GithubException as e:
            logger.error(f"Failed to create pull request: {str(e)}")
            raise
            
    def check_for_merge_conflicts(self, repo_name: str, base: str, head: str) -> Tuple[bool, Optional[List[str]]]:
        """
        Check if there would be merge conflicts between two branches.
        
        Args:
            repo_name: Full name of the repository (owner/repo)
            base: Base branch
            head: Head branch
            
        Returns:
            Tuple of (has_conflicts, conflicting_files)
        """
        logger.info(f"Checking for merge conflicts between {base} and {head} in {repo_name}")
        
        # Create a temporary directory for the operation
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Get the repository
                repo = self.github.get_repo(repo_name)
                
                # Get the token for authentication
                token = self.github._Github__requester._Requester__auth.token
                
                # Clone the repository
                repo_url = f"https://{token}@github.com/{repo_name}.git"
                logger.info(f"Cloning repository to temporary directory")
                subprocess.run(["git", "clone", repo_url, temp_dir], 
                              check=True, capture_output=True)
                
                # Change to the repository directory
                os.chdir(temp_dir)
                
                # Fetch both branches
                subprocess.run(["git", "fetch", "origin", base, head], 
                              check=True, capture_output=True)
                
                # Try to merge the branches in memory (don't actually commit)
                result = subprocess.run(
                    ["git", "merge-tree", f"origin/{base}", f"origin/{head}"],
                    capture_output=True, text=True
                )
                
                # Check if there are conflicts
                if "changed in both" in result.stdout:
                    # Parse the output to find conflicting files
                    conflicting_files = []
                    for line in result.stdout.splitlines():
                        if "changed in both" in line:
                            parts = line.split(":")
                            if len(parts) > 1:
                                conflicting_files.append(parts[0].strip())
                    
                    logger.info(f"Found merge conflicts in files: {conflicting_files}")
                    return True, conflicting_files
                else:
                    logger.info("No merge conflicts found")
                    return False, None
                    
            except subprocess.CalledProcessError as e:
                logger.error(f"Git operation failed: {e.stderr.decode() if e.stderr else str(e)}")
                raise Exception(f"Failed to check for merge conflicts: {str(e)}")
            except Exception as e:
                logger.error(f"Error checking for merge conflicts: {str(e)}")
                raise
                
    def merge_pull_request(self, repo_name: str, pr_number: int, 
                          strategy: str = MergeStrategy.MERGE,
                          commit_title: str = None,
                          commit_message: str = None) -> bool:
        """
        Merge a pull request with the specified strategy.
        
        Args:
            repo_name: Full name of the repository (owner/repo)
            pr_number: Pull request number
            strategy: Merge strategy (merge, squash, rebase)
            commit_title: Title for the merge commit
            commit_message: Message for the merge commit
            
        Returns:
            True if the merge was successful
        """
        logger.info(f"Merging pull request #{pr_number} in {repo_name} with strategy: {strategy}")
        
        # Get the repository and pull request
        repo = self.github.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        # Check if the PR is mergeable
        if not pr.mergeable:
            logger.error(f"Pull request #{pr_number} is not mergeable")
            raise Exception(f"Pull request #{pr_number} is not mergeable")
            
        try:
            if strategy == MergeStrategy.MERGE:
                result = pr.merge(
                    commit_title=commit_title,
                    commit_message=commit_message,
                    merge_method="merge"
                )
            elif strategy == MergeStrategy.SQUASH:
                result = pr.merge(
                    commit_title=commit_title,
                    commit_message=commit_message,
                    merge_method="squash"
                )
            elif strategy == MergeStrategy.REBASE:
                result = pr.merge(
                    commit_title=commit_title,
                    commit_message=commit_message,
                    merge_method="rebase"
                )
            else:
                raise ValueError(f"Invalid merge strategy: {strategy}")
                
            logger.info(f"Pull request #{pr_number} merged successfully")
            return result.merged
            
        except GithubException as e:
            logger.error(f"Failed to merge pull request: {str(e)}")
            raise
            
    def resolve_simple_conflicts(self, repo_name: str, pr_number: int) -> bool:
        """
        Attempt to resolve simple merge conflicts in a pull request.
        
        Args:
            repo_name: Full name of the repository (owner/repo)
            pr_number: Pull request number
            
        Returns:
            True if conflicts were resolved
        """
        logger.info(f"Attempting to resolve conflicts in PR #{pr_number} in {repo_name}")
        
        # Get the repository and pull request
        repo = self.github.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        # Check if the PR has conflicts
        if pr.mergeable:
            logger.info(f"Pull request #{pr_number} has no conflicts")
            return True
            
        # Get the base and head branches
        base_branch = pr.base.ref
        head_branch = pr.head.ref
        head_repo_name = pr.head.repo.full_name
        
        # Create a temporary directory for the operation
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Get the token for authentication
                token = self.github._Github__requester._Requester__auth.token
                
                # Clone the repository
                repo_url = f"https://{token}@github.com/{head_repo_name}.git"
                logger.info(f"Cloning repository to temporary directory")
                subprocess.run(["git", "clone", repo_url, temp_dir], 
                              check=True, capture_output=True)
                
                # Change to the repository directory
                os.chdir(temp_dir)
                
                # Configure Git
                subprocess.run(["git", "config", "user.name", "GitHub Compare Tool"], 
                              check=True, capture_output=True)
                subprocess.run(["git", "config", "user.email", "noreply@github.com"], 
                              check=True, capture_output=True)
                
                # Checkout the head branch
                subprocess.run(["git", "checkout", head_branch], 
                              check=True, capture_output=True)
                
                # Add the upstream repository if it's a fork
                if repo_name != head_repo_name:
                    upstream_url = f"https://{token}@github.com/{repo_name}.git"
                    subprocess.run(["git", "remote", "add", "upstream", upstream_url], 
                                  check=True, capture_output=True)
                    subprocess.run(["git", "fetch", "upstream"], 
                                  check=True, capture_output=True)
                    base_remote = "upstream"
                else:
                    base_remote = "origin"
                    
                # Try to merge the base branch
                try:
                    subprocess.run(["git", "merge", f"{base_remote}/{base_branch}"], 
                                  check=True, capture_output=True)
                    
                    # If we get here, the merge was successful with no conflicts
                    logger.info("Merge successful with no conflicts")
                    return True
                    
                except subprocess.CalledProcessError:
                    # There are conflicts, try to resolve them
                    logger.info("Merge conflicts detected, attempting to resolve")
                    
                    # Get the list of conflicting files
                    result = subprocess.run(["git", "diff", "--name-only", "--diff-filter=U"], 
                                          capture_output=True, text=True)
                    conflicting_files = result.stdout.strip().split('\n')
                    
                    # Try to resolve conflicts using the "ours" strategy for simple cases
                    resolved_count = 0
                    for file in conflicting_files:
                        if not file:
                            continue
                            
                        try:
                            # Check if the file is a simple text file
                            file_type = subprocess.run(
                                ["file", "-b", "--mime-type", file],
                                capture_output=True, text=True
                            ).stdout.strip()
                            
                            if file_type.startswith("text/"):
                                # For text files, try to use the "ours" strategy
                                subprocess.run(["git", "checkout", "--ours", file], 
                                              check=True, capture_output=True)
                                subprocess.run(["git", "add", file], 
                                              check=True, capture_output=True)
                                resolved_count += 1
                                logger.info(f"Resolved conflict in {file} using 'ours' strategy")
                            else:
                                logger.warning(f"Skipping non-text file: {file}")
                                
                        except subprocess.CalledProcessError as e:
                            logger.warning(f"Failed to resolve conflict in {file}: {str(e)}")
                            
                    # If we resolved all conflicts, commit and push
                    if resolved_count == len(conflicting_files):
                        subprocess.run(
                            ["git", "commit", "-m", f"Resolve merge conflicts with {base_branch}"],
                            check=True, capture_output=True
                        )
                        
                        subprocess.run(["git", "push", "origin", head_branch], 
                                      check=True, capture_output=True)
                        
                        logger.info(f"Resolved all {resolved_count} conflicts and pushed changes")
                        return True
                    else:
                        logger.warning(f"Could only resolve {resolved_count} out of {len(conflicting_files)} conflicts")
                        return False
                        
            except subprocess.CalledProcessError as e:
                logger.error(f"Git operation failed: {e.stderr.decode() if e.stderr else str(e)}")
                return False
            except Exception as e:
                logger.error(f"Error resolving conflicts: {str(e)}")
                return False
