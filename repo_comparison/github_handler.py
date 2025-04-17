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
        logger.info("GitHub handler initialized")
    
    def get_user_repos(self) -> List[Repository]:
        """Get list of repositories accessible to the user."""
        try:
            repos = list(self.github.get_user().get_repos())
            logger.info(f"Found {len(repos)} repositories")
            return repos
        except Exception as e:
            logger.error(f"Error fetching repositories: {str(e)}")
            raise
    
    def get_repo_branches(self, repo: Repository) -> List[Branch]:
        """Get list of branches for a repository."""
        try:
            branches = list(repo.get_branches())
            logger.info(f"Found {len(branches)} branches in {repo.full_name}")
            return branches
        except Exception as e:
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
            logger.error(f"Error getting commit details for {commit_sha}: {str(e)}")
            raise
