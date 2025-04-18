# Import the new modules
from thread_pool import ThreadPool, Task
from merge_operations import MergeOperations, MergeStrategy

# Add these to the GitHubCompare class __init__ method
self.thread_pool = ThreadPool(num_workers=5)
self.merge_operations = None  # Will be initialized when GitHub client is initialized

# Update the init_github_client method to initialize merge_operations
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

# Replace the run_in_thread method with this enhanced version
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

# Add a method to cancel a running task
def cancel_task(self, task_id):
    """Cancel a running task by its ID"""
    if self.thread_pool.cancel_task(task_id):
        self.status_var.set("Task cancelled")
        self.progress.stop()
        self.progress.pack_forget()
        return True
    return False

# Add a method to cancel all running tasks
def cancel_all_tasks(self):
    """Cancel all running tasks"""
    count = self.thread_pool.cancel_all_tasks()
    if count > 0:
        self.status_var.set(f"Cancelled {count} tasks")
        self.progress.stop()
        self.progress.pack_forget()
    return count

# Replace the submit_pull_request method with this enhanced version
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

# Add a new method for merging pull requests
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

# Add a new method to show the PR creation dialog with enhanced options
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

# Add a method to cleanup resources when the application closes
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

# Update the run method to handle cleanup
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

# Add a method to handle window close
def on_close(self):
    """Handle window close event"""
    self.cleanup()
    self.root.destroy()
