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
import queue
import concurrent.futures
import signal
import atexit
from github import Github, GithubException
from functools import partial


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

# ThreadPoolManager class for enhanced thread management
class ThreadPoolManager:
    """Manages a pool of worker threads for background tasks"""
    def __init__(self, max_workers=None):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.tasks = {}
        self.task_counter = 0
        self.task_lock = threading.Lock()
        self.running = True
        self.results_queue = queue.Queue()
        
        # Register cleanup on exit
        atexit.register(self.shutdown)
        
    def submit_task(self, func, *args, callback=None, error_callback=None, **kwargs):
        """Submit a task to the thread pool and return a task ID"""
        with self.task_lock:
            task_id = self.task_counter
            self.task_counter += 1
            
            # Wrap the function to handle callbacks
            def wrapped_func(*args, **kwargs):
                try:
                    result = func(*args, **kwargs)
                    if callback:
                        self.results_queue.put((callback, result, None))
                    return result
                except Exception as e:
                    logger.error(f"Task {task_id} failed: {str(e)}")
                    if error_callback:
                        self.results_queue.put((error_callback, None, e))
                    raise
            
            future = self.executor.submit(wrapped_func, *args, **kwargs)
            self.tasks[task_id] = future
            
            # Add callback to clean up completed tasks
            future.add_done_callback(lambda f, tid=task_id: self._task_done(tid))
            
            return task_id, future
    
    def _task_done(self, task_id):
        """Remove completed task from the tasks dictionary"""
        with self.task_lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
    
    def cancel_task(self, task_id):
        """Cancel a running task by ID"""
        with self.task_lock:
            if task_id in self.tasks:
                future = self.tasks[task_id]
                return future.cancel()
            return False
    
    def cancel_all_tasks(self):
        """Cancel all running tasks"""
        with self.task_lock:
            for task_id, future in list(self.tasks.items()):
                future.cancel()
    
    def process_callbacks(self):
        """Process any pending callbacks in the results queue"""
        try:
            while not self.results_queue.empty():
                callback, result, error = self.results_queue.get_nowait()
                if error:
                    callback(error)
                else:
                    callback(result)
        except queue.Empty:
            pass
    
    def shutdown(self):
        """Shutdown the thread pool and cancel all tasks"""
        if not self.running:
            return
            
        logger.info("Shutting down thread pool")
        self.running = False
        self.cancel_all_tasks()
        self.executor.shutdown(wait=False)
        
    def get_active_task_count(self):
        """Return the number of active tasks"""
        with self.task_lock:
            return len(self.tasks)

# MergeManager class for enhanced merge functionality
class MergeManager:
    """Enhanced merge functionality for GitHub repositories"""
    
    def __init__(self, github_token, root_widget=None):
        self.github_token = github_token
        self.g = Github(github_token) if github_token else None
        self.root_widget = root_widget
        self.lock = threading.Lock()
        
    def merge_commit(self, repo_name, branch_name, commit_sha, 
                     merge_strategy="merge", 
                     message=None, 
                     batch_size=10):
        """
        Merge a specific commit with enhanced error handling and performance
        
        Args:
            repo_name: Full repository name (owner/repo)
            branch_name: Target branch name
            commit_sha: SHA of the commit to merge
            merge_strategy: Strategy to use (merge, squash, rebase)
            message: Custom commit message
            batch_size: Number of commits to process in a batch
        
        Returns:
            dict: Result of the merge operation
        """
        logger.info(f"Merging commit {commit_sha[:7]} into {repo_name}:{branch_name} using {merge_strategy} strategy")
        
        # Default commit message if not provided
        if not message:
            message = f"Merge commit {commit_sha[:7]} using {merge_strategy} strategy"
        
        # Try GitHub API method first
        try:
            return self._merge_api_method(repo_name, branch_name, commit_sha, 
                                         merge_strategy, message)
        except Exception as e:
            logger.error(f"GitHub API merge failed: {str(e)}")
            
            # Try Git CLI method as fallback
            try:
                return self._merge_git_method(repo_name, branch_name, commit_sha, 
                                             merge_strategy, message, batch_size)
            except Exception as e2:
                logger.error(f"Git CLI merge failed: {str(e2)}")
                
                # Try cherry-pick method as final fallback
                try:
                    return self._merge_cherry_pick_method(repo_name, branch_name, commit_sha, message)
                except Exception as e3:
                    logger.error(f"Cherry-pick merge failed: {str(e3)}")
                    raise Exception(f"All merge methods failed: {str(e)}, {str(e2)}, {str(e3)}")
    
    def _merge_api_method(self, repo_name, branch_name, commit_sha, merge_strategy, message):
        """Merge using GitHub API"""
        repo = self.g.get_repo(repo_name)
        
        # Create a temporary branch for the operation
        temp_branch = f"temp-merge-{commit_sha[:7]}-{int(datetime.datetime.now().timestamp())}"
        logger.info(f"Creating temporary branch: {temp_branch}")
        
        # Get the current branch reference
        branch_ref = repo.get_git_ref(f"heads/{branch_name}")
        
        # Create the temporary branch
        repo.create_git_ref(f"refs/heads/{temp_branch}", branch_ref.object.sha)
        
        try:
            # Get the commit to merge
            commit = repo.get_commit(commit_sha)
            
            # Merge the commit into the temporary branch
            if merge_strategy == "merge":
                merge_result = repo.merge(temp_branch, commit_sha, message)
            elif merge_strategy == "squash":
                # For squash, we need to use a different approach
                base_commit = repo.get_git_commit(branch_ref.object.sha)
                tree = repo.get_git_tree(commit.commit.tree.sha)
                squash_commit = repo.create_git_commit(message, tree, [base_commit])
                temp_ref = repo.get_git_ref(f"heads/{temp_branch}")
                temp_ref.edit(squash_commit.sha, force=True)
                merge_result = {"sha": squash_commit.sha}
            elif merge_strategy == "rebase":
                # For rebase, we need to cherry-pick the commit
                cherry_pick = repo.merge(temp_branch, commit_sha, message)
                merge_result = {"sha": cherry_pick.sha}
            else:
                raise ValueError(f"Unsupported merge strategy: {merge_strategy}")
            
            # Merge the temporary branch back to the target branch
            merge_to_target = repo.merge(branch_name, temp_branch, 
                                        f"Merge {merge_strategy} of {commit_sha[:7]}")
            
            # Clean up the temporary branch
            repo.get_git_ref(f"heads/{temp_branch}").delete()
            
            return {
                "success": True,
                "sha": merge_to_target.sha,
                "message": f"Successfully merged commit {commit_sha[:7]} using {merge_strategy} strategy",
                "method": "api"
            }
        except Exception as e:
            # Clean up the temporary branch in case of error
            try:
                repo.get_git_ref(f"heads/{temp_branch}").delete()
            except:
                pass
            raise e
    
    def _merge_git_method(self, repo_name, branch_name, commit_sha, merge_strategy, message, batch_size):
        """Merge using Git CLI commands"""
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
                
                # Create a temporary branch
                temp_branch = f"temp-merge-{commit_sha[:7]}-{int(datetime.datetime.now().timestamp())}"
                logger.info(f"Creating temporary branch: {temp_branch}")
                subprocess.run(["git", "checkout", "-b", temp_branch], check=True, capture_output=True)
                
                # Perform the merge based on strategy
                if merge_strategy == "merge":
                    logger.info(f"Merging commit {commit_sha[:7]} with merge strategy")
                    subprocess.run(["git", "merge", commit_sha, "--no-ff", "-m", message], 
                                  check=True, capture_output=True)
                elif merge_strategy == "squash":
                    logger.info(f"Merging commit {commit_sha[:7]} with squash strategy")
                    subprocess.run(["git", "merge", "--squash", commit_sha], 
                                  check=True, capture_output=True)
                    subprocess.run(["git", "commit", "-m", message], 
                                  check=True, capture_output=True)
                elif merge_strategy == "rebase":
                    logger.info(f"Merging commit {commit_sha[:7]} with rebase strategy")
                    subprocess.run(["git", "cherry-pick", commit_sha], 
                                  check=True, capture_output=True)
                else:
                    raise ValueError(f"Unsupported merge strategy: {merge_strategy}")
                
                # Get the new commit SHA
                result = subprocess.run(["git", "rev-parse", "HEAD"], 
                                      check=True, capture_output=True, text=True)
                new_sha = result.stdout.strip()
                
                # Checkout the original branch
                subprocess.run(["git", "checkout", branch_name], check=True, capture_output=True)
                
                # Merge the temporary branch
                subprocess.run(["git", "merge", temp_branch, "--no-ff", "-m", 
                              f"Merge {merge_strategy} of {commit_sha[:7]}"], 
                              check=True, capture_output=True)
                
                # Push the changes
                logger.info(f"Pushing changes to remote")
                subprocess.run(["git", "push", "origin", branch_name], check=True, capture_output=True)
                
                return {
                    "success": True,
                    "sha": new_sha,
                    "message": f"Successfully merged commit {commit_sha[:7]} using {merge_strategy} strategy",
                    "method": "git"
                }
            except Exception as e:
                raise e
    
    def _merge_cherry_pick_method(self, repo_name, branch_name, commit_sha, message):
        """Merge using cherry-pick as a fallback method"""
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
                
                # Cherry-pick the commit
                logger.info(f"Cherry-picking commit {commit_sha[:7]}")
                subprocess.run(["git", "cherry-pick", commit_sha], check=True, capture_output=True)
                
                # Get the new commit SHA
                result = subprocess.run(["git", "rev-parse", "HEAD"], 
                                      check=True, capture_output=True, text=True)
                new_sha = result.stdout.strip()
                
                # Push the changes
                logger.info(f"Pushing changes to remote")
                subprocess.run(["git", "push", "origin", branch_name], check=True, capture_output=True)
                
                return {
                    "success": True,
                    "sha": new_sha,
                    "message": f"Successfully cherry-picked commit {commit_sha[:7]}",
                    "method": "cherry-pick"
                }
            except Exception as e:
                raise e
    
    def check_for_conflicts(self, repo_name, branch_name, commit_sha):
        """Check if merging a commit would cause conflicts"""
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
                
                # Try to merge the commit without committing
                try:
                    subprocess.run(["git", "merge", "--no-commit", "--no-ff", commit_sha], 
                                  check=True, capture_output=True)
                    
                    # If we get here, there are no conflicts
                    # Abort the merge to clean up
                    subprocess.run(["git", "merge", "--abort"], check=True, capture_output=True)
                    
                    return {
                        "has_conflicts": False,
                        "message": "No conflicts detected"
                    }
                except subprocess.CalledProcessError as e:
                    # Check if the error is due to conflicts
                    if "CONFLICT" in e.stderr.decode():
                        # Get the list of conflicting files
                        result = subprocess.run(["git", "diff", "--name-only", "--diff-filter=U"], 
                                              check=False, capture_output=True, text=True)
                        conflicting_files = result.stdout.strip().split('\n')
                        
                        # Abort the merge to clean up
                        subprocess.run(["git", "merge", "--abort"], check=False, capture_output=True)
                        
                        return {
                            "has_conflicts": True,
                            "conflicting_files": conflicting_files,
                            "message": f"Conflicts detected in {len(conflicting_files)} files"
                        }
                    else:
                        raise e
            except Exception as e:
                raise e
    
    def auto_resolve_conflicts(self, repo_name, branch_name, commit_sha, strategy="ours"):
        """
        Attempt to automatically resolve merge conflicts
        
        Args:
            repo_name: Full repository name (owner/repo)
            branch_name: Target branch name
            commit_sha: SHA of the commit to merge
            strategy: Conflict resolution strategy ('ours', 'theirs', or 'union')
        
        Returns:
            dict: Result of the conflict resolution
        """
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
                
                # Try to merge the commit
                try:
                    subprocess.run(["git", "merge", "--no-commit", "--no-ff", commit_sha], 
                                  check=True, capture_output=True)
                    
                    # If we get here, there are no conflicts, so just commit
                    subprocess.run(["git", "commit", "-m", f"Merge {commit_sha[:7]} without conflicts"], 
                                  check=True, capture_output=True)
                except subprocess.CalledProcessError:
                    # Get the list of conflicting files
                    result = subprocess.run(["git", "diff", "--name-only", "--diff-filter=U"], 
                                          check=False, capture_output=True, text=True)
                    conflicting_files = result.stdout.strip().split('\n')
                    
                    # Resolve conflicts based on strategy
                    if strategy == "ours":
                        for file in conflicting_files:
                            if file:  # Skip empty lines
                                subprocess.run(["git", "checkout", "--ours", file], 
                                              check=True, capture_output=True)
                                subprocess.run(["git", "add", file], check=True, capture_output=True)
                    elif strategy == "theirs":
                        for file in conflicting_files:
                            if file:  # Skip empty lines
                                subprocess.run(["git", "checkout", "--theirs", file], 
                                              check=True, capture_output=True)
                                subprocess.run(["git", "add", file], check=True, capture_output=True)
                    elif strategy == "union":
                        # This is more complex and would require parsing the conflict markers
                        # For simplicity, we'll use the merge-file command with the union option
                        for file in conflicting_files:
                            if file:  # Skip empty lines
                                # Get the base, ours, and theirs versions
                                base = f"{file}.base"
                                ours = f"{file}.ours"
                                theirs = f"{file}.theirs"
                                
                                # Extract the versions
                                subprocess.run([f"git show :1:{file} > {base}"], 
                                              shell=True, check=False)
                                subprocess.run([f"git show :2:{file} > {ours}"], 
                                              shell=True, check=False)
                                subprocess.run([f"git show :3:{file} > {theirs}"], 
                                              shell=True, check=False)
                                
                                # Merge with union strategy
                                subprocess.run([f"git merge-file -p --union {ours} {base} {theirs} > {file}"], 
                                              shell=True, check=False)
                                
                                # Add the resolved file
                                subprocess.run(["git", "add", file], check=True, capture_output=True)
                    else:
                        raise ValueError(f"Unsupported conflict resolution strategy: {strategy}")
                    
                    # Commit the resolved conflicts
                    subprocess.run(["git", "commit", "-m", 
                                  f"Merge {commit_sha[:7]} with auto-resolved conflicts using {strategy} strategy"], 
                                  check=True, capture_output=True)
                
                # Push the changes
                logger.info(f"Pushing changes to remote")
                subprocess.run(["git", "push", "origin", branch_name], check=True, capture_output=True)
                
                # Get the new commit SHA
                result = subprocess.run(["git", "rev-parse", "HEAD"], 
                                      check=True, capture_output=True, text=True)
                new_sha = result.stdout.strip()
                
                return {
                    "success": True,
                    "sha": new_sha,
                    "message": f"Successfully merged {commit_sha[:7]} with auto-resolved conflicts",
                    "strategy": strategy
                }
            except Exception as e:
                raise e

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
        
        # Initialize thread pool and merge manager
        self.thread_pool = ThreadPoolManager(max_workers=5)
        
        # Load token from config file
        self.config_file = os.path.join(os.path.expanduser("~"), ".github_compare_config")
        self.load_config()
        
        # Initialize merge manager after loading token
        self.merge_manager = MergeManager(self.github_token, self.root)
        
        # Set up a timer to process callbacks from the thread pool
        self._setup_callback_timer()
        
        # Register cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
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

    def _setup_callback_timer(self):
        """Set up a timer to process callbacks from the thread pool"""
        def process_callbacks():
            self.thread_pool.process_callbacks()
            self.root.after(100, process_callbacks)
        
        self.root.after(100, process_callbacks)
    
    def _on_close(self):
        """Clean up resources when the window is closed"""
        logger.info("Shutting down...")
        self.thread_pool.shutdown()
        self.root.destroy()

    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    config = json.load(f)
                    self.github_token = config.get("github_token", "")
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            messagebox.showerror("Error", f"Failed to load configuration: {str(e)}")

    def save_config(self):
        """Save configuration to file"""
        try:
            config = {
                "github_token": self.github_token
            }
            with open(self.config_file, "w") as f:
                json.dump(config, f)
        except Exception as e:
            logger.error(f"Error saving config: {str(e)}")
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")

    def init_github_client(self):
        """Initialize the GitHub client with the token"""
        try:
            self.g = Github(self.github_token)
            self.status_var.set("Connected to GitHub")
            self.refresh_data()
        except Exception as e:
            logger.error(f"Error initializing GitHub client: {str(e)}")
            messagebox.showerror("Error", f"Failed to connect to GitHub: {str(e)}")
            self.status_var.set("Failed to connect to GitHub")

    def run_in_thread(self, func, *args, message="Working...", success_message="Complete", **kwargs):
        """Run a function in a background thread with progress indication"""
        self.start_progress(message)
        
        def on_success(result):
            self.stop_progress(success_message)
            return result
        
        def on_error(error):
            self.handle_error(error)
            return None
        
        task_id, future = self.thread_pool.submit_task(
            func, *args, 
            callback=on_success,
            error_callback=on_error,
            **kwargs
        )
        
        return task_id, future

    def start_progress(self, message):
        """Show progress indication"""
        self.status_var.set(message)
        self.progress.pack(side=tk.BOTTOM, fill=tk.X, before=self.status_bar)
        self.progress.start(10)
        self.root.update_idletasks()

    def stop_progress(self, message):
        """Hide progress indication"""
        self.status_var.set(message)
        self.progress.stop()
        self.progress.pack_forget()
        self.root.update_idletasks()

    def handle_error(self, error):
        """Handle errors from background threads"""
        error_message = str(error)
        logger.error(f"Error: {error_message}")
        self.stop_progress("Error occurred")
        messagebox.showerror("Error", error_message)

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

    def merge_commit(self, commit):
        """Merge a specific commit from parent repo into fork"""
        if not self.current_fork:
            messagebox.showerror("Error", "No fork selected")
            return
        
        # Confirm the merge
        if not messagebox.askyesno(
            "Confirm Merge",
            f"Are you sure you want to merge commit {commit.sha[:7]} into your fork?"
        ):
            return
        
        # Use our enhanced merge manager
        repo_name = self.current_fork.full_name
        branch_name = self.current_branch
        commit_sha = commit.sha
        
        def perform_merge():
            return self.merge_manager.merge_commit(
                repo_name, branch_name, commit_sha,
                merge_strategy="merge",
                message=f"Merge commit {commit_sha[:7]} from parent"
            )
        
        self.run_in_thread(
            perform_merge,
            message=f"Merging commit {commit.sha[:7]}...",
            success_message=f"Successfully merged commit {commit.sha[:7]}"
        )
        
        # Refresh the UI after merge
        self.root.after(1000, lambda: self.after_merge())

    def _remove_commits_api_method(self, repo_name, branch_name, commits_to_remove):
        """Remove commits using the GitHub API method with enhanced error handling and performance"""
        logger.info(f"Using enhanced GitHub API method to remove {len(commits_to_remove)} commits")
        
        repo = self.g.get_repo(repo_name)
        
        # Create a temporary branch for the operation
        temp_branch_name = f"temp-remove-commits-{int(datetime.datetime.now().timestamp())}"
        logger.info(f"Creating temporary branch: {temp_branch_name}")
        
        # Get the current branch reference
        branch_ref = repo.get_git_ref(f"heads/{branch_name}")
        
        try:
            # Create the temporary branch
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
            
            # Process commits in batches for better performance
            batch_size = 20
            total_commits = len(commits_to_keep)
            
            # Hard reset to the base commit
            temp_ref.edit(base_commit.sha, force=True)
            
            # Apply the commits to keep in batches
            for i in range(0, total_commits - 1, batch_size):
                batch = commits_to_keep[i:i+batch_size]
                logger.info(f"Processing batch {i//batch_size + 1} of {(total_commits + batch_size - 1)//batch_size}")
                
                for commit in reversed(batch):
                    if commit.sha == base_commit.sha:
                        continue
                    
                    # Cherry-pick each commit
                    try:
                        repo.merge(temp_branch_name, commit.sha, f"Cherry-pick {commit.sha[:7]}")
                    except Exception as e:
                        logger.warning(f"Failed to cherry-pick commit {commit.sha[:7]}: {str(e)}")
                        # Try to continue with the next commit
            
            # Update the original branch to point to the new history
            logger.info(f"Updating {branch_name} to new history")
            branch_ref.edit(temp_ref.object.sha, force=True)
            
            # Clean up the temporary branch
            logger.info(f"Cleaning up temporary branch")
            repo.get_git_ref(f"heads/{temp_branch_name}").delete()
            
            return True
        except Exception as e:
            # Clean up the temporary branch in case of error
            try:
                repo.get_git_ref(f"heads/{temp_branch_name}").delete()
            except:
                pass
            raise e

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
