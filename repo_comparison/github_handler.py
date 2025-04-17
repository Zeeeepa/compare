import os
from github import Github
from github.Repository import Repository
from github.Branch import Branch
from github.Commit import Commit
from typing import List, Tuple, Dict
import logging

logger = logging.getLogger('RepoComparisonTool.GithubHandler')

class GithubHandler:
    def __init__(self, token: str = None):
        """Initialize GitHub handler with optional token."""
        self.token = token or os.getenv('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("GitHub token not provided and GITHUB_TOKEN environment variable not set")
        self.github = Github(self.token)
        
    def get_user_repos(self) -> List[Repository]:
        """Get list of repositories accessible to the user."""
        try:
            return list(self.github.get_user().get_repos())
        except Exception as e:
            logger.error(f"Error fetching repositories: {str(e)}")
            raise
            
    def get_repo_branches(self, repo: Repository) -> List[Branch]:
        """Get list of branches for a repository."""
        try:
            return list(repo.get_branches())
        except Exception as e:
            logger.error(f"Error fetching branches for {repo.full_name}: {str(e)}")
            raise
            
    def get_branch_comparison(self, repo: Repository, base: str, head: str) -> Tuple[int, int, List[Commit]]:
        """Get commits ahead/behind and list of commits between branches."""
        try:
            comparison = repo.compare(base=base, head=head)
            ahead_by = comparison.ahead_by
            behind_by = comparison.behind_by
            commits = comparison.commits
            return ahead_by, behind_by, commits
        except Exception as e:
            logger.error(f"Error comparing branches in {repo.full_name}: {str(e)}")
            raise
            
    def apply_commit(self, repo: Repository, commit: Commit) -> Dict[str, int]:
        """Apply a specific commit and return change statistics."""
        try:
            stats = commit.stats
            return {
                'total': stats.total,
                'additions': stats.additions,
                'deletions': stats.deletions,
                'files_changed': len(commit.files)
            }
        except Exception as e:
            logger.error(f"Error applying commit {commit.sha} in {repo.full_name}: {str(e)}")
            raise
