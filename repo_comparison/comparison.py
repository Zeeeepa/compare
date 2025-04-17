"""
Comparison manager for handling repository comparisons.
"""

import os
import logging
import tempfile
import shutil
from typing import Dict, List, Optional
from git import Repo
from github.Repository import Repository

logger = logging.getLogger(__name__)

class ComparisonManager:
    def __init__(self):
        """Initialize the comparison manager."""
        self.temp_dir = tempfile.mkdtemp()
        logger.info(f"Created temporary directory: {self.temp_dir}")
    
    def cleanup(self):
        """Clean up temporary directories."""
        try:
            shutil.rmtree(self.temp_dir)
            logger.info("Cleaned up temporary directory")
        except Exception as e:
            logger.error(f"Error cleaning up: {str(e)}")
    
    def clone_repo(self, repo_url: str, target_dir: str) -> Repo:
        """Clone a repository to a target directory."""
        try:
            repo = Repo.clone_from(repo_url, target_dir)
            logger.info(f"Cloned repository from {repo_url} to {target_dir}")
            return repo
        except Exception as e:
            logger.error(f"Error cloning repository: {str(e)}")
            raise
    
    def get_branch_diff(self, repo: Repo, base: str, compare: str) -> Dict[str, int]:
        """Get the difference between two branches."""
        try:
            # Fetch both branches
            repo.git.fetch('origin', base)
            repo.git.fetch('origin', compare)
            
            # Get the difference
            base_commit = repo.commit(f'origin/{base}')
            compare_commit = repo.commit(f'origin/{compare}')
            
            # Count differences
            diff = base_commit.diff(compare_commit)
            
            stats = {
                'files_changed': len(diff),
                'additions': sum(d.additions for d in diff),
                'deletions': sum(d.deletions for d in diff),
                'total': sum(d.additions + d.deletions for d in diff)
            }
            
            logger.info(f"Branch diff stats: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error getting branch diff: {str(e)}")
            raise
    
    def apply_commit(self, repo: Repo, commit_sha: str) -> Dict[str, int]:
        """Apply a specific commit and return statistics."""
        try:
            # Cherry pick the commit
            repo.git.cherry_pick(commit_sha)
            
            # Get commit stats
            commit = repo.commit(commit_sha)
            stats = {
                'files_changed': len(commit.stats.files),
                'additions': commit.stats.total['insertions'],
                'deletions': commit.stats.total['deletions'],
                'total': commit.stats.total['lines']
            }
            
            logger.info(f"Applied commit {commit_sha[:7]} with stats: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error applying commit: {str(e)}")
            repo.git.cherry_pick('--abort')  # Clean up failed cherry-pick
            raise
    
    def get_commit_files(self, repo: Repo, commit_sha: str) -> List[Dict[str, str]]:
        """Get list of files modified in a commit."""
        try:
            commit = repo.commit(commit_sha)
            files = []
            
            for item in commit.stats.files:
                file_data = {
                    'path': item,
                    'changes': commit.stats.files[item]
                }
                files.append(file_data)
            
            return files
        except Exception as e:
            logger.error(f"Error getting commit files: {str(e)}")
            raise
