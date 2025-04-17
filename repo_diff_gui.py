import os
import re
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import tempfile
import shutil
from datetime import datetime
import urllib.parse
import logging
from repo_comparison.github_handler import GithubHandler
from github.Repository import Repository
from github.Branch import Branch
from github.Commit import Commit

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('RepoComparisonTool')

class RepoComparisonTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Repository Comparison Tool")
        self.root.geometry("1200x800")
        self.root.minsize(1200, 800)
        
        # Set style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Variables
        self.repo1_path = tk.StringVar()
        self.repo2_path = tk.StringVar()
        self.repo1_search = tk.StringVar()
        self.repo2_search = tk.StringVar()
        self.max_commits_behind = tk.StringVar(value="100")
        self.comparison_direction = tk.StringVar(value="both")
        self.status_text = tk.StringVar(value="Ready")
        self.repo1_tags = []
        self.repo2_tags = []
        self.repo1_selected_tag = tk.StringVar()
        self.repo2_selected_tag = tk.StringVar()
        
        # GitHub integration
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.github_handler = None
        if self.github_token:
            try:
                self.github_handler = GithubHandler(self.github_token)
            except Exception as e:
                logger.error(f"Failed to initialize GitHub handler: {str(e)}")
        
        self.github_repos = []
        self.selected_repo = None
        self.repo_branches = []
        self.selected_branch = None
        self.comparison_commits = []
        
        # Create temp directory for cloning repos
        self.temp_dir = tempfile.mkdtemp()
        logger.info(f"Created temporary directory: {self.temp_dir}")
        
        # Create UI
        self.create_ui()
    
    def create_ui(self):
        # Main frame with notebook for tabs
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Local comparison tab
        local_frame = ttk.Frame(notebook, padding="10")
        notebook.add(local_frame, text="Local Comparison")
        self.create_local_comparison_ui(local_frame)
        
        # GitHub comparison tab
        github_frame = ttk.Frame(notebook, padding="10")
        notebook.add(github_frame, text="GitHub Comparison")
        self.create_github_comparison_ui(github_frame)
        
        # Status bar
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Label(status_frame, textvariable=self.status_text).pack(side=tk.LEFT, padx=10)
    
    def create_local_comparison_ui(self, parent):
        # Main frame
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Repository 1 frame
        repo1_frame = ttk.LabelFrame(main_frame, text="Repository 1", padding="10")
        repo1_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(repo1_frame, text="Repository Path or URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        repo1_entry = ttk.Entry(repo1_frame, textvariable=self.repo1_path, width=50)
        repo1_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        ttk.Button(repo1_frame, text="Browse", command=lambda: self.browse_repo(self.repo1_path)).grid(row=0, column=2, padx=5, pady=5)
        
        # Repository 2 frame
        repo2_frame = ttk.LabelFrame(main_frame, text="Repository 2", padding="10")
        repo2_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(repo2_frame, text="Repository Path or URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        repo2_entry = ttk.Entry(repo2_frame, textvariable=self.repo2_path, width=50)
        repo2_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        ttk.Button(repo2_frame, text="Browse", command=lambda: self.browse_repo(self.repo2_path)).grid(row=0, column=2, padx=5, pady=5)
        
        # Fetch tags button
        fetch_frame = ttk.Frame(main_frame)
        fetch_frame.pack(fill=tk.X, pady=5)
        ttk.Button(fetch_frame, text="Fetch Tags", command=self.fetch_tags).pack(pady=10)
        
        # Tags selection frame
        tags_frame = ttk.Frame(main_frame)
        tags_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        tags_frame.columnconfigure(0, weight=1)
        tags_frame.columnconfigure(1, weight=1)
        
        # Repository 1 tags
        repo1_tags_frame = ttk.LabelFrame(tags_frame, text="Repository 1 Tags/Branches", padding="10")
        repo1_tags_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=5)
        
        ttk.Label(repo1_tags_frame, text="Search:").pack(anchor=tk.W, pady=5)
        ttk.Entry(repo1_tags_frame, textvariable=self.repo1_search).pack(fill=tk.X, pady=5)
        self.repo1_search.trace_add("write", lambda *args: self.filter_tags(1))
        
        self.repo1_tags_listbox = tk.Listbox(repo1_tags_frame, height=10)
        self.repo1_tags_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        repo1_scrollbar = ttk.Scrollbar(self.repo1_tags_listbox, orient="vertical", command=self.repo1_tags_listbox.yview)
        self.repo1_tags_listbox.configure(yscrollcommand=repo1_scrollbar.set)
        repo1_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Repository 2 tags
        repo2_tags_frame = ttk.LabelFrame(tags_frame, text="Repository 2 Tags/Branches", padding="10")
        repo2_tags_frame.grid(row=0, column=1, sticky=tk.NSEW, padx=5)
        
        ttk.Label(repo2_tags_frame, text="Search:").pack(anchor=tk.W, pady=5)
        ttk.Entry(repo2_tags_frame, textvariable=self.repo2_search).pack(fill=tk.X, pady=5)
        self.repo2_search.trace_add("write", lambda *args: self.filter_tags(2))
        
        self.repo2_tags_listbox = tk.Listbox(repo2_tags_frame, height=10)
        self.repo2_tags_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        repo2_scrollbar = ttk.Scrollbar(self.repo2_tags_listbox, orient="vertical", command=self.repo2_tags_listbox.yview)
        self.repo2_tags_listbox.configure(yscrollcommand=repo2_scrollbar.set)
        repo2_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Filter frame
        filter_frame = ttk.LabelFrame(main_frame, text="Filtering Options", padding="10")
        filter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(filter_frame, text="Max Commits Behind:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(filter_frame, textvariable=self.max_commits_behind, width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Button(filter_frame, text="Apply Filter", command=self.apply_filter).grid(row=0, column=2, padx=5, pady=5)
        
        # Comparison direction
        direction_frame = ttk.LabelFrame(main_frame, text="Comparison Direction", padding="10")
        direction_frame.pack(fill=tk.X, pady=5)
        
        ttk.Radiobutton(direction_frame, text="Repo1 \u2192 Repo2 (files in Repo1 not in Repo2)", 
                        variable=self.comparison_direction, value="1to2").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(direction_frame, text="Repo2 \u2192 Repo1 (files in Repo2 not in Repo1)", 
                        variable=self.comparison_direction, value="2to1").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(direction_frame, text="Both directions (all differences)", 
                        variable=self.comparison_direction, value="both").pack(anchor=tk.W, pady=2)
        
        # Generate button
        generate_frame = ttk.Frame(main_frame)
        generate_frame.pack(fill=tk.X, pady=10)
        ttk.Button(generate_frame, text="Generate Difference", command=self.generate_difference).pack(pady=5)
    
    def create_github_comparison_ui(self, parent):
        # Repository selection frame
        repo_frame = ttk.LabelFrame(parent, text="GitHub Repository", padding="10")
        repo_frame.pack(fill=tk.X, pady=5)
        
        # Repository list
        repo_list_frame = ttk.Frame(repo_frame)
        repo_list_frame.pack(fill=tk.X, pady=5)
        
        self.repo_listbox = tk.Listbox(repo_list_frame, height=5)
        self.repo_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        repo_scrollbar = ttk.Scrollbar(repo_list_frame, orient="vertical", command=self.repo_listbox.yview)
        self.repo_listbox.configure(yscrollcommand=repo_scrollbar.set)
        repo_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Refresh repositories button
        ttk.Button(repo_frame, text="Refresh Repositories", command=self.refresh_github_repos).pack(pady=5)
        
        # Branch selection frame
        branch_frame = ttk.LabelFrame(parent, text="Branch Selection", padding="10")
        branch_frame.pack(fill=tk.X, pady=5)
        
        # Branch lists
        branches_container = ttk.Frame(branch_frame)
        branches_container.pack(fill=tk.X, pady=5)
        
        # Base branch
        base_frame = ttk.LabelFrame(branches_container, text="Base Branch", padding="5")
        base_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.base_branch_listbox = tk.Listbox(base_frame, height=5)
        self.base_branch_listbox.pack(fill=tk.X)
        
        # Compare branch
        compare_frame = ttk.LabelFrame(branches_container, text="Compare Branch", padding="5")
        compare_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.compare_branch_listbox = tk.Listbox(compare_frame, height=5)
        self.compare_branch_listbox.pack(fill=tk.X)
        
        # Compare button
        ttk.Button(branch_frame, text="Compare Branches", command=self.compare_branches).pack(pady=5)
        
        # Commits frame
        commits_frame = ttk.LabelFrame(parent, text="Commits", padding="10")
        commits_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Commit information
        info_frame = ttk.Frame(commits_frame)
        info_frame.pack(fill=tk.X, pady=5)
        
        self.ahead_label = ttk.Label(info_frame, text="Ahead by: 0")
        self.ahead_label.pack(side=tk.LEFT, padx=5)
        
        self.behind_label = ttk.Label(info_frame, text="Behind by: 0")
        self.behind_label.pack(side=tk.LEFT, padx=5)
        
        # Commits list
        self.commits_listbox = tk.Listbox(commits_frame, height=10)
        self.commits_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        commits_scrollbar = ttk.Scrollbar(self.commits_listbox, orient="vertical", command=self.commits_listbox.yview)
        self.commits_listbox.configure(yscrollcommand=commits_scrollbar.set)
        commits_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Apply commit button
        ttk.Button(commits_frame, text="Apply Selected Commit", command=self.apply_selected_commit).pack(pady=5)
    
    def browse_repo(self, path_var):
        folder_path = filedialog.askdirectory()
        if folder_path:
            path_var.set(folder_path)
            logger.info(f"Selected repository path: {folder_path}")
    
    def is_url(self, path):
        """Check if the given path is a URL."""
        return path.startswith(('http://', 'https://'))
    
    def get_repo_name(self, repo_path):
        """Extract repository name from path or URL."""
        if self.is_url(repo_path):
            # Extract repo name from URL
            parsed_url = urllib.parse.urlparse(repo_path)
            path_parts = parsed_url.path.strip('/').split('/')
            if len(path_parts) >= 2:
                return path_parts[-1].replace('.git', '')
            return "repo"  # Default if we can't extract a name
        else:
            # Extract repo name from local path
            return os.path.basename(repo_path)
    
    def clone_repo(self, repo_path, target_dir):
        """Clone a repository from URL to target directory."""
        if self.is_url(repo_path):
            self.update_status(f"Cloning repository from {repo_path}...")
            logger.info(f"Cloning repository from {repo_path} to {target_dir}")
            try:
                # First try a regular clone to get all branches
                result = subprocess.run(
                    ['git', 'clone', '--depth', '1', repo_path, target_dir], 
                    capture_output=True, text=True
                )
                
                if result.returncode != 0:
                    # If regular clone fails, try mirror clone
                    logger.warning(f"Regular clone failed: {result.stderr}. Trying mirror clone.")
                    result = subprocess.run(
                        ['git', 'clone', '--mirror', repo_path, target_dir], 
                        capture_output=True, text=True
                    )
                    
                if result.returncode != 0:
                    error_msg = f"Failed to clone repository: {result.stderr}"
                    logger.error(error_msg)
                    messagebox.showerror("Error", error_msg)
                    return False
                
                # Configure fetch to get all branches
                subprocess.run(
                    ['git', '-C', target_dir, 'config', 'remote.origin.fetch', '+refs/heads/*:refs/remotes/origin/*'],
                    capture_output=True, text=True
                )
                
                # Fetch all branches
                subprocess.run(
                    ['git', '-C', target_dir, 'fetch', '--all'],
                    capture_output=True, text=True
                )
                
                return True
            except subprocess.SubprocessError as e:
                error_msg = f"Error during repository cloning: {str(e)}"
                logger.error(error_msg)
                messagebox.showerror("Error", error_msg)
                return False
        else:
            # Local repository, just validate it
            if not os.path.exists(os.path.join(repo_path, '.git')):
                error_msg = f"The path '{repo_path}' is not a valid Git repository."
                logger.error(error_msg)
                messagebox.showerror("Error", error_msg)
                return False
            return True
    
    def get_repo_dir(self, repo_path):
        """Get or create a directory for the repository."""
        if not repo_path:
            logger.error("Repository path is empty")
            messagebox.showerror("Error", "Repository path cannot be empty")
            return None
            
        if self.is_url(repo_path):
            repo_name = self.get_repo_name(repo_path)
            repo_dir = os.path.join(self.temp_dir, repo_name)
            
            # If directory exists but is empty or not a git repo, remove it
            if os.path.exists(repo_dir):
                if not os.path.exists(os.path.join(repo_dir, '.git')):
                    logger.info(f"Removing invalid repository directory: {repo_dir}")
                    shutil.rmtree(repo_dir, ignore_errors=True)
            
            if not os.path.exists(repo_dir):
                if not self.clone_repo(repo_path, repo_dir):
                    return None
            return repo_dir
        else:
            # Validate local repository
            if not os.path.exists(repo_path):
                error_msg = f"The path '{repo_path}' does not exist."
                logger.error(error_msg)
                messagebox.showerror("Error", error_msg)
                return None
                
            if not os.path.isdir(repo_path):
                error_msg = f"The path '{repo_path}' is not a directory."
                logger.error(error_msg)
                messagebox.showerror("Error", error_msg)
                return None
                
            if not os.path.exists(os.path.join(repo_path, '.git')):
                error_msg = f"The path '{repo_path}' is not a valid Git repository."
                logger.error(error_msg)
                messagebox.showerror("Error", error_msg)
                return None
                
            return repo_path
    
    def fetch_tags(self):
        """Start a thread to fetch tags and branches."""
        threading.Thread(target=self._fetch_tags_thread).start()
    
    def _fetch_tags_thread(self):
        """Fetch tags and branches from repositories."""
        self.update_status("Fetching tags and branches...")
        
        # Repo 1
        repo1_path = self.repo1_path.get().strip()
        if not repo1_path:
            messagebox.showerror("Error", "Please enter Repository 1 path or URL")
            self.update_status("Ready")
            return
        
        repo1_dir = self.get_repo_dir(repo1_path)
        if not repo1_dir:
            self.update_status("Failed to access Repository 1")
            return
        
        # Repo 2
        repo2_path = self.repo2_path.get().strip()
        if not repo2_path:
            messagebox.showerror("Error", "Please enter Repository 2 path or URL")
            self.update_status("Ready")
            return
        
        repo2_dir = self.get_repo_dir(repo2_path)
        if not repo2_dir:
            self.update_status("Failed to access Repository 2")
            return
        
        # Get tags and branches for repo1
        self.update_status("Getting tags and branches for Repository 1...")
        self.repo1_tags = self.get_tags_and_branches(repo1_dir)
        
        # Get tags and branches for repo2
        self.update_status("Getting tags and branches for Repository 2...")
        self.repo2_tags = self.get_tags_and_branches(repo2_dir)
        
        # Update UI with tags
        self.update_status("Updating UI with tags and branches...")
        self.update_tags_ui()
        
        self.update_status("Ready")
    
    def get_tags_and_branches(self, repo_dir):
        """Get all tags and branches from a repository with commit information."""
        tags_and_branches = []
        
        try:
            # Get all branches (local and remote)
            branches_result = subprocess.run(
                ['git', '-C', repo_dir, 'branch', '-a'], 
                capture_output=True, text=True, check=True
            )
            
            # Get all tags
            tags_result = subprocess.run(
                ['git', '-C', repo_dir, 'tag'], 
                capture_output=True, text=True, check=True
            )
            
            # Process branches
            branches = []
            for line in branches_result.stdout.splitlines():
                branch = line.strip().replace('* ', '')
                # Skip remote branches that are duplicates of local ones
                if branch.startswith('remotes/origin/') and branch.replace('remotes/origin/', '') in branches:
                    continue
                # Clean up remote branch names
                if branch.startswith('remotes/origin/'):
                    branch = branch.replace('remotes/origin/', '')
                if branch and branch != 'HEAD':
                    branches.append(branch)
            
            # Process tags
            tags = tags_result.stdout.splitlines()
            
            # Combine branches and tags
            refs = branches + tags
            
            # Get default branch (usually main or master)
            default_branch = self.get_default_branch(repo_dir)
            
            # Add default branch first if it exists
            if default_branch in refs:
                refs.remove(default_branch)
                refs.insert(0, default_branch)
            
            # Get commit information for each ref
            for ref in refs:
                try:
                    # Get ahead/behind counts compared to HEAD
                    ahead_behind = self.get_ahead_behind(repo_dir, ref)
                    tags_and_branches.append({
                        'name': ref,
                        'ahead': ahead_behind['ahead'],
                        'behind': ahead_behind['behind']
                    })
                except subprocess.CalledProcessError:
                    # Skip refs that cause errors
                    logger.warning(f"Skipping ref {ref} due to error")
                    continue
            
            return tags_and_branches
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting tags and branches: {e.stderr}")
            return []
    
    def get_default_branch(self, repo_dir):
        """Get the default branch of a repository (main or master)."""
        try:
            # Try to get the default branch from remote
            result = subprocess.run(
                ['git', '-C', repo_dir, 'remote', 'show', 'origin'], 
                capture_output=True, text=True, check=True
            )
            
            # Parse the output to find the default branch
            for line in result.stdout.splitlines():
                if 'HEAD branch' in line:
                    return line.split(':')[-1].strip()
            
            # If we can't determine from remote, check if main or master exists
            for branch in ['main', 'master']:
                result = subprocess.run(
                    ['git', '-C', repo_dir, 'rev-parse', '--verify', branch], 
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    return branch
            
            # If all else fails, return the current branch
            result = subprocess.run(
                ['git', '-C', repo_dir, 'rev-parse', '--abbrev-ref', 'HEAD'], 
                capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
            
        except subprocess.CalledProcessError:
            # If all methods fail, default to 'main'
            logger.warning("Could not determine default branch, using 'main'")
            return 'main'
    
    def get_ahead_behind(self, repo_dir, ref):
        """Get how many commits a ref is ahead/behind compared to HEAD."""
        try:
            # Make sure we have the latest refs
            subprocess.run(
                ['git', '-C', repo_dir, 'fetch', '--all', '--tags'], 
                capture_output=True, text=True
            )
            
            # Get the merge base (common ancestor)
            merge_base_result = subprocess.run(
                ['git', '-C', repo_dir, 'merge-base', 'HEAD', ref], 
                capture_output=True, text=True
            )
            
            if merge_base_result.returncode != 0:
                # If merge-base fails, try to get the commit directly
                try:
                    subprocess.run(
                        ['git', '-C', repo_dir, 'rev-parse', ref], 
                        capture_output=True, text=True, check=True
                    )
                    # If we can get the ref but not merge-base, they're unrelated
                    return {'ahead': 999, 'behind': 999}
                except subprocess.CalledProcessError:
                    # If we can't even get the ref, it doesn't exist
                    return {'ahead': 0, 'behind': 0}
            
            merge_base = merge_base_result.stdout.strip()
            
            # Get commits ahead (ref has but HEAD doesn't)
            ahead_result = subprocess.run(
                ['git', '-C', repo_dir, 'rev-list', '--count', f'HEAD..{ref}'], 
                capture_output=True, text=True
            )
            
            # Get commits behind (HEAD has but ref doesn't)
            behind_result = subprocess.run(
                ['git', '-C', repo_dir, 'rev-list', '--count', f'{ref}..HEAD'], 
                capture_output=True, text=True
            )
            
            ahead = int(ahead_result.stdout.strip()) if ahead_result.returncode == 0 else 0
            behind = int(behind_result.stdout.strip()) if behind_result.returncode == 0 else 0
            
            return {'ahead': ahead, 'behind': behind}
            
        except (subprocess.CalledProcessError, ValueError) as e:
            logger.error(f"Error calculating ahead/behind for {ref}: {str(e)}")
            return {'ahead': 0, 'behind': 0}
    
    def update_tags_ui(self):
        """Update the UI with tags and branches."""
        # Clear listboxes
        self.repo1_tags_listbox.delete(0, tk.END)
        self.repo2_tags_listbox.delete(0, tk.END)
        
        # Get max commits behind filter
        try:
            max_behind = int(self.max_commits_behind.get())
        except ValueError:
            max_behind = 100  # Default if invalid input
        
        # Filter and populate repo1 tags
        filtered_tags1 = self.filter_tags_by_search(self.repo1_tags, self.repo1_search.get())
        filtered_tags1 = [tag for tag in filtered_tags1 if tag['behind'] <= max_behind]
        
        # Sort tags: default branch first, then branches, then tags
        filtered_tags1 = sorted(filtered_tags1, key=lambda x: (
            0 if x['name'] in ['main', 'master'] else 
            1 if '/' not in x['name'] else 
            2
        ))
        
        for tag in filtered_tags1:
            display_name = f"{tag['name']} (+{tag['ahead']}/-{tag['behind']})"
            self.repo1_tags_listbox.insert(tk.END, display_name)
        
        # Filter and populate repo2 tags
        filtered_tags2 = self.filter_tags_by_search(self.repo2_tags, self.repo2_search.get())
        filtered_tags2 = [tag for tag in filtered_tags2 if tag['behind'] <= max_behind]
        
        # Sort tags: default branch first, then branches, then tags
        filtered_tags2 = sorted(filtered_tags2, key=lambda x: (
            0 if x['name'] in ['main', 'master'] else 
            1 if '/' not in x['name'] else 
            2
        ))
        
        for tag in filtered_tags2:
            display_name = f"{tag['name']} (+{tag['ahead']}/-{tag['behind']})"
            self.repo2_tags_listbox.insert(tk.END, display_name)
        
        # If no tags were found, show a message
        if not filtered_tags1:
            self.repo1_tags_listbox.insert(tk.END, "No branches or tags found")
        
        if not filtered_tags2:
            self.repo2_tags_listbox.insert(tk.END, "No branches or tags found")
    
    def filter_tags_by_search(self, tags, search_text):
        """Filter tags by search text."""
        if not search_text:
            return tags
        search_text = search_text.lower()
        return [tag for tag in tags if search_text in tag['name'].lower()]
    
    def filter_tags(self, repo_num):
        """Filter tags based on search text."""
        self.update_tags_ui()
    
    def apply_filter(self):
        """Apply filter to tags."""
        self.update_tags_ui()
    
    def on_tag_select(self, repo_num):
        """Handle tag selection."""
        if repo_num == 1:
            selected_indices = self.repo1_tags_listbox.curselection()
            if selected_indices:
                selected_index = selected_indices[0]
                selected_tag = self.repo1_tags_listbox.get(selected_index)
                # Extract tag name from display string
                tag_name = selected_tag.split(" (+")[0]
                self.repo1_selected_tag.set(tag_name)
        else:
            selected_indices = self.repo2_tags_listbox.curselection()
            if selected_indices:
                selected_index = selected_indices[0]
                selected_tag = self.repo2_tags_listbox.get(selected_index)
                # Extract tag name from display string
                tag_name = selected_tag.split(" (+")[0]
                self.repo2_selected_tag.set(tag_name)
    
    def generate_difference(self):
        """Generate difference between repositories."""
        threading.Thread(target=self._generate_difference_thread).start()
    
    def _generate_difference_thread(self):
        """Generate difference between repositories."""
        self.update_status("Generating difference...")
        
        # Check if tags are selected
        if not self.repo1_selected_tag.get():
            messagebox.showerror("Error", "Please select a tag/branch for Repository 1")
            self.update_status("Ready")
            return
        
        if not self.repo2_selected_tag.get():
            messagebox.showerror("Error", "Please select a tag/branch for Repository 2")
            self.update_status("Ready")
            return
        
        # Get repo directories
        repo1_dir = self.get_repo_dir(self.repo1_path.get().strip())
        if not repo1_dir:
            self.update_status("Failed to access Repository 1")
            return
        
        repo2_dir = self.get_repo_dir(self.repo2_path.get().strip())
        if not repo2_dir:
            self.update_status("Failed to access Repository 2")
            return
        
        # Create output directory on desktop
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(desktop_path, f"repo_diff_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Create subdirectories based on comparison direction
        if self.comparison_direction.get() in ["1to2", "both"]:
            os.makedirs(os.path.join(output_dir, "repo1_unique"), exist_ok=True)
        
        if self.comparison_direction.get() in ["2to1", "both"]:
            os.makedirs(os.path.join(output_dir, "repo2_unique"), exist_ok=True)
        
        # Create temporary working directories
        temp_repo1 = os.path.join(self.temp_dir, "temp_repo1")
        temp_repo2 = os.path.join(self.temp_dir, "temp_repo2")
        
        # Clean up any existing temp directories
        if os.path.exists(temp_repo1):
            shutil.rmtree(temp_repo1, ignore_errors=True)
        if os.path.exists(temp_repo2):
            shutil.rmtree(temp_repo2, ignore_errors=True)
            
        os.makedirs(temp_repo1, exist_ok=True)
        os.makedirs(temp_repo2, exist_ok=True)
        
        # Clone repositories to temporary directories with specific tags/branches
        self.update_status("Preparing repositories...")
        
        try:
            # For repo1
            self.prepare_repo_for_comparison(
                self.repo1_path.get().strip(),
                repo1_dir,
                temp_repo1,
                self.repo1_selected_tag.get()
            )
            
            # For repo2
            self.prepare_repo_for_comparison(
                self.repo2_path.get().strip(),
                repo2_dir,
                temp_repo2,
                self.repo2_selected_tag.get()
            )
                
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to prepare repositories: {e.stderr if hasattr(e, 'stderr') else str(e)}"
            logger.error(error_msg)
            messagebox.showerror("Error", error_msg)
            self.update_status("Failed to generate difference")
            return
        
        # Compare repositories
        self.update_status("Comparing repositories...")
        
        # Files in repo1 but not in repo2
        if self.comparison_direction.get() in ["1to2", "both"]:
            self.update_status("Finding files in Repository 1 not in Repository 2...")
            self.find_unique_files(temp_repo1, temp_repo2, os.path.join(output_dir, "repo1_unique"))
        
        # Files in repo2 but not in repo1
        if self.comparison_direction.get() in ["2to1", "both"]:
            self.update_status("Finding files in Repository 2 not in Repository 1...")
            self.find_unique_files(temp_repo2, temp_repo1, os.path.join(output_dir, "repo2_unique"))
        
        # Create a summary file
        self.create_comparison_summary(output_dir, temp_repo1, temp_repo2)
        
        # Clean up temporary directories
        self.update_status("Cleaning up...")
        shutil.rmtree(temp_repo1, ignore_errors=True)
        shutil.rmtree(temp_repo2, ignore_errors=True)
        
        # Open output directory
        self.update_status("Difference generated successfully")
        os.startfile(output_dir)
    
    def prepare_repo_for_comparison(self, repo_path, repo_dir, temp_dir, selected_ref):
        """Prepare a repository for comparison by checking out the selected ref."""
        logger.info(f"Preparing repository {repo_path} with ref {selected_ref}")
        
        try:
            if self.is_url(repo_path):
                # For URL repositories, clone with the selected ref
                subprocess.run(
                    ['git', 'clone', repo_path, temp_dir], 
                    check=True, capture_output=True, text=True
                )
                
                # Try to checkout the selected ref
                checkout_result = subprocess.run(
                    ['git', '-C', temp_dir, 'checkout', selected_ref], 
                    capture_output=True, text=True
                )
                
                if checkout_result.returncode != 0:
                    # If direct checkout fails, try to fetch and checkout
                    logger.warning(f"Direct checkout failed: {checkout_result.stderr}")
                    
                    # Try to fetch the specific ref
                    subprocess.run(
                        ['git', '-C', temp_dir, 'fetch', 'origin', selected_ref], 
                        check=True, capture_output=True, text=True
                    )
                    
                    # Try to checkout again
                    checkout_result = subprocess.run(
                        ['git', '-C', temp_dir, 'checkout', selected_ref], 
                        capture_output=True, text=True
                    )
                    
                    if checkout_result.returncode != 0:
                        # If it still fails, try to checkout FETCH_HEAD
                        logger.warning(f"Fetch and checkout failed: {checkout_result.stderr}")
                        subprocess.run(
                            ['git', '-C', temp_dir, 'checkout', 'FETCH_HEAD'], 
                            check=True, capture_output=True, text=True
                        )
            else:
                # For local repositories, create a copy and checkout
                self.copy_git_repo(repo_dir, temp_dir)
                
                # Try to checkout the selected ref
                checkout_result = subprocess.run(
                    ['git', '-C', temp_dir, 'checkout', selected_ref], 
                    capture_output=True, text=True
                )
                
                if checkout_result.returncode != 0:
                    # If checkout fails, try to fetch first
                    logger.warning(f"Local checkout failed: {checkout_result.stderr}")
                    
                    # Try to fetch all refs
                    subprocess.run(
                        ['git', '-C', temp_dir, 'fetch', '--all'], 
                        check=True, capture_output=True, text=True
                    )
                    
                    # Try to checkout again
                    checkout_result = subprocess.run(
                        ['git', '-C', temp_dir, 'checkout', selected_ref], 
                        capture_output=True, text=True
                    )
        except subprocess.CalledProcessError as e:
            error_msg = f"Error preparing repository: {e.stderr if hasattr(e, 'stderr') else str(e)}"
            logger.error(error_msg)
            raise
    
    def create_comparison_summary(self, output_dir, repo1_dir, repo2_dir):
        """Create a summary file with information about the comparison."""
        summary_path = os.path.join(output_dir, "comparison_summary.txt")
        
        with open(summary_path, 'w') as f:
            f.write("Repository Comparison Summary\n")
            f.write("============================\n\n")
            
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("Repository 1:\n")
            f.write(f"  Path: {self.repo1_path.get()}\n")
            f.write(f"  Branch/Tag: {self.repo1_selected_tag.get()}\n\n")
            
            f.write("Repository 2:\n")
            f.write(f"  Path: {self.repo2_path.get()}\n")
            f.write(f"  Branch/Tag: {self.repo2_selected_tag.get()}\n\n")
            
            f.write("Comparison Direction:\n")
            if self.comparison_direction.get() == "1to2":
                f.write("  Files in Repository 1 not in Repository 2\n\n")
            elif self.comparison_direction.get() == "2to1":
                f.write("  Files in Repository 2 not in Repository 1\n\n")
            else:
                f.write("  Both directions (all differences)\n\n")
            
            # Count unique files
            repo1_unique_count = 0
            repo2_unique_count = 0
            
            if self.comparison_direction.get() in ["1to2", "both"]:
                repo1_unique_dir = os.path.join(output_dir, "repo1_unique")
                for root, dirs, files in os.walk(repo1_unique_dir):
                    repo1_unique_count += len(files)
            
            if self.comparison_direction.get() in ["2to1", "both"]:
                repo2_unique_dir = os.path.join(output_dir, "repo2_unique")
                for root, dirs, files in os.walk(repo2_unique_dir):
                    repo2_unique_count += len(files)
            
            f.write("Results Summary:\n")
            if self.comparison_direction.get() in ["1to2", "both"]:
                f.write(f"  Files unique to Repository 1: {repo1_unique_count}\n")
            if self.comparison_direction.get() in ["2to1", "both"]:
                f.write(f"  Files unique to Repository 2: {repo2_unique_count}\n")
            
            f.write(f"\nTotal unique files: {repo1_unique_count + repo2_unique_count}\n")
    
    def copy_git_repo(self, source_repo, target_dir):
        """Create a copy of a git repository for comparison"""
        logger.info(f"Copying repository from {source_repo} to {target_dir}")
        
        try:
            # Initialize a new git repository in the target directory
            subprocess.run(['git', 'init', target_dir], 
                          check=True, capture_output=True, text=True)
            
            # Add the source repository as a remote
            subprocess.run(['git', '-C', target_dir, 'remote', 'add', 'origin', source_repo], 
                          check=True, capture_output=True, text=True)
            
            # Fetch all branches and tags
            subprocess.run(['git', '-C', target_dir, 'fetch', '--all'], 
                          check=True, capture_output=True, text=True)
            
            # Fetch all tags
            subprocess.run(['git', '-C', target_dir, 'fetch', '--tags'], 
                          check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            error_msg = f"Error copying repository: {e.stderr if hasattr(e, 'stderr') else str(e)}"
            logger.error(error_msg)
            raise
    
    def find_unique_files(self, source_repo, target_repo, output_dir):
        """Find files that exist in source_repo but not in target_repo and copy them to output_dir"""
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
    
    def update_status(self, message):
        """Update the status bar with a message"""
        logger.info(message)
        self.status_text.set(message)
        self.root.update_idletasks()
    
    def cleanup(self):
        """Clean up temporary directories"""
        logger.info("Cleaning up temporary directories")
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def refresh_github_repos(self):
        """Refresh the list of GitHub repositories."""
        if not self.github_handler:
            messagebox.showerror("Error", "GitHub integration not available. Please set GITHUB_TOKEN environment variable.")
            return
            
        try:
            self.update_status("Fetching repositories...")
            self.github_repos = self.github_handler.get_user_repos()
            
            self.repo_listbox.delete(0, tk.END)
            for repo in self.github_repos:
                self.repo_listbox.insert(tk.END, repo.full_name)
                
            self.update_status("Repositories refreshed successfully")
            
            # Set up selection handler
            self.repo_listbox.bind('<<ListboxSelect>>', self.on_repo_select)
        except Exception as e:
            error_msg = f"Error fetching repositories: {str(e)}"
            logger.error(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def on_repo_select(self, event):
        """Handle repository selection."""
        if not self.repo_listbox.curselection():
            return
            
        try:
            index = self.repo_listbox.curselection()[0]
            self.selected_repo = self.github_repos[index]
            self.update_status(f"Selected repository: {self.selected_repo.full_name}")
            
            # Fetch branches
            self.repo_branches = self.github_handler.get_repo_branches(self.selected_repo)
            
            # Update branch listboxes
            self.base_branch_listbox.delete(0, tk.END)
            self.compare_branch_listbox.delete(0, tk.END)
            
            for branch in self.repo_branches:
                self.base_branch_listbox.insert(tk.END, branch.name)
                self.compare_branch_listbox.insert(tk.END, branch.name)
        except Exception as e:
            error_msg = f"Error loading repository details: {str(e)}"
            logger.error(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def compare_branches(self):
        """Compare selected branches and show commits."""
        if not self.selected_repo:
            messagebox.showerror("Error", "Please select a repository first")
            return
            
        if not self.base_branch_listbox.curselection() or not self.compare_branch_listbox.curselection():
            messagebox.showerror("Error", "Please select both base and compare branches")
            return
            
        try:
            base_branch = self.repo_branches[self.base_branch_listbox.curselection()[0]].name
            compare_branch = self.repo_branches[self.compare_branch_listbox.curselection()[0]].name
            
            self.update_status(f"Comparing branches {base_branch} and {compare_branch}...")
            
            ahead_by, behind_by, commits = self.github_handler.get_branch_comparison(
                self.selected_repo, base_branch, compare_branch)
                
            self.ahead_label.config(text=f"Ahead by: {ahead_by}")
            self.behind_label.config(text=f"Behind by: {behind_by}")
            
            self.commits_listbox.delete(0, tk.END)
            self.comparison_commits = commits
            
            for commit in commits:
                self.commits_listbox.insert(tk.END, f"{commit.sha[:7]} - {commit.commit.message.split('\n')[0]}")
                
            self.update_status("Branch comparison complete")
        except Exception as e:
            error_msg = f"Error comparing branches: {str(e)}"
            logger.error(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def apply_selected_commit(self):
        """Apply the selected commit and show statistics."""
        if not self.commits_listbox.curselection():
            messagebox.showerror("Error", "Please select a commit to apply")
            return
            
        try:
            index = self.commits_listbox.curselection()[0]
            commit = self.comparison_commits[index]
            
            self.update_status(f"Applying commit {commit.sha[:7]}...")
            
            stats = self.github_handler.apply_commit(self.selected_repo, commit)
            
            success_msg = (
                f"Successfully applied commit!\n\n"
                f"Files changed: {stats['files_changed']}\n"
                f"Additions: {stats['additions']}\n"
                f"Deletions: {stats['deletions']}\n"
                f"Total changes: {stats['total']}"
            )
            
            messagebox.showinfo("Success", success_msg)
            
            # Refresh the comparison
            self.compare_branches()
        except Exception as e:
            error_msg = f"Error applying commit: {str(e)}"
            logger.error(error_msg)
            messagebox.showerror("Error", error_msg)

def main():
    root = tk.Tk()
    app = RepoComparisonTool(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.cleanup(), root.destroy()))
    root.mainloop()

if __name__ == "__main__":
    main()
