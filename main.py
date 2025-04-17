#!/usr/bin/env python3

"""
Repository Comparison Tool
A tool for comparing Git repositories and managing commits.
"""

import os
import sys
import logging
from repo_comparison.github_handler import GithubHandler
from repo_comparison.comparison import ComparisonManager
from repo_diff_gui_upgraded import RepoComparisonTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('repo_compare.log')
    ]
)
logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if all required dependencies are installed."""
    try:
        import tkinter
        import git
        return True
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        print("Please install required dependencies using: pip install -r requirements.txt")
        return False

def check_github_token():
    """Check if GitHub token is set in environment variables."""
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        logger.warning("GITHUB_TOKEN environment variable not set")
        print("Warning: GITHUB_TOKEN not set. GitHub integration will be limited.")
        return False
    return True

def main():
    """Main entry point for the application."""
    try:
        # Check dependencies
        if not check_dependencies():
            sys.exit(1)
            
        # Check GitHub token
        check_github_token()
        
        # Initialize components
        github_handler = GithubHandler()
        comparison_manager = ComparisonManager()
        
        # Start the GUI application
        app = RepoComparisonTool()
        app.mainloop()
        
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
