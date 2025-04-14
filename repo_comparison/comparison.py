"""
Comparison functionality for the Repository Comparison Tool.
"""
import os
import shutil
import tempfile
import logging
from datetime import datetime
from typing import Dict, Any, Tuple, List, Optional
import threading

from .git_utils import GitUtils

logger = logging.getLogger('RepoComparisonTool.Comparison')

class ComparisonManager:
    """Manager for repository comparison operations."""
    
    def __init__(self, settings: Dict[str, Any] = None):
        self.settings = settings or {}
        self.temp_dir = tempfile.mkdtemp()
        logger.info(f"Created temporary directory: {self.temp_dir}")
    
    def cleanup(self):
        """Clean up temporary directories."""
        logger.info("Cleaning up temporary directories")
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def generate_difference(self, 
                           repo1_path: str, 
                           repo2_path: str, 
                           repo1_ref: str, 
                           repo2_ref: str, 
                           comparison_direction: str,
                           max_commits_behind: int = 100,
                           callback: Optional[callable] = None) -> Tuple[str, Dict[str, int]]:
        """
        Generate difference between two repositories.
        
        Args:
            repo1_path: Path or URL to the first repository
            repo2_path: Path or URL to the second repository
            repo1_ref: Branch or tag for the first repository
            repo2_ref: Branch or tag for the second repository
            comparison_direction: Direction of comparison ('1to2', '2to1', or 'both')
            max_commits_behind: Maximum number of commits to consider
            callback: Optional callback function for progress updates
            
        Returns:
            Tuple of (output directory path, statistics dictionary)
        """
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        repo1_name = GitUtils.get_repo_name(repo1_path)
        repo2_name = GitUtils.get_repo_name(repo2_path)
        output_dir = os.path.join(
            os.path.expanduser("~"), 
            "RepoComparisons", 
            f"{repo1_name}_vs_{repo2_name}_{timestamp}"
        )
        os.makedirs(output_dir, exist_ok=True)
        
        # Create temporary directories for repositories
        temp_repo1 = os.path.join(self.temp_dir, "repo1")
        temp_repo2 = os.path.join(self.temp_dir, "repo2")
        os.makedirs(temp_repo1, exist_ok=True)
        os.makedirs(temp_repo2, exist_ok=True)
        
        # Update callback if provided
        if callback:
            callback("Preparing repositories...", True)
        
        # Prepare repositories
        try:
            # Determine if paths are URLs or local paths
            repo1_is_url = GitUtils.is_url(repo1_path)
            repo2_is_url = GitUtils.is_url(repo2_path)
            
            # Clone repositories if needed
            if repo1_is_url:
                if callback:
                    callback(f"Cloning repository 1 from {repo1_path}...", True)
                if not GitUtils.clone_repo(repo1_path, temp_repo1):
                    raise Exception(f"Failed to clone repository 1 from {repo1_path}")
            else:
                temp_repo1 = repo1_path
            
            if repo2_is_url:
                if callback:
                    callback(f"Cloning repository 2 from {repo2_path}...", True)
                if not GitUtils.clone_repo(repo2_path, temp_repo2):
                    raise Exception(f"Failed to clone repository 2 from {repo2_path}")
            else:
                temp_repo2 = repo2_path
            
            # Create temporary directories for checked out repositories
            checkout_repo1 = os.path.join(self.temp_dir, "checkout_repo1")
            checkout_repo2 = os.path.join(self.temp_dir, "checkout_repo2")
            os.makedirs(checkout_repo1, exist_ok=True)
            os.makedirs(checkout_repo2, exist_ok=True)
            
            # Checkout specified refs
            if callback:
                callback(f"Checking out {repo1_ref} in repository 1...", True)
            if not GitUtils.prepare_repo_for_comparison(repo1_path, temp_repo1, checkout_repo1, repo1_ref):
                raise Exception(f"Failed to checkout {repo1_ref} in repository 1")
            
            if callback:
                callback(f"Checking out {repo2_ref} in repository 2...", True)
            if not GitUtils.prepare_repo_for_comparison(repo2_path, temp_repo2, checkout_repo2, repo2_ref):
                raise Exception(f"Failed to checkout {repo2_ref} in repository 2")
            
            # Create directories for unique files
            stats = {"repo1_unique": 0, "repo2_unique": 0}
            
            # Find files unique to repo1
            if comparison_direction in ["1to2", "both"]:
                if callback:
                    callback("Finding files unique to repository 1...", True)
                repo1_unique_dir = os.path.join(output_dir, "repo1_unique")
                os.makedirs(repo1_unique_dir, exist_ok=True)
                stats["repo1_unique"] = GitUtils.find_unique_files(checkout_repo1, checkout_repo2, repo1_unique_dir)
            
            # Find files unique to repo2
            if comparison_direction in ["2to1", "both"]:
                if callback:
                    callback("Finding files unique to repository 2...", True)
                repo2_unique_dir = os.path.join(output_dir, "repo2_unique")
                os.makedirs(repo2_unique_dir, exist_ok=True)
                stats["repo2_unique"] = GitUtils.find_unique_files(checkout_repo2, checkout_repo1, repo2_unique_dir)
            
            # Create comparison summary
            if callback:
                callback("Creating comparison summary...", True)
            self.create_comparison_summary(output_dir, repo1_path, repo2_path, repo1_ref, repo2_ref, 
                                          comparison_direction, stats)
            
            if callback:
                callback("Comparison completed successfully", False)
            
            return output_dir, stats
            
        except Exception as e:
            logger.error(f"Error during comparison: {str(e)}")
            if callback:
                callback(f"Error: {str(e)}", False)
            raise
    
    def create_comparison_summary(self, 
                                 output_dir: str, 
                                 repo1_path: str, 
                                 repo2_path: str, 
                                 repo1_ref: str, 
                                 repo2_ref: str,
                                 comparison_direction: str,
                                 stats: Dict[str, int]):
        """Create a summary file with information about the comparison."""
        summary_path = os.path.join(output_dir, "comparison_summary.txt")
        
        with open(summary_path, 'w') as f:
            f.write("Repository Comparison Summary\n")
            f.write("============================\n\n")
            
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("Repository 1:\n")
            f.write(f"  Path: {repo1_path}\n")
            f.write(f"  Branch/Tag: {repo1_ref}\n\n")
            
            f.write("Repository 2:\n")
            f.write(f"  Path: {repo2_path}\n")
            f.write(f"  Branch/Tag: {repo2_ref}\n\n")
            
            f.write("Comparison Direction:\n")
            if comparison_direction == "1to2":
                f.write("  Files in Repository 1 not in Repository 2\n\n")
            elif comparison_direction == "2to1":
                f.write("  Files in Repository 2 not in Repository 1\n\n")
            else:
                f.write("  Both directions (all differences)\n\n")
            
            f.write("Results Summary:\n")
            if comparison_direction in ["1to2", "both"]:
                f.write(f"  Files unique to Repository 1: {stats['repo1_unique']}\n")
            if comparison_direction in ["2to1", "both"]:
                f.write(f"  Files unique to Repository 2: {stats['repo2_unique']}\n")
            
            f.write(f"\nTotal unique files: {stats['repo1_unique'] + stats['repo2_unique']}\n")
            
            # Add settings information
            f.write("\nComparison Settings:\n")
            if self.settings.get('ignore_whitespace', False):
                f.write("  - Ignoring whitespace changes\n")
            if self.settings.get('ignore_case', False):
                f.write("  - Ignoring case differences\n")
            
            f.write("\nGenerated by Repository Comparison Tool v1.1.0\n")
    
    def run_comparison_async(self, 
                            repo1_path: str, 
                            repo2_path: str, 
                            repo1_ref: str, 
                            repo2_ref: str, 
                            comparison_direction: str,
                            max_commits_behind: int = 100,
                            callback: Optional[callable] = None,
                            on_complete: Optional[callable] = None):
        """Run the comparison in a background thread."""
        def _run():
            try:
                output_dir, stats = self.generate_difference(
                    repo1_path, repo2_path, repo1_ref, repo2_ref, 
                    comparison_direction, max_commits_behind, callback
                )
                if on_complete:
                    on_complete(output_dir, stats)
            except Exception as e:
                logger.error(f"Error in async comparison: {str(e)}")
                if callback:
                    callback(f"Error: {str(e)}", False)
        
        thread = threading.Thread(target=_run)
        thread.daemon = True
        thread.start()
        return thread
