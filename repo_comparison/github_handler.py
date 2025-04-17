"""
GitHub integration handler for the Repository Comparison Tool.
"""

import os
import logging
from github import Github
from github.Repository import Repository
from github.Branch import Branch
from github.Commit import Commit
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

class GithubHandler:
    def __init__(self, token: Optional[str] = None):
        """Initialize GitHub handler with optional token."""
        self.token = token or os.getenv('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("GitHub token not provided and GITHUB_TOKEN environment variable not set")
        
        self.github = Github(self.token)
        self.current_user = self.github.get_user()
        self.current_repo: Optional[Repository] = None
        self.cached_repos: List[Repository] = []
        self.cached_branches: Dict[str, List[Branch]] = {}
        self.last_error: Optional[str] = None
        
        logger.info("GitHub handler initialized")
    
    def get_user_repos(self) -> List[Repository]:
        """Get list of repositories accessible to the user."""
        try:
            if not self.cached_repos:
                self.cached_repos = list(self.github.get_user().get_repos())
            logger.info(f"Found {len(self.cached_repos)} repositories")
            return self.cached_repos
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error fetching repositories: {str(e)}")
            raise
    
    def get_repo_branches(self, repo: Repository) -> List[Branch]:
        """Get list of branches for a repository."""
        try:
            repo_key = repo.full_name
            if repo_key not in self.cached_branches:
                self.cached_branches[repo_key] = list(repo.get_branches())
            branches = self.cached_branches[repo_key]
            logger.info(f"Found {len(branches)} branches in {repo.full_name}")
            return branches
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error fetching branches for {repo.full_name}: {str(e)}")
            raise
    
    def get_branch_comparison(self, repo: Repository, base: str, compare: str) -> Tuple[int, int, List[Commit]]:
        """
        Compare two branches and return:
        - Number of commits ahead
        - Number of commits behind
        - List of commits
        """
        try:
            comparison = repo.compare(base, compare)
            ahead_by = comparison.ahead_by
            behind_by = comparison.behind_by
            commits = comparison.commits
            
            logger.info(f"Branch comparison for {repo.full_name}: ahead={ahead_by}, behind={behind_by}")
            return ahead_by, behind_by, commits
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error comparing branches in {repo.full_name}: {str(e)}")
            raise
    
    def apply_commit(self, repo: Repository, commit: Commit) -> Dict[str, int]:
        """
        Apply a commit and return statistics:
        - Number of files changed
        - Number of additions
        - Number of deletions
        """
        try:
            # Get commit stats
            stats = {
                'files_changed': len(commit.files),
                'additions': commit.stats.additions,
                'deletions': commit.stats.deletions,
                'total': commit.stats.total
            }
            
            logger.info(f"Commit {commit.sha[:7]} stats: {stats}")
            return stats
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error applying commit {commit.sha[:7]}: {str(e)}")
            raise
    
    def get_commit_details(self, repo: Repository, commit_sha: str) -> Dict:
        """Get detailed information about a specific commit."""
        try:
            commit = repo.get_commit(commit_sha)
            return {
                'sha': commit.sha,
                'message': commit.commit.message,
                'author': commit.commit.author.name,
                'date': commit.commit.author.date,
                'stats': {
                    'additions': commit.stats.additions,
                    'deletions': commit.stats.deletions,
                    'total': commit.stats.total
                },
                'files': [
                    {
                        'filename': f.filename,
                        'additions': f.additions,
                        'deletions': f.deletions,
                        'changes': f.changes,
                        'status': f.status
                    }
                    for f in commit.files
                ]
            }
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error getting commit details for {commit_sha}: {str(e)}")
            raise
    
    def set_current_repo(self, repo: Repository) -> bool:
        """Set the current repository for operations."""
        try:
            self.current_repo = repo
            return True
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error setting current repository: {str(e)}")
            return False
    
    def clear_cache(self):
        """Clear cached data."""
        self.cached_repos = []
        self.cached_branches = {}
        logger.info("Cache cleared")
    
    def get_last_error(self) -> Optional[str]:
        """Get the last error message."""
        return self.last_error
    
    def get_rate_limit(self) -> Dict[str, int]:
        """Get current GitHub API rate limit status."""
        try:
            rate_limit = self.github.get_rate_limit()
            return {
                'core': {
                    'limit': rate_limit.core.limit,
                    'remaining': rate_limit.core.remaining,
                    'reset': rate_limit.core.reset.timestamp()
                },
                'search': {
                    'limit': rate_limit.search.limit,
                    'remaining': rate_limit.search.remaining,
                    'reset': rate_limit.search.reset.timestamp()
                }
            }
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error getting rate limit: {str(e)}")
            raise
