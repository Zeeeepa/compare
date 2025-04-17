"""
Comparison manager for handling repository comparisons.
"""

import os
import logging
import tempfile
import shutil
from typing import Dict, List, Optional, Tuple
from git import Repo
from github.Repository import Repository

logger = logging.getLogger(__name__)

class ComparisonManager:
    def __init__(self):
        """Initialize the comparison manager."""
        self.temp_dir = tempfile.mkdtemp()
        logger.info(f"Created temporary directory: {self.temp_dir}")
        
        # Repository attributes
        self.repo1: Optional[Repo] = None
        self.repo2: Optional[Repo] = None
        self.repo1_path: Optional[str] = None
        self.repo2_path: Optional[str] = None
        
        # Comparison state
        self.comparison_in_progress = False
        self.last_comparison_result: Optional[Dict] = None
        self.current_operation: Optional[str] = None
        
        # Statistics
        self.stats = {
            'files_compared': 0,
            'differences_found': 0,
            'comparison_time': 0.0
        }
    
    def cleanup(self):
        """Clean up temporary directories."""
        try:
            if self.repo1:
                self.repo1.close()
            if self.repo2:
                self.repo2.close()
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
    
    def set_repositories(self, repo1_path: str, repo2_path: str) -> Tuple[bool, str]:
        """Set the repositories for comparison."""
        try:
            self.repo1_path = repo1_path
            self.repo2_path = repo2_path
            
            # Clone or open repositories
            if repo1_path.startswith(('http://', 'https://', 'git@')):
                self.repo1 = self.clone_repo(repo1_path, os.path.join(self.temp_dir, 'repo1'))
            else:
                self.repo1 = Repo(repo1_path)
            
            if repo2_path.startswith(('http://', 'https://', 'git@')):
                self.repo2 = self.clone_repo(repo2_path, os.path.join(self.temp_dir, 'repo2'))
            else:
                self.repo2 = Repo(repo2_path)
            
            return True, "Repositories set successfully"
        except Exception as e:
            logger.error(f"Error setting repositories: {str(e)}")
            return False, str(e)
    
    def get_comparison_status(self) -> Dict[str, any]:
        """Get current comparison status and statistics."""
        return {
            'in_progress': self.comparison_in_progress,
            'current_operation': self.current_operation,
            'stats': self.stats,
            'last_result': self.last_comparison_result
        }
    
    def reset_state(self):
        """Reset the comparison state."""
        self.comparison_in_progress = False
        self.current_operation = None
        self.stats = {
            'files_compared': 0,
            'differences_found': 0,
            'comparison_time': 0.0
        }
        self.last_comparison_result = None
