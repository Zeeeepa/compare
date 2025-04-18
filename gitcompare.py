import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import webbrowser
import threading
import queue
import concurrent.futures
import signal
import atexit
import json
import datetime
import time
import logging
import tempfile
import subprocess
from github import Github, GithubException
from functools import partial


# Set up logging
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
