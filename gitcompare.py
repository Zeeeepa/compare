import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import webbrowser
import threading
import json
import datetime
import time
import logging
import tempfile
import subprocess
from github import Github, GithubException
from functools import partial


# Import the new modules
from thread_pool import ThreadPool, Task
from merge_operations import MergeOperations, MergeStrategy


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.expanduser("~"), ".github_compare.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GitHubCompare")

class GitHubCompare:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Branch Comparison Tool")
        self.root.geometry("1000x700")  # Larger default window size
        
        # Initialize variables
        self.github_token = ""
        self.g = None
        self.cache = {
            "repos": [],
            "branches": {},
            "last_updated": None
        }
        
        # Load token from config file
        self.config_file = os.path.join(os.path.expanduser("~"), ".github_compare_config")
        self.load_config()
        
        # Create main frame with status bar
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create progress bar (hidden by default)
        self.progress = ttk.Progressbar(self.root, mode="indeterminate")
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(pady=10, expand=True, fill="both")
        
        # Create tabs
        self.local_tab = ttk.Frame(self.notebook)
        self.origin_tab = ttk.Frame(self.notebook)
        self.commit_list_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.local_tab, text="Local Compare")
        self.notebook.add(self.origin_tab, text="Origin Compare")
        self.notebook.add(self.commit_list_tab, text="Commit List")
        
        # Setup tabs
        self.setup_local_tab()
        self.setup_origin_tab()
        self.setup_commit_list_tab()
        
        # Add settings button and refresh button
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        settings_btn = ttk.Button(button_frame, text="⚙️ Settings", command=self.show_settings)
        settings_btn.pack(side=tk.LEFT, padx=5)
        
        refresh_btn = ttk.Button(button_frame, text="🔄 Refresh", command=self.refresh_data)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        

        # Initialize thread pool
        self.thread_pool = ThreadPool(num_workers=5)
        self.merge_operations = None  # Will be initialized when GitHub client is initialized
        
        # Initialize GitHub client if token exists
        if self.github_token:
            self.init_github_client()

    def setup_local_tab(self):
        # Create frames for better organization
        top_frame = ttk.Frame(self.local_tab)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Repository selection
        repo_frame = ttk.LabelFrame(top_frame, text="Repository Selection")
        repo_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side=tk.LEFT, padx=5)
        self.repo_var = tk.StringVar()
        self.repo_combo = ttk.Combobox(repo_frame, textvariable=self.repo_var, width=50)
        self.repo_combo.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        self.repo_combo.bind('<<ComboboxSelected>>', self.update_branches)
        
        # Add a search entry for repositories
        ttk.Label(repo_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.repo_search_var = tk.StringVar()
        self.repo_search_var.trace("w", self.filter_repos)
        repo_search_entry = ttk.Entry(repo_frame, textvariable=self.repo_search_var, width=20)
        repo_search_entry.pack(side=tk.LEFT, padx=5)
        
        # Branch selection
        branch_frame = ttk.LabelFrame(top_frame, text="Branch Selection")
        branch_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(branch_frame, text="Base Branch:").pack(side=tk.LEFT, padx=5)
        self.base_branch_var = tk.StringVar()
        self.base_branch_combo = ttk.Combobox(branch_frame, textvariable=self.base_branch_var, width=30)
        self.base_branch_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(branch_frame, text="Compare Branch:").pack(side=tk.LEFT, padx=5)
        self.compare_branch_var = tk.StringVar()
        self.compare_branch_combo = ttk.Combobox(branch_frame, textvariable=self.compare_branch_var, width=30)
        self.compare_branch_combo.pack(side=tk.LEFT, padx=5)
        
        # Compare button and filter options
        action_frame = ttk.Frame(top_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        compare_btn = ttk.Button(action_frame, text="Compare Branches", command=self.compare_branches)
        create_pr_btn = ttk.Button(action_frame, text="Create PR", command=lambda: self.show_pr_dialog(self.compare_branch_var.get(), self.base_branch_var.get()))
        create_pr_btn.pack(side=tk.LEFT, padx=5)
        compare_btn.pack(side=tk.LEFT, padx=5)
        
        # Add filter options
        self.only_show_recent_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(action_frame, text="Only Recent Commits", variable=self.only_show_recent_var, 
                      command=self.refresh_commits_display).pack(side=tk.LEFT, padx=5)
        
        self.only_show_verified_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(action_frame, text="Only Verified Commits", variable=self.only_show_verified_var,
                      command=self.refresh_commits_display).pack(side=tk.LEFT, padx=5)
        
        # Results frame with summary and commits
        results_frame = ttk.LabelFrame(self.local_tab, text="Comparison Results")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Summary section
        self.summary_frame = ttk.Frame(results_frame)
        self.summary_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.summary_label = ttk.Label(self.summary_frame, text="No comparison results yet")
        self.summary_label.pack(anchor=tk.W)
        
        # Create a frame for the commits with a scrollbar
        commits_frame = ttk.Frame(results_frame)
        commits_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create canvas and scrollbar for scrolling
        self.commits_canvas = tk.Canvas(commits_frame)
        scrollbar = ttk.Scrollbar(commits_frame, orient=tk.VERTICAL, command=self.commits_canvas.yview)
        self.commits_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.commits_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Frame inside canvas for commits
        self.local_commits_frame = ttk.Frame(self.commits_canvas)
        self.commits_canvas_window = self.commits_canvas.create_window((0, 0), window=self.local_commits_frame, anchor=tk.NW)
        
        # Configure scrolling
        self.local_commits_frame.bind("<Configure>", lambda e: self.commits_canvas.configure(scrollregion=self.commits_canvas.bbox("all")))
        self.commits_canvas.bind("<Configure>", self.on_canvas_configure)
        
        # Bind mousewheel scrolling
        self.commits_canvas.bind_all("<MouseWheel>", lambda event: self.commits_canvas.yview_scroll(int(-1*(event.delta/120)), "units"))
        
    def on_canvas_configure(self, event):
        # Update the width of the canvas window when the canvas size changes
        self.commits_canvas.itemconfig(self.commits_canvas_window, width=event.width)

    def setup_origin_tab(self):
        # Similar structure to local tab but for origin comparison
        top_frame = ttk.Frame(self.origin_tab)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Repository selection
        repo_frame = ttk.LabelFrame(top_frame, text="Repository Selection")
        repo_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side=tk.LEFT, padx=5)
        self.origin_repo_var = tk.StringVar()
        self.origin_repo_combo = ttk.Combobox(repo_frame, textvariable=self.origin_repo_var, width=50)
        self.origin_repo_combo.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        self.origin_repo_combo.bind('<<ComboboxSelected>>', self.update_origin_info)
        
        # Origin label to show parent repository
        self.origin_info_label = ttk.Label(repo_frame, text="")
        self.origin_info_label.pack(side=tk.LEFT, padx=5)
        
        # Branch selection
        branch_frame = ttk.LabelFrame(top_frame, text="Branch Selection")
        branch_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(branch_frame, text="Base Branch:").pack(side=tk.LEFT, padx=5)
        self.origin_base_branch_var = tk.StringVar()
        self.origin_base_branch_combo = ttk.Combobox(branch_frame, textvariable=self.origin_base_branch_var, width=30)
        self.origin_base_branch_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(branch_frame, text="Origin Branch:").pack(side=tk.LEFT, padx=5)
        self.origin_compare_branch_var = tk.StringVar()
        self.origin_compare_branch_combo = ttk.Combobox(branch_frame, textvariable=self.origin_compare_branch_var, width=30)
        self.origin_compare_branch_combo.pack(side=tk.LEFT, padx=5)
        
        # Compare button and filter options
        action_frame = ttk.Frame(top_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        create_pr_btn = ttk.Button(action_frame, text="Create PR", command=lambda: self.show_pr_dialog(self.origin_compare_branch_var.get(), self.origin_base_branch_var.get()))
        create_pr_btn.pack(side=tk.LEFT, padx=5)
        
        compare_btn = ttk.Button(action_frame, text="Compare with Origin", command=self.compare_with_origin)
        compare_btn.pack(side=tk.LEFT, padx=5)
        
        # Add filter options (same as local tab)
        self.origin_only_show_recent_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(action_frame, text="Only Recent Commits", variable=self.origin_only_show_recent_var, 
                       command=self.refresh_origin_commits_display).pack(side=tk.LEFT, padx=5)
        
        self.origin_only_show_verified_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(action_frame, text="Only Verified Commits", variable=self.origin_only_show_verified_var,
                       command=self.refresh_origin_commits_display).pack(side=tk.LEFT, padx=5)
        
        # Create PR button
        self.create_pr_btn = ttk.Button(action_frame, text="Create Pull Request", command=self.create_pull_request)
        self.create_pr_btn.pack(side=tk.LEFT, padx=5)
        self.create_pr_btn.config(state=tk.DISABLED) # Initially disabled until comparison is done
        
        # Results frame with summary and commits
        results_frame = ttk.LabelFrame(self.origin_tab, text="Comparison Results")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Summary section
        self.origin_summary_frame = ttk.Frame(results_frame)
        self.origin_summary_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.origin_summary_label = ttk.Label(self.origin_summary_frame, text="No comparison results yet")
        self.origin_summary_label.pack(anchor=tk.W)
        
        # Create a frame for the commits with a scrollbar
        commits_frame = ttk.Frame(results_frame)
        commits_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create canvas and scrollbar for scrolling
        self.origin_commits_canvas = tk.Canvas(commits_frame)
        scrollbar = ttk.Scrollbar(commits_frame, orient=tk.VERTICAL, command=self.origin_commits_canvas.yview)
        self.origin_commits_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.origin_commits_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Frame inside canvas for commits
        self.origin_commits_frame = ttk.Frame(self.origin_commits_canvas)
        self.origin_commits_canvas_window = self.origin_commits_canvas.create_window((0, 0), window=self.origin_commits_frame, anchor=tk.NW)
        
        # Configure scrolling
        self.origin_commits_frame.bind("<Configure>", lambda e: self.origin_commits_canvas.configure(scrollregion=self.origin_commits_canvas.bbox("all")))
        self.origin_commits_canvas.bind("<Configure>", self.on_origin_canvas_configure)
        
        # Bind mousewheel scrolling
        self.origin_commits_canvas.bind_all("<MouseWheel>", lambda event: self.origin_commits_canvas.yview_scroll(int(-1*(event.delta/120)), "units"))

    def on_origin_canvas_configure(self, event):
        # Update the width of the canvas window when the canvas size changes
        self.origin_commits_canvas.itemconfig(self.origin_commits_canvas_window, width=event.width)
        
    def init_github_client(self):
        """Initialize GitHub client with validation"""
        try:
            self.status_var.set("Validating GitHub token...")
            self.root.update()
            
            self.g = Github(self.github_token)
            # Test connection by getting user info
            user = self.g.get_user().login
            self.status_var.set(f"Connected as {user}")
            
            # Load cache or update data
            if not self.load_cache():
                self.update_repos()
            
        except Exception as e:
            self.status_var.set("Invalid GitHub token")
            messagebox.showerror("Authentication Error", f"GitHub token validation failed: {str(e)}")
            self.show_settings()

    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.github_token = config.get('token', '')
        except Exception as e:
            print(f"Error loading config: {e}")

    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump({'token': self.github_token}, f)
            os.chmod(self.config_file, 0o600)  # Set secure permissions
        except Exception as e:
            print(f"Error saving config: {e}")

    def load_cache(self):
        """Load cached data if available and not expired"""
        cache_file = os.path.join(os.path.expanduser("~"), ".github_compare_cache")
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    self.cache = json.load(f)
                
                # Check if cache is still valid (less than 1 hour old)
                if self.cache.get('last_updated'):
                    last_updated = datetime.datetime.fromisoformat(self.cache['last_updated'])
                    if (datetime.datetime.now() - last_updated).total_seconds() < 3600:
                        # Cache is valid, update UI
                        self.repo_combo['values'] = self.cache['repos']
                        self.origin_repo_combo['values'] = self.cache['repos']
                        self.commit_list_repo_combo['values'] = self.cache['repos']  # Add this line
                        self.status_var.set("Data loaded from cache")
                        return True
        except Exception as e:
            print(f"Error loading cache: {e}")
        
        return False

    def save_cache(self):
        """Save data cache to file"""
        cache_file = os.path.join(os.path.expanduser("~"), ".github_compare_cache")
        try:
            self.cache['last_updated'] = datetime.datetime.now().isoformat()
            with open(cache_file, 'w') as f:
                json.dump(self.cache, f)
        except Exception as e:
            print(f"Error saving cache: {e}")

    def start_progress(self, message="Working..."):
        """Start progress indicator"""
        self.status_var.set(message)
        self.progress.pack(before=self.status_bar, fill=tk.X)
        self.progress.start(10)
        self.root.update()
        
    def stop_progress(self, message="Ready"):
        """Stop progress indicator"""
        self.progress.stop()
        self.progress.pack_forget()
        self.status_var.set(message)
        self.root.update()

    def run_in_thread(self, func, *args, message="Working...", success_message="Complete", **kwargs):
        """Run a function in a background thread with progress indication"""
        self.start_progress(message)
        
        def thread_func():
            try:
                result = func(*args, **kwargs)
                self.root.after(0, lambda: self.stop_progress(success_message))
                return result
            except Exception as e:
                error_message = str(e)  # Capture the error message
                self.root.after(0, lambda error_msg=error_message: 
                            self.handle_error(Exception(error_msg)))
                return None
                
        thread = threading.Thread(target=thread_func)
        thread.daemon = True
        thread.start()
        return thread

    def handle_error(self, error):
        """Handle and display errors"""
        self.stop_progress(f"Error: {str(error)}")
        messagebox.showerror("Error", str(error))
        print(f"Error details: {error}")

    def update_repos(self):
        """Update repository list from GitHub"""
        def fetch_repos():
            try:
                # Fetch repositories with pagination
                user = self.g.get_user()
                repos = []
                
                # Get both user repositories and organization repositories
                for repo in user.get_repos():
                    repos.append(repo.full_name)
                
                # Get organizations the user belongs to
                for org in user.get_orgs():
                    for repo in org.get_repos():
                        repos.append(repo.full_name)
                
                # Sort repositories by name
                repos.sort()
                
                # Update cache
                self.cache['repos'] = repos
                self.save_cache()
                
                # Update UI in main thread
                self.root.after(0, lambda: self.update_repo_dropdowns(repos))
                
            except Exception as e:
                raise Exception(f"Failed to fetch repositories: {str(e)}")
        
        # Run in background thread
        self.run_in_thread(fetch_repos, message="Fetching repositories...", success_message="Repositories updated")
    
    def update_repo_dropdowns(self, repos):
        """Update repository dropdowns with fetched data"""
        self.repo_combo['values'] = repos
        self.origin_repo_combo['values'] = repos
        self.commit_list_repo_combo['values'] = repos
    
    def filter_repos(self, *args):
        """Filter repositories based on search term"""
        search_term = self.repo_search_var.get().lower()
        if not search_term:
            self.repo_combo['values'] = self.cache['repos']
            self.origin_repo_combo['values'] = self.cache['repos']
            return
        
        filtered_repos = [repo for repo in self.cache['repos'] if search_term in repo.lower()]
        self.repo_combo['values'] = filtered_repos
        self.origin_repo_combo['values'] = filtered_repos

    def update_branches(self, event=None):
        """Update branch lists when repository is selected"""
        repo_name = self.repo_var.get()
        if not repo_name:
            return
            
        def fetch_branches():
            try:
                # Check if branches are cached
                if repo_name in self.cache['branches']:
                    branches = self.cache['branches'][repo_name]
                else:
                    repo = self.g.get_repo(repo_name)
                    branches = [branch.name for branch in repo.get_branches()]
                    self.cache['branches'][repo_name] = branches
                    self.save_cache()
                
                # Update UI in main thread
                self.root.after(0, lambda: self.update_branch_dropdowns(branches, repo_name))
                
            except Exception as e:
                raise Exception(f"Failed to fetch branches: {str(e)}")
        
        # Run in background thread
        self.run_in_thread(fetch_branches, message=f"Fetching branches for {repo_name}...", 
                         success_message=f"Branches updated for {repo_name}")

    def update_branch_dropdowns(self, branches, repo_name):
        """Update branch dropdowns with fetched data"""
        self.base_branch_combo['values'] = branches
        self.compare_branch_combo['values'] = branches
        
        # Set default branch
        try:
            default_branch = self.g.get_repo(repo_name).default_branch
            self.base_branch_var.set(default_branch)
        except:
            if branches:
                self.base_branch_var.set(branches[0])

    def update_origin_info(self, event=None):
        """Update origin repository information when repository is selected"""
        repo_name = self.origin_repo_var.get()
        if not repo_name:
            return
            
        def fetch_origin_info():
            try:
                repo = self.g.get_repo(repo_name)
                parent = repo.parent
                
                if parent:
                    # It's a fork - get branches from both repos
                    repo_branches = [branch.name for branch in repo.get_branches()]
                    parent_branches = [branch.name for branch in parent.get_branches()]
                    
                    # Cache the branches
                    self.cache['branches'][repo_name] = repo_branches
                    self.cache['branches'][parent.full_name] = parent_branches
                    self.save_cache()
                    
                    # Update UI in main thread
                    self.root.after(0, lambda: self.update_origin_dropdowns(
                        repo_branches, parent_branches, repo, parent))
                else:
                    # Not a fork
                    self.root.after(0, lambda: self.handle_not_fork(repo_name))
                
            except Exception as e:
                raise Exception(f"Failed to fetch origin info: {str(e)}")
        
        # Run in background thread
        self.run_in_thread(fetch_origin_info, message=f"Fetching origin info for {repo_name}...", 
                         success_message=f"Origin info updated for {repo_name}")

    def update_origin_dropdowns(self, repo_branches, parent_branches, repo, parent):
        """Update origin branch dropdowns with fetched data"""
        # Update branch dropdowns
        self.origin_base_branch_combo['values'] = repo_branches
        self.origin_compare_branch_combo['values'] = parent_branches
        
        # Set default values
        if repo_branches:
            self.origin_base_branch_var.set(repo_branches[0])
        if parent_branches:
            # Try to set same branch name as base if exists in parent
            base_branch = self.origin_base_branch_var.get()
            if base_branch in parent_branches:
                self.origin_compare_branch_var.set(base_branch)
            else:
                self.origin_compare_branch_var.set(parent_branches[0])
        
        # Update origin info label
        self.origin_info_label.config(text=f"Parent: {parent.full_name}")
        
        # Store parent info for later use
        self.current_parent = parent
        self.current_fork = repo

    def handle_not_fork(self, repo_name):
        """Handle case when selected repository is not a fork"""
        messagebox.showinfo("Not a Fork", 
                          f"Repository '{repo_name}' is not a fork. Please select a forked repository for origin comparison.")
        
        # Clear origin info
        self.origin_info_label.config(text="Not a fork")
        self.origin_base_branch_combo['values'] = []
        self.origin_compare_branch_combo['values'] = []
        self.origin_base_branch_var.set("")
        self.origin_compare_branch_var.set("")
        
        # Disable PR button
        self.create_pr_btn.config(state=tk.DISABLED)

    def show_settings(self):
        """Show settings dialog"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("500x200")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Make dialog modal
        settings_window.focus_set()
        
        # Add GitHub token input
        frame = ttk.Frame(settings_window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="GitHub Personal Access Token:").pack(anchor=tk.W, pady=5)
        
        # Token entry with show/hide toggle
        token_frame = ttk.Frame(frame)
        token_frame.pack(fill=tk.X, pady=5)
        
        token_var = tk.StringVar(value=self.github_token)
        token_entry = ttk.Entry(token_frame, textvariable=token_var, width=50, show="*")
        token_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Show/hide token button
        self.show_token = tk.BooleanVar(value=False)
        
        def toggle_token_visibility():
            if self.show_token.get():
                token_entry.config(show="")
            else:
                token_entry.config(show="*")
        
        show_btn = ttk.Checkbutton(token_frame, text="Show", variable=self.show_token, 
                                 command=toggle_token_visibility)
        show_btn.pack(side=tk.LEFT, padx=5)
        
        # Help text
        help_text = "A GitHub Personal Access Token is required to use this tool. "\
                  "It needs 'repo' scope permissions to access your repositories."
        ttk.Label(frame, text=help_text, wraplength=480).pack(anchor=tk.W, pady=10)
        
        # Link to GitHub token creation page
        link_text = "Create a token on GitHub"
        link_label = ttk.Label(frame, text=link_text, foreground="blue", cursor="hand2")
        link_label.pack(anchor=tk.W)
        link_label.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/settings/tokens"))
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        save_btn = ttk.Button(btn_frame, text="Save", command=lambda: self.save_token(token_var.get(), settings_window))
        save_btn.pack(side=tk.RIGHT, padx=5)
        
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=settings_window.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        # Center the window on the screen
        settings_window.update_idletasks()
        width = settings_window.winfo_width()
        height = settings_window.winfo_height()
        x = (settings_window.winfo_screenwidth() // 2) - (width // 2)
        y = (settings_window.winfo_screenheight() // 2) - (height // 2)
        settings_window.geometry(f'+{x}+{y}')
        
        # Initial focus on token entry
        token_entry.focus_set()
        
        # Handle window closing
        settings_window.protocol("WM_DELETE_WINDOW", settings_window.destroy)

    def save_token(self, token, window):
        """Save GitHub token and initialize client"""
        if not token:
            messagebox.showerror("Error", "Please enter a valid GitHub token")
            return
            
        self.github_token = token
        self.save_config()
        window.destroy()
        
        # Initialize GitHub client with new token
        self.init_github_client()
        
        # Update repositories list
        self.update_repos()

    def refresh_data(self):
        """Refresh all data from GitHub"""
        # Clear cache
        self.cache = {
            "repos": [],
            "branches": {},
            "last_updated": None
        }
        
        # Update repositories and branches
        self.update_repos()
        
        # Clear comparison results
        self.clear_comparison_results()
        
    def clear_comparison_results(self):
        """Clear comparison results in both tabs"""
        # Clear local tab results
        self.summary_label.config(text="No comparison results yet")
        
        # Clear all widgets in commits frame
        for widget in self.local_commits_frame.winfo_children():
            widget.destroy()
            
        # Clear origin tab results  
        self.origin_summary_label.config(text="No comparison results yet")
        
        # Clear all widgets in origin commits frame
        for widget in self.origin_commits_frame.winfo_children():
            widget.destroy()
            
        # Disable PR button
        self.create_pr_btn.config(state=tk.DISABLED)

    def compare_branches(self):
        """Compare two branches in the same repository"""
        repo_name = self.repo_var.get()
        base_branch = self.base_branch_var.get()
        compare_branch = self.compare_branch_var.get()
        
        if not repo_name or not base_branch or not compare_branch:
            messagebox.showerror("Error", "Please select repository and branches")
            return
            
        def perform_comparison():
            try:
                repo = self.g.get_repo(repo_name)
                
                # Get the comparison
                comparison = repo.compare(base_branch, compare_branch)
                
                # Store commits for filter use
                self.current_commits = comparison.commits
                
                # Update UI in main thread
                self.root.after(0, lambda: self.display_comparison_results(
                    comparison, repo_name, base_branch, compare_branch))
                
            except Exception as e:
                raise Exception(f"Failed to compare branches: {str(e)}")
        
        # Run in background thread
        self.run_in_thread(perform_comparison, 
                         message=f"Comparing {base_branch} and {compare_branch}...", 
                         success_message="Comparison complete")

    def display_comparison_results(self, comparison, repo_name, base_branch, compare_branch):
        """Display comparison results in the local tab"""
        # Clear previous results
        for widget in self.local_commits_frame.winfo_children():
            widget.destroy()
            
        # Update summary
        summary_text = f"Comparing {base_branch}...{compare_branch} in {repo_name}\n"
        summary_text += f"Status: {comparison.status}\n"
        summary_text += f"Total commits: {len(comparison.commits)}"
        
        if comparison.ahead_by is not None and comparison.behind_by is not None:
            summary_text += f" ({comparison.ahead_by} ahead, {comparison.behind_by} behind)"
            
        self.summary_label.config(text=summary_text)
        
        # Display commits based on filter settings
        self.refresh_commits_display()

    def refresh_commits_display(self):
        """Refresh the commits display based on filter settings"""
        # Clear previous results
        for widget in self.local_commits_frame.winfo_children():
            widget.destroy()
            
        if not self.current_commits:
            return
            
        # Apply filters
        filtered_commits = self.apply_commit_filters(self.current_commits)
        
        # Display commits
        self.display_commits(filtered_commits, self.local_commits_frame, is_origin=False)

    def apply_commit_filters(self, commits):
        """Apply filters to commits"""
        filtered = commits
        
        # Filter for recent commits (last 30 days) if enabled
        if self.only_show_recent_var.get():
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=30)
            filtered = [c for c in filtered if c.commit.author.date > cutoff_date]
            
        # Filter for verified commits if enabled
        if self.only_show_verified_var.get():
            filtered = [c for c in filtered if c.commit.verification and c.commit.verification.verified]
            
        return filtered

    def display_commits(self, commits, parent_frame, is_origin=False):
        """Display commits in the specified frame"""
        if not commits:
            no_commits_label = ttk.Label(parent_frame, text="No commits match the filter criteria")
            no_commits_label.pack(pady=10)
            return
            
        # Create a frame for each commit
        for i, commit in enumerate(commits):
            commit_frame = ttk.Frame(parent_frame)
            commit_frame.pack(fill=tk.X, padx=5, pady=5, anchor=tk.N)
            
            # Add a separator before each commit (except the first)
            if i > 0:
                separator = ttk.Separator(parent_frame)
                separator.pack(fill=tk.X, padx=5, pady=5, before=commit_frame)
            
            # Commit number and hash
            header_frame = ttk.Frame(commit_frame)
            header_frame.pack(fill=tk.X)
            
            commit_num = ttk.Label(header_frame, text=f"#{i+1}", font=("", 10, "bold"))
            commit_num.pack(side=tk.LEFT, padx=5)
            
            commit_hash = ttk.Label(header_frame, text=commit.sha[:7])
            commit_hash.pack(side=tk.LEFT, padx=5)
            
            # Commit message
            msg_frame = ttk.Frame(commit_frame)
            msg_frame.pack(fill=tk.X, pady=5)
            
            commit_msg = ttk.Label(msg_frame, text=commit.commit.message.split('\n')[0],
                                wraplength=800, anchor=tk.W)
            commit_msg.pack(side=tk.LEFT, padx=5)
            
            # Author and date
            info_frame = ttk.Frame(commit_frame)
            info_frame.pack(fill=tk.X)
            
            author = commit.commit.author.name
            date = commit.commit.author.date.strftime("%Y-%m-%d %H:%M:%S")
            
            author_label = ttk.Label(info_frame, text=f"{author} committed on {date}")
            author_label.pack(side=tk.LEFT, padx=5)
            
            # Stats (if available)
            if hasattr(commit, 'stats') and commit.stats:
                # Get number of files changed - we need to fetch the detailed commit to get this info
                try:
                    detailed_commit = self.g.get_repo(commit.repository.full_name).get_commit(commit.sha)
                    num_files = len(detailed_commit.files)
                    stats_text = f"{num_files} file{'s' if num_files != 1 else ''} changed: "
                    stats_text += f"+{commit.stats.additions}, -{commit.stats.deletions}"
                    
                    stats_label = ttk.Label(info_frame, text=stats_text)
                    stats_label.pack(side=tk.RIGHT, padx=5)
                except Exception:
                    # Fall back to just showing additions/deletions if we can't get file count
                    stats_text = f"{commit.stats.total} changes: "
                    stats_text += f"+{commit.stats.additions}, -{commit.stats.deletions}"
                    
                    stats_label = ttk.Label(info_frame, text=stats_text)
                    stats_label.pack(side=tk.RIGHT, padx=5)
            
            # Action buttons
            btn_frame = ttk.Frame(commit_frame)
            btn_frame.pack(fill=tk.X, pady=5)
            
            # View diff button
            view_diff_btn = ttk.Button(
                btn_frame, 
                text="View Diff", 
                command=lambda c=commit: webbrowser.open_new(c.html_url)
            )
            view_diff_btn.pack(side=tk.LEFT, padx=5)
            
            # Add merge button for origin comparison
            if is_origin and self.current_fork:
                merge_btn = ttk.Button(
                    btn_frame, 
                    text="Merge This Commit", 
                    command=lambda c=commit: self.merge_commit(c)
                )
                merge_btn.pack(side=tk.LEFT, padx=5)

    def compare_with_origin(self):
        """Compare fork with parent repository"""
        repo_name = self.origin_repo_var.get()
        base_branch = self.origin_base_branch_var.get()
        origin_branch = self.origin_compare_branch_var.get()
        
        if not repo_name or not base_branch or not origin_branch:
            messagebox.showerror("Error", "Please select repository and branches")
            return
            
        if not self.current_parent:
            messagebox.showerror("Error", "Selected repository is not a fork or parent info not available")
            return
            
        def perform_origin_comparison():
            try:
                # Get repositories
                fork_repo = self.g.get_repo(repo_name)
                parent_repo = self.current_parent
                
                # Get the comparison (parent base <- fork head)
                comparison = parent_repo.compare(origin_branch, f"{fork_repo.owner.login}:{base_branch}")
                
                # Get the reverse comparison to see what's behind (fork base <- parent head)
                reverse_comparison = fork_repo.compare(base_branch, f"{parent_repo.owner.login}:{origin_branch}")
                
                # Store commits for filter use
                self.origin_commits = reverse_comparison.commits
                
                # Update UI in main thread
                self.root.after(0, lambda: self.display_origin_comparison_results(
                    comparison, reverse_comparison, fork_repo, parent_repo, base_branch, origin_branch))
                
            except Exception as e:
                raise Exception(f"Failed to compare with origin: {str(e)}")
        
        # Run in background thread
        self.run_in_thread(perform_origin_comparison, 
                         message=f"Comparing with origin...", 
                         success_message="Origin comparison complete")

    def display_origin_comparison_results(self, comparison, reverse_comparison, fork_repo, parent_repo, base_branch, origin_branch):
        """Display origin comparison results"""
        # Clear previous results
        for widget in self.origin_commits_frame.winfo_children():
            widget.destroy()
            
        # Update summary
        fork_name = fork_repo.full_name
        parent_name = parent_repo.full_name
        
        summary_text = f"Comparing {fork_name}:{base_branch} with {parent_name}:{origin_branch}\n"
        summary_text += f"Your branch is "
        
        if comparison.ahead_by > 0:
            summary_text += f"{comparison.ahead_by} commit(s) ahead"
            
        if comparison.ahead_by > 0 and reverse_comparison.ahead_by > 0:
            summary_text += " and "
            
        if reverse_comparison.ahead_by > 0:
            summary_text += f"{reverse_comparison.ahead_by} commit(s) behind"
            
        if comparison.ahead_by == 0 and reverse_comparison.ahead_by == 0:
            summary_text += "up to date with the parent branch"
            
        self.origin_summary_label.config(text=summary_text)
        
        # Enable PR button if ahead
        if comparison.ahead_by > 0:
            self.create_pr_btn.config(state=tk.NORMAL)
        else:
            self.create_pr_btn.config(state=tk.DISABLED)
        
        # Display commits from parent that are not in fork (behind commits)
        self.refresh_origin_commits_display()

    def refresh_origin_commits_display(self):
        """Refresh the origin commits display based on filter settings"""
        # Clear previous results
        for widget in self.origin_commits_frame.winfo_children():
            widget.destroy()
            
        if not self.origin_commits:
            return
            
        # Apply filters based on the origin tab's filter settings
        only_recent = self.origin_only_show_recent_var.get()
        only_verified = self.origin_only_show_verified_var.get()
        
        filtered_commits = self.origin_commits
        
        # Filter for recent commits if enabled
        if only_recent:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=30)
            filtered_commits = [c for c in filtered_commits if c.commit.author.date > cutoff_date]
            
        # Filter for verified commits if enabled
        if only_verified:
            filtered_commits = [c for c in filtered_commits if c.commit.verification and c.commit.verification.verified]
        
        # Display filtered commits
        self.display_commits(filtered_commits, self.origin_commits_frame, is_origin=True)

    def merge_commit(self, commit):
        """Merge a specific commit from parent repo into fork"""
        if not self.current_fork or not self.current_parent:
            messagebox.showerror("Error", "Repository information missing")
            return
            
        # Ask for confirmation
        response = messagebox.askyesno(
            "Confirm Merge", 
            f"Are you sure you want to merge commit {commit.sha[:7]} into your fork?"
        )
        
        if not response:
            return
            
        def perform_merge():
            try:
                # Apply the cherry-pick via API
                base_branch = self.origin_base_branch_var.get()
                
                # Create a temporary branch from the base
                temp_branch = f"temp-merge-{commit.sha[:7]}"
                base_ref = self.current_fork.get_git_ref(f"heads/{base_branch}")
                self.current_fork.create_git_ref(f"refs/heads/{temp_branch}", base_ref.object.sha)
                
                # Cherry-pick the commit to the temp branch
                # This isn't directly supported by PyGithub, so we'll do a manual cherry-pick
                # by creating a commit with the same changes
                cherry_pick = self.current_fork.merge(
                    temp_branch,
                    commit.sha,
                    f"Cherry-pick: {commit.commit.message}"
                )
                
                # Merge temp branch back to base
                merge_result = self.current_fork.merge(
                    base_branch,
                    temp_branch,
                    f"Merge commit {commit.sha[:7]} from parent"
                )
                
                # Delete the temporary branch
                self.current_fork.get_git_ref(f"heads/{temp_branch}").delete()
                
                # Update UI in main thread
                self.root.after(0, lambda: self.after_merge())
                
                return merge_result
                
            except Exception as e:
                raise Exception(f"Failed to merge commit: {str(e)}")
        
        # Run in background thread
        self.run_in_thread(perform_merge, 
                         message=f"Merging commit {commit.sha[:7]}...", 
                         success_message=f"Commit {commit.sha[:7]} merged successfully")

    def after_merge(self):
        """Update display after merging a commit"""
        # Refresh the comparison
        self.compare_with_origin()

    def create_pull_request(self):
        """Create a pull request from fork to parent"""
        if not self.current_fork or not self.current_parent:
            messagebox.showerror("Error", "Repository information missing")
            return
            
        # Get branch names
        fork_branch = self.origin_base_branch_var.get()
        parent_branch = self.origin_compare_branch_var.get()
        
        # Create PR dialog
        pr_window = tk.Toplevel(self.root)
        pr_window.title("Create Pull Request")
        pr_window.geometry("600x400")
        pr_window.transient(self.root)
        pr_window.grab_set()
        
        # Make dialog modal
        pr_window.focus_set()
        
        # Create form
        frame = ttk.Frame(pr_window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # PR title
        ttk.Label(frame, text="Title:").pack(anchor=tk.W, pady=5)
        
        title_var = tk.StringVar(value=f"PR from {self.current_fork.full_name}:{fork_branch}")
        title_entry = ttk.Entry(frame, textvariable=title_var, width=70)
        title_entry.pack(anchor=tk.W, fill=tk.X, pady=5)
        
        # PR description
        ttk.Label(frame, text="Description:").pack(anchor=tk.W, pady=5)
        
        description_text = scrolledtext.ScrolledText(frame, width=70, height=10)
        description_text.pack(anchor=tk.W, fill=tk.BOTH, expand=True, pady=5)
        
        # Default description
        default_desc = "## Description\n\n" \
                     "Please include a summary of the changes.\n\n" \
                     "## Changes Made\n\n" \
                     "- \n\n" \
                     "## Related Issues\n\n" \
                     "- "
        description_text.insert(tk.INSERT, default_desc)
        
        # Branch info
        info_text = f"Creating PR from {self.current_fork.full_name}:{fork_branch} → " \
                  f"{self.current_parent.full_name}:{parent_branch}"
        ttk.Label(frame, text=info_text, wraplength=580).pack(anchor=tk.W, pady=10)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        create_btn = ttk.Button(
            btn_frame, 
            text="Create Pull Request", 
            command=lambda: self.submit_pull_request(
                title_var.get(), 
                description_text.get(1.0, tk.END), 
                fork_branch, 
                parent_branch, 
                pr_window
            )
        )
        create_btn.pack(side=tk.RIGHT, padx=5)
        
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=pr_window.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        # Center the window
        pr_window.update_idletasks()
        width = pr_window.winfo_width()
        height = pr_window.winfo_height()
        x = (pr_window.winfo_screenwidth() // 2) - (width // 2)
        y = (pr_window.winfo_screenheight() // 2) - (height // 2)
        pr_window.geometry(f'+{x}+{y}')
        
        # Initial focus
        title_entry.focus_set()





    def setup_commit_list_tab(self):
        # Create frames for organization
        top_frame = ttk.Frame(self.commit_list_tab)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Repository selection
        repo_frame = ttk.LabelFrame(top_frame, text="Repository Selection")
        repo_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side=tk.LEFT, padx=5)
        self.commit_list_repo_var = tk.StringVar()
        self.commit_list_repo_combo = ttk.Combobox(repo_frame, textvariable=self.commit_list_repo_var, width=50)
        self.commit_list_repo_combo.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        self.commit_list_repo_combo.bind('<<ComboboxSelected>>', self.update_commit_list_branches)
        
        # Branch selection
        branch_frame = ttk.LabelFrame(top_frame, text="Branch Selection")
        branch_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(branch_frame, text="Branch:").pack(side=tk.LEFT, padx=5)
        self.commit_list_branch_var = tk.StringVar()
        self.commit_list_branch_combo = ttk.Combobox(branch_frame, textvariable=self.commit_list_branch_var, width=30)
        self.commit_list_branch_combo.pack(side=tk.LEFT, padx=5)
        
        # Action buttons
        merge_pr_btn = ttk.Button(action_frame, text="Merge PR", command=self.show_merge_pr_dialog)
        merge_pr_btn.pack(side=tk.LEFT, padx=5)
        action_frame = ttk.Frame(top_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        fetch_btn = ttk.Button(action_frame, text="Fetch Commits", command=self.fetch_commit_list)
        fetch_btn.pack(side=tk.LEFT, padx=5)
        
        remove_btn = ttk.Button(action_frame, text="Remove Selected Commits", command=self.remove_selected_commits)
        remove_btn.pack(side=tk.LEFT, padx=5)
        
        # Number of commits to show
        limit_frame = ttk.Frame(action_frame)
        limit_frame.pack(side=tk.LEFT, padx=15)
        
        ttk.Label(limit_frame, text="Show last:").pack(side=tk.LEFT, padx=5)
        self.commit_limit_var = tk.StringVar(value="20")
        limit_entry = ttk.Combobox(limit_frame, textvariable=self.commit_limit_var, width=5, 
                                values=["10", "20", "50", "100"])
        limit_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(limit_frame, text="commits").pack(side=tk.LEFT)
        
        # Results frame with commits list
        results_frame = ttk.LabelFrame(self.commit_list_tab, text="Commit List")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a frame for the commits with a scrollbar
        commits_frame = ttk.Frame(results_frame)
        commits_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create canvas and scrollbar for scrolling
        self.commit_list_canvas = tk.Canvas(commits_frame)
        scrollbar = ttk.Scrollbar(commits_frame, orient=tk.VERTICAL, command=self.commit_list_canvas.yview)
        self.commit_list_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.commit_list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Frame inside canvas for commits
        self.commit_list_frame = ttk.Frame(self.commit_list_canvas)
        self.commit_list_canvas_window = self.commit_list_canvas.create_window((0, 0), window=self.commit_list_frame, anchor=tk.NW)
        
        # Configure scrolling
        self.commit_list_frame.bind("<Configure>", lambda e: self.commit_list_canvas.configure(scrollregion=self.commit_list_canvas.bbox("all")))
        self.commit_list_canvas.bind("<Configure>", self.on_commit_list_canvas_configure)
        
        # Bind mousewheel scrolling
        self.commit_list_canvas.bind_all("<MouseWheel>", lambda event: self.commit_list_canvas.yview_scroll(int(-1*(event.delta/120)), "units"))
        
        # Status message
        self.commit_list_status_var = tk.StringVar(value="Select a repository and branch to view commits")
        status_label = ttk.Label(results_frame, textvariable=self.commit_list_status_var)
        status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

    def on_commit_list_canvas_configure(self, event):
        # Update the width of the canvas window when the canvas size changes
        self.commit_list_canvas.itemconfig(self.commit_list_canvas_window, width=event.width)

    def update_commit_list_branches(self, event=None):
        """Update branch list when repository is selected in commit list tab"""
        repo_name = self.commit_list_repo_var.get()
        if not repo_name:
            return
            
        def fetch_branches():
            try:
                # Check if branches are cached
                if repo_name in self.cache['branches']:
                    branches = self.cache['branches'][repo_name]
                else:
                    repo = self.g.get_repo(repo_name)
                    branches = [branch.name for branch in repo.get_branches()]
                    self.cache['branches'][repo_name] = branches
                    self.save_cache()
                
                # Update UI in main thread
                self.root.after(0, lambda: self.update_commit_list_branch_dropdown(branches, repo_name))
                
            except Exception as e:
                raise Exception(f"Failed to fetch branches: {str(e)}")
        
        # Run in background thread
        self.run_in_thread(fetch_branches, message=f"Fetching branches for {repo_name}...", 
                        success_message=f"Branches updated for {repo_name}")

    def update_commit_list_branch_dropdown(self, branches, repo_name):
        """Update branch dropdown in commit list tab"""
        self.commit_list_branch_combo['values'] = branches
        
        # Try to set to develop branch if exists, otherwise default branch
        if 'develop' in branches:
            self.commit_list_branch_var.set('develop')
        else:
            try:
                default_branch = self.g.get_repo(repo_name).default_branch
                self.commit_list_branch_var.set(default_branch)
            except:
                if branches:
                    self.commit_list_branch_var.set(branches[0])

    def display_commit_list(self, commits, repo_name, branch_name):
        """Display commits with checkboxes in the commit list tab"""
        # Clear previous results
        for widget in self.commit_list_frame.winfo_children():
            widget.destroy()
            
        if not commits:
            self.commit_list_status_var.set(f"No commits found in {repo_name}/{branch_name}")
            return
            
        self.commit_list_status_var.set(f"Showing {len(commits)} commits from {repo_name}/{branch_name}")
        
        # Store checkboxes for later access
        self.commit_checkboxes = {}
        
        # Create header
        header_frame = ttk.Frame(self.commit_list_frame)
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Select all checkbox
        self.select_all_var = tk.BooleanVar(value=False)
        select_all_cb = ttk.Checkbutton(header_frame, variable=self.select_all_var, command=self.toggle_all_commits)
        select_all_cb.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(header_frame, text="Select All", font=("", 10, "bold")).pack(side=tk.LEFT)
        
        # Add separators for header
        separator = ttk.Separator(self.commit_list_frame, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, padx=5, pady=5)
        
        # Create a frame for each commit
        for i, commit in enumerate(commits):
            commit_frame = ttk.Frame(self.commit_list_frame)
            commit_frame.pack(fill=tk.X, padx=5, pady=5, anchor=tk.N)
            
            # Checkbox for selection
            var = tk.BooleanVar(value=False)
            checkbox = ttk.Checkbutton(commit_frame, variable=var)
            checkbox.pack(side=tk.LEFT, padx=5)
            
            # Store the checkbox variable
            self.commit_checkboxes[commit.sha] = var
            
            # Commit number and hash
            commit_num = ttk.Label(commit_frame, text=f"#{i+1}", font=("", 10, "bold"))
            commit_num.pack(side=tk.LEFT, padx=5)
            
            commit_hash = ttk.Label(commit_frame, text=commit.sha[:7])
            commit_hash.pack(side=tk.LEFT, padx=5)
            
            # Commit message
            msg_text = commit.commit.message.split('\n')[0]
            commit_msg = ttk.Label(commit_frame, text=msg_text, wraplength=800, anchor=tk.W)
            commit_msg.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            
            # Author and date
            author = commit.commit.author.name
            date = commit.commit.author.date.strftime("%Y-%m-%d %H:%M:%S")
            
            info_frame = ttk.Frame(commit_frame)
            info_frame.pack(side=tk.RIGHT)
            
            author_label = ttk.Label(info_frame, text=f"{author} on {date}")
            author_label.pack(side=tk.RIGHT, padx=5)
            
            # Add separator after each commit
            if i < len(commits) - 1:
                separator = ttk.Separator(self.commit_list_frame, orient=tk.HORIZONTAL)
                separator.pack(fill=tk.X, padx=5, pady=5)


    def setup_commit_list_tab(self):
        # Create frames for organization
        top_frame = ttk.Frame(self.commit_list_tab)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Repository selection
        repo_frame = ttk.LabelFrame(top_frame, text="Repository Selection")
        repo_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side=tk.LEFT, padx=5)
        self.commit_list_repo_var = tk.StringVar()
        self.commit_list_repo_combo = ttk.Combobox(repo_frame, textvariable=self.commit_list_repo_var, width=50)
        self.commit_list_repo_combo.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        self.commit_list_repo_combo.bind('<<ComboboxSelected>>', self.update_commit_list_branches)
        
        # Branch selection
        branch_frame = ttk.LabelFrame(top_frame, text="Branch Selection")
        branch_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(branch_frame, text="Branch:").pack(side=tk.LEFT, padx=5)
        self.commit_list_branch_var = tk.StringVar()
        self.commit_list_branch_combo = ttk.Combobox(branch_frame, textvariable=self.commit_list_branch_var, width=30)
        self.commit_list_branch_combo.pack(side=tk.LEFT, padx=5)
        
        # Action buttons
        action_frame = ttk.Frame(top_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        fetch_btn = ttk.Button(action_frame, text="Fetch Commits", command=self.fetch_commit_list)
        fetch_btn.pack(side=tk.LEFT, padx=5)
        
        remove_btn = ttk.Button(action_frame, text="Remove Selected Commits", command=self.remove_selected_commits)
        remove_btn.pack(side=tk.LEFT, padx=5)
        
        # Number of commits to show
        limit_frame = ttk.Frame(action_frame)
        limit_frame.pack(side=tk.LEFT, padx=15)
        
        ttk.Label(limit_frame, text="Show last:").pack(side=tk.LEFT, padx=5)
        self.commit_limit_var = tk.StringVar(value="20")
        limit_entry = ttk.Combobox(limit_frame, textvariable=self.commit_limit_var, width=5, 
                                values=["10", "20", "50", "100"])
        limit_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(limit_frame, text="commits").pack(side=tk.LEFT)
        
        # Results frame with commits list
        results_frame = ttk.LabelFrame(self.commit_list_tab, text="Commit List")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a frame for the commits with a scrollbar
        commits_frame = ttk.Frame(results_frame)
        commits_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create canvas and scrollbar for scrolling
        self.commit_list_canvas = tk.Canvas(commits_frame)
        scrollbar = ttk.Scrollbar(commits_frame, orient=tk.VERTICAL, command=self.commit_list_canvas.yview)
        self.commit_list_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.commit_list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Frame inside canvas for commits
        self.commit_list_frame = ttk.Frame(self.commit_list_canvas)
        self.commit_list_canvas_window = self.commit_list_canvas.create_window((0, 0), window=self.commit_list_frame, anchor=tk.NW)
        
        # Configure scrolling
        self.commit_list_frame.bind("<Configure>", lambda e: self.commit_list_canvas.configure(scrollregion=self.commit_list_canvas.bbox("all")))
        self.commit_list_canvas.bind("<Configure>", self.on_commit_list_canvas_configure)
        
        # Bind mousewheel scrolling
        self.commit_list_canvas.bind_all("<MouseWheel>", lambda event: self.commit_list_canvas.yview_scroll(int(-1*(event.delta/120)), "units"))
        
        # Status message
        self.commit_list_status_var = tk.StringVar(value="Select a repository and branch to view commits")
        status_label = ttk.Label(results_frame, textvariable=self.commit_list_status_var)
        status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

    def on_commit_list_canvas_configure(self, event):
        # Update the width of the canvas window when the canvas size changes
        self.commit_list_canvas.itemconfig(self.commit_list_canvas_window, width=event.width)

    def update_commit_list_branches(self, event=None):
        """Update branch list when repository is selected in commit list tab"""
        repo_name = self.commit_list_repo_var.get()
        if not repo_name:
            return
            
        def fetch_branches():
            try:
                # Check if branches are cached
                if repo_name in self.cache['branches']:
                    branches = self.cache['branches'][repo_name]
                else:
                    repo = self.g.get_repo(repo_name)
                    branches = [branch.name for branch in repo.get_branches()]
                    self.cache['branches'][repo_name] = branches
                    self.save_cache()
                
                # Update UI in main thread
                self.root.after(0, lambda: self.update_commit_list_branch_dropdown(branches, repo_name))
                
            except Exception as e:
                raise Exception(f"Failed to fetch branches: {str(e)}")
        
        # Run in background thread
        self.run_in_thread(fetch_branches, message=f"Fetching branches for {repo_name}...", 
                        success_message=f"Branches updated for {repo_name}")

    def update_commit_list_branch_dropdown(self, branches, repo_name):
        """Update branch dropdown in commit list tab"""
        self.commit_list_branch_combo['values'] = branches
        
        # Try to set to develop branch if exists, otherwise default branch
        if 'develop' in branches:
            self.commit_list_branch_var.set('develop')
        else:
            try:
                default_branch = self.g.get_repo(repo_name).default_branch
                self.commit_list_branch_var.set(default_branch)
            except:
                if branches:
                    self.commit_list_branch_var.set(branches[0])

    def fetch_commit_list(self):
        """Fetch commit list from the selected branch"""
        repo_name = self.commit_list_repo_var.get()
        branch_name = self.commit_list_branch_var.get()
        
        if not repo_name or not branch_name:
            messagebox.showerror("Error", "Please select a repository and branch")
            return
            
        try:
            limit = int(self.commit_limit_var.get())
        except ValueError:
            limit = 20  # Default value
        
        def fetch_commits():
            try:
                repo = self.g.get_repo(repo_name)
                branch = repo.get_branch(branch_name)
                
                # Get commits from the branch
                commits = []
                for commit in repo.get_commits(sha=branch.commit.sha):
                    commits.append(commit)
                    if len(commits) >= limit:
                        break
                
                # Store commits for later use
                self.commit_list_commits = commits
                
                # Update UI in main thread
                self.root.after(0, lambda: self.display_commit_list(commits, repo_name, branch_name))
                
            except Exception as e:
                raise Exception(f"Failed to fetch commits: {str(e)}")
        
        # Run in background thread
        self.run_in_thread(fetch_commits, 
                        message=f"Fetching commits from {branch_name}...", 
                        success_message=f"Fetched commits from {branch_name}")

    def display_commit_list(self, commits, repo_name, branch_name):
        """Display commits with checkboxes in the commit list tab"""
        # Clear previous results
        for widget in self.commit_list_frame.winfo_children():
            widget.destroy()
            
        if not commits:
            self.commit_list_status_var.set(f"No commits found in {repo_name}/{branch_name}")
            return
            
        self.commit_list_status_var.set(f"Showing {len(commits)} commits from {repo_name}/{branch_name}")
        
        # Store checkboxes for later access
        self.commit_checkboxes = {}
        
        # Create header
        header_frame = ttk.Frame(self.commit_list_frame)
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Select all checkbox
        self.select_all_var = tk.BooleanVar(value=False)
        select_all_cb = ttk.Checkbutton(header_frame, variable=self.select_all_var, command=self.toggle_all_commits)
        select_all_cb.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(header_frame, text="Select All", font=("", 10, "bold")).pack(side=tk.LEFT)
        
        # Add separators for header
        separator = ttk.Separator(self.commit_list_frame, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, padx=5, pady=5)
        
        # Create a frame for each commit
        for i, commit in enumerate(commits):
            commit_frame = ttk.Frame(self.commit_list_frame)
            commit_frame.pack(fill=tk.X, padx=5, pady=5, anchor=tk.N)
            
            # Checkbox for selection
            var = tk.BooleanVar(value=False)
            checkbox = ttk.Checkbutton(commit_frame, variable=var)
            checkbox.pack(side=tk.LEFT, padx=5)
            
            # Store the checkbox variable
            self.commit_checkboxes[commit.sha] = var
            
            # Commit number and hash
            commit_num = ttk.Label(commit_frame, text=f"#{i+1}", font=("", 10, "bold"))
            commit_num.pack(side=tk.LEFT, padx=5)
            
            commit_hash = ttk.Label(commit_frame, text=commit.sha[:7])
            commit_hash.pack(side=tk.LEFT, padx=5)
            
            # Commit message
            msg_text = commit.commit.message.split('\n')[0]
            commit_msg = ttk.Label(commit_frame, text=msg_text, wraplength=800, anchor=tk.W)
            commit_msg.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            
            # Author and date
            author = commit.commit.author.name
            date = commit.commit.author.date.strftime("%Y-%m-%d %H:%M:%S")
            
            info_frame = ttk.Frame(commit_frame)
            info_frame.pack(side=tk.RIGHT)
            
            author_label = ttk.Label(info_frame, text=f"{author} on {date}")
            author_label.pack(side=tk.RIGHT, padx=5)
            
            # Add separator after each commit
            if i < len(commits) - 1:
                separator = ttk.Separator(self.commit_list_frame, orient=tk.HORIZONTAL)
                separator.pack(fill=tk.X, padx=5, pady=5)

    def toggle_all_commits(self):
        """Select or deselect all commits"""
        select_all = self.select_all_var.get()
        
        for var in self.commit_checkboxes.values():
            var.set(select_all)

    def remove_selected_commits(self):
    """Remove selected commits from the branch with improved error handling and fallback methods"""
    repo_name = self.commit_list_repo_var.get()
    branch_name = self.commit_list_branch_var.get()
    
    if not repo_name or not branch_name:
        messagebox.showerror("Error", "Please select a repository and branch")
        return
        
    # Get selected commits
    selected_commits = [sha for sha, var in self.commit_checkboxes.items() if var.get()]
    
    if not selected_commits:
        messagebox.showinfo("Information", "No commits selected for removal")
        return
    
    # Confirmation dialog
    response = messagebox.askyesno(
        "Confirm Commit Removal", 
        f"Are you sure you want to remove {len(selected_commits)} commits from {branch_name}?

"
        "This operation will rewrite the branch history and cannot be undone."
    )
    
    if not response:
        return
    
    def perform_removal():
        logger.info(f"Starting commit removal process for {len(selected_commits)} commits from {branch_name}")
        
        # Track failed commits for retry
        failed_commits = []
        success = False
        error_message = ""
        
        try:
            # Method 1: GitHub API approach
            logger.info("Attempting commit removal using GitHub API")
            success = self._remove_commits_api_method(repo_name, branch_name, selected_commits)
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"GitHub API method failed: {error_message}")
            failed_commits = selected_commits
            
            try:
                # Method 2: Git filter-branch fallback
                logger.info("Attempting commit removal using git filter-branch fallback")
                success = self._remove_commits_filter_branch(repo_name, branch_name, failed_commits)
                failed_commits = []
                
            except Exception as e2:
                error_message = f"{error_message}
Filter-branch fallback failed: {str(e2)}"
                logger.error(f"Filter-branch fallback failed: {str(e2)}")
                
                try:
                    # Method 3: Cherry-pick fallback
                    logger.info("Attempting commit removal using cherry-pick fallback")
                    success = self._remove_commits_cherry_pick(repo_name, branch_name, failed_commits)
                    failed_commits = []
                    
                except Exception as e3:
                    error_message = f"{error_message}
Cherry-pick fallback failed: {str(e3)}"
                    logger.error(f"Cherry-pick fallback failed: {str(e3)}")
        
        # Update UI in main thread
        if success:
            self.root.after(0, lambda: self.after_commit_removal(len(selected_commits)))
            logger.info(f"Successfully removed {len(selected_commits)} commits")
        else:
            if failed_commits:
                error_msg = f"Failed to remove commits: {failed_commits}
Error details: {error_message}"
                logger.error(error_msg)
                self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to remove commits: {error_message}"))
    
    # Run in background thread
    self.run_in_thread(perform_removal, 
                    message=f"Removing {len(selected_commits)} commits...", 
                    success_message=f"Successfully removed {len(selected_commits)} commits")

def _remove_commits_api_method(self, repo_name, branch_name, commits_to_remove):
    """Remove commits using the GitHub API method"""
    logger.info(f"Using GitHub API method to remove {len(commits_to_remove)} commits")
    
    repo = self.g.get_repo(repo_name)
    
    # Get the current branch reference
    branch_ref = repo.get_git_ref(f"heads/{branch_name}")
    
    # Create a temporary branch for the operation
    temp_branch_name = f"temp-remove-commits-{int(datetime.datetime.now().timestamp())}"
    logger.info(f"Creating temporary branch: {temp_branch_name}")
    
    try:
        temp_ref = repo.create_git_ref(f"refs/heads/{temp_branch_name}", branch_ref.object.sha)
        
        # Get all commits in chronological order
        logger.info(f"Fetching all commits from {branch_name}")
        all_commits = list(repo.get_commits(sha=branch_name))
        
        # Filter out selected commits to remove
        commits_to_keep = [c for c in all_commits if c.sha not in commits_to_remove]
        
        if not commits_to_keep:
            raise Exception("Cannot remove all commits from the branch")
            
        # Find the oldest commit to keep
        base_commit = commits_to_keep[-1]
        logger.info(f"Base commit for new history: {base_commit.sha[:7]}")
        
        # Hard reset to the base commit
        logger.info(f"Resetting temporary branch to base commit")
        temp_ref.edit(base_commit.sha, force=True)
        
        # Cherry-pick each commit to keep in reverse order (oldest to newest)
        logger.info(f"Cherry-picking {len(commits_to_keep)-1} commits to temporary branch")
        
        for i, commit in enumerate(reversed(commits_to_keep[:-1])):  # Skip the base commit
            logger.info(f"Processing commit {i+1}/{len(commits_to_keep)-1}: {commit.sha[:7]}")
            
            # Get the commit data
            commit_data = repo.get_git_commit(commit.sha)
            tree = commit_data.tree
            parents = [base_commit.sha]
            
            # Create a new commit with the same data
            logger.info(f"Creating new commit based on {commit.sha[:7]}")
            new_commit = repo.create_git_commit(
                message=commit_data.message,
                tree=tree,
                parents=parents
            )
            
            # Update the temp branch reference
            temp_ref.edit(new_commit.sha, force=True)
            
            # Update the base commit for the next iteration
            base_commit = repo.get_git_commit(new_commit.sha)
            
            # Add a small delay to avoid rate limiting
            time.sleep(0.5)
        
        # Update the original branch to point to the new history
        logger.info(f"Updating original branch {branch_name} to new history")
        branch_ref.edit(temp_ref.object.sha, force=True)
        
        # Delete the temporary branch
        logger.info(f"Cleaning up temporary branch")
        temp_ref.delete()
        
        return True
        
    except Exception as e:
        logger.error(f"Error in API method: {str(e)}")
        # Try to clean up the temporary branch if it exists
        try:
            repo.get_git_ref(f"heads/{temp_branch_name}").delete()
        except:
            pass
        raise e

def _remove_commits_filter_branch(self, repo_name, branch_name, commits_to_remove):
    """Remove commits using git filter-branch as a fallback method"""
    logger.info(f"Using git filter-branch method to remove {len(commits_to_remove)} commits")
    
    # Create a temporary directory for the operation
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Clone the repository
            repo_url = f"https://{self.github_token}@github.com/{repo_name}.git"
            logger.info(f"Cloning repository to temporary directory")
            subprocess.run(["git", "clone", repo_url, temp_dir], check=True, capture_output=True)
            
            # Change to the repository directory
            os.chdir(temp_dir)
            
            # Checkout the branch
            logger.info(f"Checking out branch: {branch_name}")
            subprocess.run(["git", "checkout", branch_name], check=True, capture_output=True)
            
            # Create a list of commit SHAs to remove
            commit_list = " ".join(commits_to_remove)
            
            # Use git filter-branch to remove the commits
            logger.info(f"Running git filter-branch to remove commits")
            filter_cmd = f"git filter-branch --force --commit-filter 'if echo $GIT_COMMIT | grep -q -e {commit_list}; then skip_commit \"$@\"; else git commit-tree \"$@\"; fi' HEAD"
            subprocess.run(filter_cmd, shell=True, check=True, capture_output=True)
            
            # Push the changes
            logger.info(f"Pushing changes to remote")
            subprocess.run(["git", "push", "--force", "origin", branch_name], check=True, capture_output=True)
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Subprocess error in filter-branch method: {e.stderr.decode()}")
            raise Exception(f"Git operation failed: {e.stderr.decode()}")
        except Exception as e:
            logger.error(f"Error in filter-branch method: {str(e)}")
            raise e

def _remove_commits_cherry_pick(self, repo_name, branch_name, commits_to_remove):
    """Remove commits using cherry-pick as a fallback method"""
    logger.info(f"Using cherry-pick method to remove {len(commits_to_remove)} commits")
    
    # Create a temporary directory for the operation
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Clone the repository
            repo_url = f"https://{self.github_token}@github.com/{repo_name}.git"
            logger.info(f"Cloning repository to temporary directory")
            subprocess.run(["git", "clone", repo_url, temp_dir], check=True, capture_output=True)
            
            # Change to the repository directory
            os.chdir(temp_dir)
            
            # Get all commits in the branch
            logger.info(f"Getting commit history")
            result = subprocess.run(["git", "log", "--format=%H", branch_name], check=True, capture_output=True, text=True)
            all_commits = result.stdout.strip().split('
')
            
            # Filter out commits to remove
            commits_to_keep = [c for c in all_commits if c not in commits_to_remove]
            
            if not commits_to_keep:
                raise Exception("Cannot remove all commits from the branch")
            
            # Create a new branch from the earliest commit to keep
            earliest_commit = commits_to_keep[-1]
            temp_branch = f"temp-remove-{int(datetime.datetime.now().timestamp())}"
            logger.info(f"Creating temporary branch from {earliest_commit[:7]}")
            subprocess.run(["git", "checkout", "-b", temp_branch, earliest_commit], check=True, capture_output=True)
            
            # Cherry-pick each commit to keep
            logger.info(f"Cherry-picking {len(commits_to_keep)-1} commits")
            for i, commit in enumerate(reversed(commits_to_keep[:-1])):
                logger.info(f"Cherry-picking commit {i+1}/{len(commits_to_keep)-1}: {commit[:7]}")
                try:
                    subprocess.run(["git", "cherry-pick", commit], check=True, capture_output=True)
                except subprocess.CalledProcessError:
                    # Handle cherry-pick conflicts
                    logger.warning(f"Cherry-pick conflict for commit {commit[:7]}, skipping")
                    subprocess.run(["git", "cherry-pick", "--abort"], check=False)
            
            # Force update the original branch
            logger.info(f"Updating original branch {branch_name}")
            subprocess.run(["git", "branch", "-f", branch_name, temp_branch], check=True, capture_output=True)
            
            # Push the changes
            logger.info(f"Pushing changes to remote")
            subprocess.run(["git", "push", "--force", "origin", branch_name], check=True, capture_output=True)
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Subprocess error in cherry-pick method: {e.stderr.decode() if e.stderr else str(e)}")
            raise Exception(f"Git operation failed: {e.stderr.decode() if e.stderr else str(e)}")
        except Exception as e:
            logger.error(f"Error in cherry-pick method: {str(e)}")
            raise e

def after_commit_removal(self, num_removed):
    """Update after commit removal"""
    # Refresh the commit list
    self.fetch_commit_list()
    
    # Show success message
    messagebox.showinfo("Success", f"Successfully removed {num_removed} commits")



    def submit_pull_request(self, title, body, head, base, window):
        """Submit the pull request to GitHub"""
        if not title:
            messagebox.showerror("Error", "Please enter a title for the pull request")
            return
            
        def create_pr():
            try:
                # Format head branch in the required format (username:branch)
                head_branch = f"{self.current_fork.owner.login}:{head}"
                
                # Create the pull request
                pull_request = self.current_parent.create_pull(
                    title=title,
                    body=body,
                    head=head_branch,
                    base=base
                )
                
                # Close the window and open the PR in browser
                self.root.after(0, lambda: window.destroy())
                self.root.after(0, lambda: webbrowser.open_new(pull_request.html_url))
                
                return pull_request
                
            except Exception as e:
                raise Exception(f"Failed to create pull request: {str(e)}")
        
        # Run in background thread
        self.run_in_thread(create_pr, 
                          message="Creating pull request...", 
                          success_message="Pull request created successfully")

    def run(self):
        """Run the application"""
        # Set app icon (if available)
        try:
            # Add app icon here if needed
            pass
        except:
            pass
            
        # Start the main loop
        self.root.mainloop()

# Main entry point
if __name__ == "__main__":
    app = GitHubCompare()
    app.run()

    # Enhanced threading and merging methods
    def run_in_thread(self, func, args=None, kwargs=None, 
                     message="Working...", success_message=None,
                     on_success=None, on_error=None, task_id=None):
        """
        Run a function in a background thread with enhanced error handling and cancellation support.
        
        Args:
            func: The function to run
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            message: Message to display in the status bar
            success_message: Message to display on success
            on_success: Callback to execute on success
            on_error: Callback to execute on error
            task_id: Unique identifier for the task
        
        Returns:
            The submitted task
        """
        # Update status and show progress bar
        self.status_var.set(message)
        self.progress.pack(side=tk.BOTTOM, fill=tk.X, before=self.status_bar)
        self.progress.start()
        
        # Define success callback
        def handle_success(result):
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.progress.pack_forget())
            
            if success_message:
                self.root.after(0, lambda: self.status_var.set(success_message))
            else:
                self.root.after(0, lambda: self.status_var.set("Ready"))
                
            if on_success:
                self.root.after(0, lambda: on_success(result))
        
        # Define error callback
        def handle_error(error):
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.progress.pack_forget())
            self.root.after(0, lambda: self.status_var.set(f"Error: {str(error)}"))
            
            error_message = f"An error occurred: {str(error)}"
            self.root.after(0, lambda: messagebox.showerror("Error", error_message))
            
            if on_error:
                self.root.after(0, lambda: on_error(error))
        
        # Submit the task to the thread pool
        return self.thread_pool.submit(
            func=func,
            args=args,
            kwargs=kwargs,
            on_success=handle_success,
            on_error=handle_error,
            task_id=task_id
        )

    def cancel_task(self, task_id):
        """Cancel a running task by its ID"""
        if self.thread_pool.cancel_task(task_id):
            self.status_var.set("Task cancelled")
            self.progress.stop()
            self.progress.pack_forget()
            return True
        return False

    def cancel_all_tasks(self):
        """Cancel all running tasks"""
        count = self.thread_pool.cancel_all_tasks()
        if count > 0:
            self.status_var.set(f"Cancelled {count} tasks")
            self.progress.stop()
            self.progress.pack_forget()
        return count

    def init_github_client(self):
        """Initialize the GitHub client with the token"""
        try:
            self.g = Github(self.github_token)
            self.merge_operations = MergeOperations(self.g)
            self.status_var.set("Connected to GitHub")
            
            # Load cached data or fetch new data
            if self.cache["last_updated"] is None or (datetime.datetime.now() - self.cache["last_updated"]).total_seconds() > 3600:
                self.refresh_data()
            else:
                self.load_cached_data()
                
        except Exception as e:
            self.status_var.set(f"Error connecting to GitHub: {str(e)}")
            messagebox.showerror("GitHub Error", f"Failed to connect to GitHub: {str(e)}")

    def submit_pull_request(self, title, body, head, base, window, draft=False, reviewers=None):
        """
        Submit the pull request to GitHub with enhanced options.
        
        Args:
            title: Title of the pull request
            body: Body/description of the pull request
            head: Head branch
            base: Base branch
            window: The PR creation window
            draft: Whether to create a draft PR
            reviewers: List of GitHub usernames to request reviews from
        """
        if not title:
            messagebox.showerror("Error", "Please enter a title for the pull request")
            return
            
        # Get the repository name
        repo_name = self.current_fork.full_name
        
        # Format head branch if needed
        if self.current_fork.owner.login != self.current_parent.owner.login:
            head_branch = f"{self.current_fork.owner.login}:{head}"
        else:
            head_branch = head
        
        # Define the task function
        def create_pr_task():
            try:
                # Check for merge conflicts first
                has_conflicts, conflicting_files = self.merge_operations.check_for_merge_conflicts(
                    self.current_parent.full_name, base, head_branch
                )
                
                if has_conflicts:
                    # If there are conflicts, try to resolve them
                    files_str = ", ".join(conflicting_files[:5])
                    if len(conflicting_files) > 5:
                        files_str += f" and {len(conflicting_files) - 5} more"
                        
                    if messagebox.askyesno(
                        "Merge Conflicts", 
                        f"There are merge conflicts between {base} and {head} in files: {files_str}. "
                        f"Would you like to attempt to resolve them automatically?"
                    ):
                        # Try to resolve conflicts
                        resolved = self.merge_operations.resolve_simple_conflicts(
                            self.current_parent.full_name, 
                            # We don't have a PR number yet, so we'll need to create a temporary PR
                            # This is a placeholder for now
                            0
                        )
                        
                        if not resolved:
                            raise Exception(
                                f"Could not automatically resolve all merge conflicts. "
                                f"Please resolve them manually before creating the PR."
                            )
                
                # Create the pull request
                pr = self.merge_operations.create_pull_request(
                    self.current_parent.full_name,
                    title=title,
                    body=body,
                    head=head_branch,
                    base=base,
                    draft=draft,
                    reviewers=reviewers
                )
                
                # Close the window and open the PR in browser
                self.root.after(0, lambda: window.destroy())
                self.root.after(0, lambda: webbrowser.open_new(pr.html_url))
                
                return pr
                
            except Exception as e:
                raise Exception(f"Failed to create pull request: {str(e)}")
        
        # Run in background thread
        self.run_in_thread(
            create_pr_task, 
            message="Creating pull request...", 
            success_message="Pull request created successfully",
            task_id=f"create_pr_{head}_{base}"
        )

    def merge_pull_request(self, repo_name, pr_number, strategy=MergeStrategy.MERGE, 
                          commit_title=None, commit_message=None):
        """
        Merge a pull request with the specified strategy.
        
        Args:
            repo_name: Full name of the repository (owner/repo)
            pr_number: Pull request number
            strategy: Merge strategy (merge, squash, rebase)
            commit_title: Title for the merge commit
            commit_message: Message for the merge commit
        """
        def merge_task():
            return self.merge_operations.merge_pull_request(
                repo_name, pr_number, strategy, commit_title, commit_message
            )
        
        strategy_name = "merged"
        if strategy == MergeStrategy.SQUASH:
            strategy_name = "squash merged"
        elif strategy == MergeStrategy.REBASE:
            strategy_name = "rebased and merged"
        
        self.run_in_thread(
            merge_task,
            message=f"Merging pull request #{pr_number}...",
            success_message=f"Pull request #{pr_number} {strategy_name} successfully",
            task_id=f"merge_pr_{pr_number}"
        )

    def show_pr_dialog(self, head_branch, base_branch):
        """
        Show an enhanced dialog for creating a pull request.
        
        Args:
            head_branch: Head branch (source)
            base_branch: Base branch (target)
        """
        # Create a new window
        pr_window = tk.Toplevel(self.root)
        pr_window.title("Create Pull Request")
        pr_window.geometry("600x500")
        pr_window.transient(self.root)
        pr_window.grab_set()
        
        # Create a frame for the form
        form_frame = ttk.Frame(pr_window, padding=10)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title field
        ttk.Label(form_frame, text="Title:").grid(row=0, column=0, sticky=tk.W, pady=5)
        title_var = tk.StringVar()
        title_entry = ttk.Entry(form_frame, textvariable=title_var, width=50)
        title_entry.grid(row=0, column=1, sticky=tk.EW, pady=5)
        
        # Body field
        ttk.Label(form_frame, text="Description:").grid(row=1, column=0, sticky=tk.NW, pady=5)
        body_text = scrolledtext.ScrolledText(form_frame, width=50, height=10)
        body_text.grid(row=1, column=1, sticky=tk.NSEW, pady=5)
        
        # Branch information
        branch_frame = ttk.LabelFrame(form_frame, text="Branch Information", padding=5)
        branch_frame.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        ttk.Label(branch_frame, text=f"Head Branch: {head_branch}").pack(anchor=tk.W)
        ttk.Label(branch_frame, text=f"Base Branch: {base_branch}").pack(anchor=tk.W)
        
        # Options frame
        options_frame = ttk.LabelFrame(form_frame, text="Options", padding=5)
        options_frame.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        # Draft option
        draft_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Create as draft", variable=draft_var).pack(anchor=tk.W)
        
        # Reviewers
        ttk.Label(options_frame, text="Reviewers (comma-separated):").pack(anchor=tk.W, pady=(10, 0))
        reviewers_var = tk.StringVar()
        ttk.Entry(options_frame, textvariable=reviewers_var, width=50).pack(anchor=tk.W, fill=tk.X)
        
        # Buttons
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        ttk.Button(
            button_frame, 
            text="Cancel", 
            command=pr_window.destroy
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="Create Pull Request", 
            command=lambda: self.submit_pull_request(
                title_var.get(),
                body_text.get("1.0", tk.END),
                head_branch,
                base_branch,
                pr_window,
                draft=draft_var.get(),
                reviewers=reviewers_var.get().split(",") if reviewers_var.get() else None
            )
        ).pack(side=tk.LEFT, padx=5)
        
        # Configure grid weights
        form_frame.columnconfigure(1, weight=1)
        form_frame.rowconfigure(1, weight=1)
        
        # Focus the title entry
        title_entry.focus_set()

    def cleanup(self):
        """Clean up resources when the application closes"""
        try:
            # Shutdown the thread pool
            if hasattr(self, 'thread_pool'):
                self.thread_pool.shutdown()
                
            # Save config and cache
            self.save_config()
            self.save_cache()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def on_close(self):
        """Handle window close event"""
        self.cleanup()
        self.root.destroy()

    def run(self):
        """Run the application"""
        # Set app icon (if available)
        try:
            # Add app icon here if needed
            pass
        except:
            pass
            
        # Register cleanup handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Start the main loop
        self.root.mainloop()

    def show_merge_pr_dialog(self):
        """Show a dialog to merge a pull request"""
        # Create a new window
        merge_window = tk.Toplevel(self.root)
        merge_window.title("Merge Pull Request")
        merge_window.geometry("500x400")
        merge_window.transient(self.root)
        merge_window.grab_set()
        
        # Create a frame for the form
        form_frame = ttk.Frame(merge_window, padding=10)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Repository field
        ttk.Label(form_frame, text="Repository:").grid(row=0, column=0, sticky=tk.W, pady=5)
        repo_var = tk.StringVar()
        repo_combo = ttk.Combobox(form_frame, textvariable=repo_var, width=40)
        repo_combo.grid(row=0, column=1, sticky=tk.EW, pady=5)
        
        # Populate repository dropdown
        repos = [repo.full_name for repo in self.g.get_user().get_repos()]
        repo_combo['values'] = repos
        if repos:
            repo_combo.current(0)
        
        # PR number field
        ttk.Label(form_frame, text="PR Number:").grid(row=1, column=0, sticky=tk.W, pady=5)
        pr_number_var = tk.StringVar()
        pr_number_entry = ttk.Entry(form_frame, textvariable=pr_number_var, width=10)
        pr_number_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Merge strategy
        ttk.Label(form_frame, text="Merge Strategy:").grid(row=2, column=0, sticky=tk.W, pady=5)
        strategy_var = tk.StringVar(value="merge")
        strategy_frame = ttk.Frame(form_frame)
        strategy_frame.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        ttk.Radiobutton(strategy_frame, text="Merge", variable=strategy_var, value="merge").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(strategy_frame, text="Squash", variable=strategy_var, value="squash").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(strategy_frame, text="Rebase", variable=strategy_var, value="rebase").pack(side=tk.LEFT, padx=5)
        
        # Commit title field
        ttk.Label(form_frame, text="Commit Title:").grid(row=3, column=0, sticky=tk.W, pady=5)
        title_var = tk.StringVar()
        title_entry = ttk.Entry(form_frame, textvariable=title_var, width=40)
        title_entry.grid(row=3, column=1, sticky=tk.EW, pady=5)
        
        # Commit message field
        ttk.Label(form_frame, text="Commit Message:").grid(row=4, column=0, sticky=tk.NW, pady=5)
        message_text = scrolledtext.ScrolledText(form_frame, width=40, height=10)
        message_text.grid(row=4, column=1, sticky=tk.NSEW, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        ttk.Button(
            button_frame, 
            text="Cancel", 
            command=merge_window.destroy
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="Merge PR", 
            command=lambda: self.merge_pull_request(
                repo_var.get(),
                int(pr_number_var.get()) if pr_number_var.get().isdigit() else 0,
                strategy_var.get(),
                title_var.get() if title_var.get() else None,
                message_text.get("1.0", tk.END) if message_text.get("1.0", tk.END).strip() else None
            ) and merge_window.destroy()
        ).pack(side=tk.LEFT, padx=5)
        
        # Configure grid weights
        form_frame.columnconfigure(1, weight=1)
        form_frame.rowconfigure(4, weight=1)
        
        # Focus the PR number entry
        pr_number_entry.focus_set()
