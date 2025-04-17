import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import webbrowser
import threading
import json
import datetime
from github import Github, GithubException
from functools import partial

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
    def remove_selected_commits(self):
        """Remove selected commits from the branch"""
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
            f"Are you sure you want to remove {len(selected_commits)} selected commits from {branch_name}?\n\n"
            "This operation will rewrite the branch history and cannot be undone."
        )
        
        if not response:
            return
        
        def perform_removal():
            temp_branch_name = None
            try:
                repo = self.g.get_repo(repo_name)
                
                # Get the current branch reference
                try:
                    branch_ref = repo.get_git_ref(f"heads/{branch_name}")
                except GithubException as e:
                    if e.status == 404:
                        raise Exception(f"Branch '{branch_name}' not found")
                    raise Exception(f"Failed to access branch: {str(e)}")
                
                # Create a temporary branch for the operation
                temp_branch_name = f"temp-remove-commits-{int(datetime.datetime.now().timestamp())}"
                try:
                    temp_ref = repo.create_git_ref(f"refs/heads/{temp_branch_name}", branch_ref.object.sha)
                except GithubException as e:
                    raise Exception(f"Failed to create temporary branch: {str(e)}")
                
                # Get all commits in chronological order
                try:
                    all_commits = list(repo.get_commits(sha=branch_name))
                except GithubException as e:
                    raise Exception(f"Failed to fetch commits: {str(e)}")
                
                # Filter out selected commits to remove
                commit_to_keep = [c for c in all_commits if c.sha not in selected_commits]
                
                if not commit_to_keep:
                    raise Exception("Cannot remove all commits from the branch")
                    
                # Find the oldest commit to keep
                base_commit = commit_to_keep[-1]
                
                # Cherry-pick commits to the temporary branch
                # First, hard reset to the base commit
                try:
                    temp_ref.edit(base_commit.sha, force=True)
                except GithubException as e:
                    raise Exception(f"Failed to reset temporary branch: {str(e)}")
                
                # Cherry-pick each commit to keep in reverse order (oldest to newest)
                for i, commit in enumerate(reversed(commit_to_keep[:-1])):  # Skip the base commit
                    try:
                        # Get the commit data
                        commit_data = repo.get_git_commit(commit.sha)
                        tree = commit_data.tree
                        parents = [base_commit.sha]
                        
                        # Handle merge commits
                        if len(commit_data.parents) > 1:
                            # For merge commits, we need to ensure we have the correct parent
                            # Find the parent that's in our keep list
                            valid_parents = [p for p in commit_data.parents if p.sha in [c.sha for c in commit_to_keep]]
                            if valid_parents:
                                parents = [valid_parents[0].sha]
                            else:
                                # Skip this commit if we can't find a valid parent
                                continue
                        
                        # Create a new commit with the same data
                        new_commit = repo.create_git_commit(
                            message=commit_data.message,
                            tree=tree,
                            parents=parents
                        )
                        
                        # Update the temp branch reference
                        temp_ref.edit(new_commit.sha, force=True)
                        
                        # Update the base commit for the next iteration
                        base_commit = repo.get_git_commit(new_commit.sha)
                        
                        # Log progress
                        self.status_var.set(f"Cherry-picking commit {i+1}/{len(commit_to_keep)-1}...")
                        
                    except GithubException as e:
                        raise Exception(f"Failed to cherry-pick commit {commit.sha}: {str(e)}")
                
                # Update the original branch to point to the new history
                try:
                    branch_ref.edit(temp_ref.object.sha, force=True)
                except GithubException as e:
                    raise Exception(f"Failed to update branch: {str(e)}")
                
                # Delete the temporary branch
                try:
                    temp_ref.delete()
                    temp_branch_name = None  # Mark as deleted
                except GithubException as e:
                    # Non-fatal error, just log it
                    print(f"Warning: Failed to delete temporary branch: {str(e)}")
                
                # Update UI in main thread
                self.root.after(0, lambda: self.after_commit_removal(len(selected_commits)))
                
            except Exception as e:
                error_msg = str(e)
                # Clean up temporary branch if it exists
                if temp_branch_name:
                    try:
                        repo.get_git_ref(f"refs/heads/{temp_branch_name}").delete()
                    except:
                        pass  # Ignore cleanup errors
                raise Exception(f"Failed to remove commits: {error_msg}")
        
        # Run in background thread
        self.run_in_thread(perform_removal, 
                        message=f"Removing {len(selected_commits)} commits...", 
                        success_message=f"Successfully removed {len(selected_commits)} commits")
