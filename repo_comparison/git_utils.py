"""
Git utilities for the Repository Comparison Tool.
"""
import os
import subprocess
import logging
import shutil
from typing import List, Tuple, Optional, Dict, Any
import git

logger = logging.getLogger('RepoComparisonTool.GitUtils')

class GitUtils:
    """Utility class for Git operations."""
    
    @staticmethod
    def is_url(path: str) -> bool:
        """Check if the given path is a URL."""
        return path.startswith(('http://', 'https://', 'git@'))
    
    @staticmethod
    def get_repo_name(repo_path: str) -> str:
        """Extract repository name from path or URL."""
        if GitUtils.is_url(repo_path):
            # Extract repo name from URL
            if repo_path.endswith('.git'):
                repo_path = repo_path[:-4]
            
            # Handle SSH URLs (git@github.com:user/repo.git)
            if repo_path.startswith('git@'):
                parts = repo_path.split(':')
                if len(parts) >= 2:
                    return parts[1].split('/')[-1]
            
            # Handle HTTPS URLs
            parts = repo_path.rstrip('/').split('/')
            return parts[-1]
        else:
            # Extract repo name from local path
            return os.path.basename(os.path.normpath(repo_path))
    
    @staticmethod
    def clone_repo(repo_path: str, target_dir: str) -> bool:
        """Clone a repository from URL to target directory."""
        if GitUtils.is_url(repo_path):
            logger.info(f"Cloning repository from {repo_path} to {target_dir}")
            try:
                # Use GitPython for more robust cloning
                git.Repo.clone_from(repo_path, target_dir)
                
                # Configure fetch to get all branches
                repo = git.Repo(target_dir)
                with repo.config_writer() as config:
                    config.set_value('remote "origin"', 'fetch', '+refs/heads/*:refs/remotes/origin/*')
                
                # Fetch all branches
                repo.git.fetch('--all')
                
                return True
            except git.GitCommandError as e:
                logger.error(f"Error during repository cloning: {str(e)}")
                return False
        else:
            logger.info(f"Using local repository: {repo_path}")
            return True
    
    @staticmethod
    def get_tags_and_branches(repo_path: str) -> Tuple[List[str], List[str]]:
        """Get all tags and branches from a repository."""
        tags = []
        branches = []
        
        try:
            if os.path.exists(repo_path):
                # Get tags
                result = subprocess.run(
                    ['git', '-C', repo_path, 'tag'], 
                    capture_output=True, text=True, check=True
                )
                tags = [tag.strip() for tag in result.stdout.splitlines() if tag.strip()]
                
                # Get branches
                result = subprocess.run(
                    ['git', '-C', repo_path, 'branch', '-a'], 
                    capture_output=True, text=True, check=True
                )
                
                for branch in result.stdout.splitlines():
                    branch = branch.strip()
                    if branch.startswith('*'):
                        branch = branch[1:].strip()
                    
                    if branch.startswith('remotes/origin/'):
                        branch = branch[len('remotes/origin/'):].strip()
                    
                    if branch and branch != 'HEAD' and branch not in branches:
                        branches.append(branch)
        except subprocess.SubprocessError as e:
            logger.error(f"Error getting tags and branches: {str(e)}")
        
        return tags, branches
    
    @staticmethod
    def prepare_repo_for_comparison(repo_path: str, repo_dir: str, temp_dir: str, selected_ref: str) -> bool:
        """Prepare a repository for comparison by checking out the selected ref."""
        logger.info(f"Preparing repository {repo_path} with ref {selected_ref}")
        
        try:
            if GitUtils.is_url(repo_path):
                # For URL repositories, clone with the selected ref
                repo = git.Repo.clone_from(repo_path, temp_dir)
                
                try:
                    # Try to checkout the selected ref
                    repo.git.checkout(selected_ref)
                except git.GitCommandError:
                    # If direct checkout fails, try to fetch and checkout
                    logger.warning(f"Direct checkout failed, trying to fetch {selected_ref}")
                    repo.git.fetch('origin', selected_ref)
                    
                    try:
                        repo.git.checkout(selected_ref)
                    except git.GitCommandError:
                        # If it still fails, try to checkout FETCH_HEAD
                        logger.warning("Fetch and checkout failed, trying FETCH_HEAD")
                        repo.git.checkout('FETCH_HEAD')
            else:
                # For local repositories, create a copy and checkout
                GitUtils.copy_git_repo(repo_dir, temp_dir)
                
                repo = git.Repo(temp_dir)
                try:
                    # Try to checkout the selected ref
                    repo.git.checkout(selected_ref)
                except git.GitCommandError:
                    # If checkout fails, try to fetch first
                    logger.warning(f"Local checkout failed, trying to fetch {selected_ref}")
                    repo.git.fetch('--all')
                    
                    try:
                        repo.git.checkout(selected_ref)
                    except git.GitCommandError:
                        logger.error(f"Failed to checkout {selected_ref}")
                        return False
            
            return True
        except Exception as e:
            logger.error(f"Error preparing repository: {str(e)}")
            return False
    
    @staticmethod
    def copy_git_repo(source_repo: str, target_dir: str) -> bool:
        """Create a copy of a git repository for comparison."""
        logger.info(f"Copying repository from {source_repo} to {target_dir}")
        
        try:
            # Initialize a new git repository in the target directory
            os.makedirs(target_dir, exist_ok=True)
            git.Repo.init(target_dir)
            
            # Add the source repository as a remote
            repo = git.Repo(target_dir)
            origin = repo.create_remote('origin', source_repo)
            
            # Fetch all branches and tags
            origin.fetch('--all')
            origin.fetch('--tags')
            
            return True
        except Exception as e:
            logger.error(f"Error copying repository: {str(e)}")
            return False
    
    @staticmethod
    def find_unique_files(source_repo: str, target_repo: str, output_dir: str) -> int:
        """Find files that exist in source_repo but not in target_repo and copy them to output_dir."""
        logger.info(f"Finding unique files from {source_repo} not in {target_repo}")
        
        # Get list of files in source repo
        source_files = []
        for root, dirs, files in os.walk(source_repo):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, source_repo)
                source_files.append(rel_path)
        
        # Get list of files in target repo
        target_files = []
        for root, dirs, files in os.walk(target_repo):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, target_repo)
                target_files.append(rel_path)
        
        # Find files in source but not in target
        unique_files = [f for f in source_files if f not in target_files]
        logger.info(f"Found {len(unique_files)} unique files")
        
        # Copy unique files to output directory
        for file in unique_files:
            source_file = os.path.join(source_repo, file)
            target_file = os.path.join(output_dir, file)
            
            # Create directory structure
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            
            # Copy file
            try:
                shutil.copy2(source_file, target_file)
            except (shutil.Error, IOError) as e:
                logger.warning(f"Error copying file {file}: {str(e)}")
        
        return len(unique_files)
