import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
from github import Github, GithubException
import webbrowser
import git
import tempfile
import shutil

class GitHubCompare:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Branch Comparison Tool")
        
        # Initialize GitHub token from settings or environment
        self.token = self.load_github_token()
        
        # Initialize GitHub API
        self.init_github_api()
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create tabs
        self.local_tab = ttk.Frame(self.notebook)
        self.origin_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.local_tab, text='Local Compare')
        self.notebook.add(self.origin_tab, text='Origin Compare')
        self.notebook.add(self.settings_tab, text='Settings')
        
        # Initialize UI components
        self.init_local_tab()
        self.init_origin_tab()
        self.init_settings_tab()
        
        # Initialize workspace
        self.workspace = None

    def load_github_token(self):
        try:
            with open('github_settings.json', 'r') as f:
                settings = json.load(f)
                return settings.get('token', '')
        except:
            return os.getenv('GITHUB_TOKEN', '')

    def save_github_token(self, token):
        with open('github_settings.json', 'w') as f:
            json.dump({'token': token}, f)
        self.token = token
        self.init_github_api()
        messagebox.showinfo("Success", "GitHub token saved successfully!")

    def init_github_api(self):
        try:
            self.github = Github(self.token) if self.token else None
            self.user = self.github.get_user() if self.github else None
        except Exception as e:
            self.github = None
            self.user = None
            messagebox.showerror("Error", f"Failed to initialize GitHub API: {str(e)}")

    def init_local_tab(self):
        # Repository selection
        ttk.Label(self.local_tab, text="Repository:").pack(pady=5)
        self.repo_var = tk.StringVar()
        self.repo_dropdown = ttk.Combobox(self.local_tab, textvariable=self.repo_var)
        self.repo_dropdown.pack(pady=5)
        self.repo_dropdown.bind('<<ComboboxSelected>>', self.update_branches)
        
        # Branch selection frame
        branch_frame = ttk.Frame(self.local_tab)
        branch_frame.pack(fill='x', pady=5)
        
        # Base branch
        base_frame = ttk.Frame(branch_frame)
        base_frame.pack(side='left', padx=5)
        ttk.Label(base_frame, text="Base Branch:").pack()
        self.base_branch_var = tk.StringVar()
        self.base_branch_dropdown = ttk.Combobox(base_frame, textvariable=self.base_branch_var)
        self.base_branch_dropdown.pack()
        
        # Compare branch
        compare_frame = ttk.Frame(branch_frame)
        compare_frame.pack(side='right', padx=5)
        ttk.Label(compare_frame, text="Compare Branch:").pack()
        self.compare_branch_var = tk.StringVar()
        self.compare_branch_dropdown = ttk.Combobox(compare_frame, textvariable=self.compare_branch_var)
        self.compare_branch_dropdown.pack()
        
        # Compare button
        ttk.Button(self.local_tab, text="Compare Branches", command=self.compare_branches).pack(pady=10)
        
        # Results
        self.results_text = tk.Text(self.local_tab, height=20, width=60)
        self.results_text.pack(pady=5, padx=5, fill='both', expand=True)
        
        self.update_repos()

    def init_origin_tab(self):
        # Repository selection
        ttk.Label(self.origin_tab, text="Your Repository:").pack(pady=5)
        self.origin_repo_var = tk.StringVar()
        self.origin_repo_dropdown = ttk.Combobox(self.origin_tab, textvariable=self.origin_repo_var)
        self.origin_repo_dropdown.pack(pady=5)
        self.origin_repo_dropdown.bind('<<ComboboxSelected>>', self.update_origin_branches)
        
        # Branch selection
        ttk.Label(self.origin_tab, text="Your Branch:").pack(pady=5)
        self.origin_branch_var = tk.StringVar()
        self.origin_branch_dropdown = ttk.Combobox(self.origin_tab, textvariable=self.origin_branch_var)
        self.origin_branch_dropdown.pack(pady=5)
        
        # Compare button
        ttk.Button(self.origin_tab, text="Compare with Origin", command=self.compare_with_origin).pack(pady=10)
        
        # Results
        self.origin_results_text = tk.Text(self.origin_tab, height=20, width=60)
        self.origin_results_text.pack(pady=5, padx=5, fill='both', expand=True)
        
        self.update_repos(origin=True)

    def init_settings_tab(self):
        # GitHub Token
        ttk.Label(self.settings_tab, text="GitHub Token:").pack(pady=5)
        self.token_entry = ttk.Entry(self.settings_tab, width=50)
        self.token_entry.pack(pady=5)
        self.token_entry.insert(0, self.token)
        
        # Save button
        ttk.Button(self.settings_tab, text="Save Token", command=lambda: self.save_github_token(self.token_entry.get())).pack(pady=10)
        
        # Help text
        help_text = """
        To get a GitHub token:
        1. Go to GitHub.com
        2. Click your profile picture → Settings
        3. Developer settings → Personal access tokens → Tokens (classic)
        4. Generate new token
        5. Select 'repo' scope
        6. Copy and paste the token here
        """
        ttk.Label(self.settings_tab, text=help_text, justify='left').pack(pady=20)

    def update_repos(self, origin=False):
        if not self.github:
            messagebox.showerror("Error", "Please set your GitHub token in Settings first!")
            return
        
        try:
            repos = [repo.full_name for repo in self.user.get_repos()]
            if origin:
                self.origin_repo_dropdown['values'] = repos
            else:
                self.repo_dropdown['values'] = repos
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch repositories: {str(e)}")

    def update_branches(self, event=None):
        if not self.github:
            return
        
        try:
            repo = self.github.get_repo(self.repo_var.get())
            branches = [branch.name for branch in repo.get_branches()]
            self.base_branch_dropdown['values'] = branches
            self.compare_branch_dropdown['values'] = branches
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch branches: {str(e)}")

    def update_origin_branches(self, event=None):
        if not self.github:
            return
        
        try:
            repo = self.github.get_repo(self.origin_repo_var.get())
            branches = [branch.name for branch in repo.get_branches()]
            self.origin_branch_dropdown['values'] = branches
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch branches: {str(e)}")

    def compare_branches(self):
        if not self.github:
            messagebox.showerror("Error", "Please set your GitHub token in Settings first!")
            return
        
        try:
            repo = self.github.get_repo(self.repo_var.get())
            base = self.base_branch_var.get()
            compare = self.compare_branch_var.get()
            
            if not base or not compare:
                messagebox.showerror("Error", "Please select both branches!")
                return
            
            comparison = repo.compare(base, compare)
            self.results_text.delete(1.0, tk.END)
            
            for commit in comparison.commits:
                # Create a frame for each commit
                commit_frame = ttk.Frame(self.results_text)
                
                # Add commit message and stats
                message = commit.commit.message.split('\n')[0]  # Get first line of commit message
                stats = commit.stats
                info_text = f"{message}\n{stats.total} changed files with {stats.additions} additions and {stats.deletions} deletions"
                
                # Create buttons
                view_button = ttk.Button(
                    commit_frame, 
                    text="View Diff",
                    command=lambda url=commit.html_url: webbrowser.open(url)
                )
                merge_button = ttk.Button(
                    commit_frame,
                    text="Merge",
                    command=lambda c=commit: self.merge_commit(c)
                )
                
                # Pack elements
                ttk.Label(commit_frame, text=info_text, wraplength=400).pack(side='left', padx=5)
                view_button.pack(side='left', padx=2)
                merge_button.pack(side='left', padx=2)
                
                # Insert the frame into the text widget
                self.results_text.window_create(tk.END, window=commit_frame)
                self.results_text.insert(tk.END, '\n\n')
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to compare branches: {str(e)}")

    def compare_with_origin(self):
        if not self.github:
            messagebox.showerror("Error", "Please set your GitHub token in Settings first!")
            return
        
        try:
            repo = self.github.get_repo(self.origin_repo_var.get())
            branch = self.origin_branch_var.get() or repo.default_branch
            
            # Get the parent/origin repository
            parent = repo.parent
            if not parent:
                messagebox.showerror("Error", "This repository is not a fork!")
                return
            
            # Compare with parent's default branch
            comparison = repo.compare(f"{parent.owner.login}:{parent.default_branch}", branch)
            
            self.origin_results_text.delete(1.0, tk.END)
            self.origin_results_text.insert(tk.END, f"Comparing with {parent.full_name}:{parent.default_branch}\n")
            self.origin_results_text.insert(tk.END, f"Commits behind: {comparison.behind_by}\n")
            self.origin_results_text.insert(tk.END, f"Commits ahead: {comparison.ahead_by}\n\n")
            
            if comparison.behind_by > 0:
                # Get commits that we're behind
                commits = parent.get_commits(since=repo.get_branch(branch).commit.commit.author.date)
                
                for commit in commits:
                    # Create a frame for each commit
                    commit_frame = ttk.Frame(self.origin_results_text)
                    
                    # Add commit message and stats
                    message = commit.commit.message.split('\n')[0]  # Get first line of commit message
                    stats = commit.stats
                    info_text = f"{message}\n{stats.total} changed files with {stats.additions} additions and {stats.deletions} deletions"
                    
                    # Create buttons
                    view_button = ttk.Button(
                        commit_frame,
                        text="View Diff",
                        command=lambda url=commit.html_url: webbrowser.open(url)
                    )
                    merge_button = ttk.Button(
                        commit_frame,
                        text="Merge",
                        command=lambda c=commit: self.merge_commit(c, is_origin=True)
                    )
                    
                    # Pack elements
                    ttk.Label(commit_frame, text=info_text, wraplength=400).pack(side='left', padx=5)
                    view_button.pack(side='left', padx=2)
                    merge_button.pack(side='left', padx=2)
                    
                    # Insert the frame into the text widget
                    self.origin_results_text.window_create(tk.END, window=commit_frame)
                    self.origin_results_text.insert(tk.END, '\n\n')
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to compare with origin: {str(e)}")

    def merge_commit(self, commit, is_origin=False):
        try:
            # Get the repository and current branch
            repo_name = self.origin_repo_var.get() if is_origin else self.repo_var.get()
            repo = self.github.get_repo(repo_name)
            current_branch = self.origin_branch_var.get() if is_origin else self.compare_branch_var.get()
            
            # Create temporary workspace if needed
            if not self.workspace:
                self.workspace = tempfile.mkdtemp()
                git.Repo.clone_from(repo.clone_url, self.workspace)
            
            # Get the local repo
            local_repo = git.Repo(self.workspace)
            
            # Fetch and checkout the current branch
            local_repo.git.fetch('origin', current_branch)
            local_repo.git.checkout(current_branch)
            
            # Cherry-pick the commit
            local_repo.git.cherry_pick(commit.sha)
            
            # Push the changes
            local_repo.git.push('origin', current_branch)
            
            messagebox.showinfo("Success", "Commit merged successfully!")
            
            # Refresh the comparison
            if is_origin:
                self.compare_with_origin()
            else:
                self.compare_branches()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to merge commit: {str(e)}")
            if self.workspace:
                local_repo = git.Repo(self.workspace)
                local_repo.git.cherry_pick('--abort')

    def run(self):
        self.root.mainloop()
        # Cleanup workspace
        if self.workspace:
            shutil.rmtree(self.workspace)

if __name__ == "__main__":
    app = GitHubCompare()
    app.run()
