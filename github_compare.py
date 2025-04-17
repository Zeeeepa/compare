import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from github import Github, GithubException
import webbrowser
import git
import tempfile
import shutil

class GitHubComparisonTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Branch Comparison Tool")
        self.root.geometry("800x600")
        
        # Initialize GitHub API
        self.gh = None
        self.load_github_token()
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Create tabs
        self.local_tab = ttk.Frame(self.notebook)
        self.origin_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.local_tab, text='Local Branch Compare')
        self.notebook.add(self.origin_tab, text='Origin Compare')
        
        # Setup UI elements
        self.setup_settings_button()
        self.setup_local_tab()
        self.setup_origin_tab()
        
        # Initialize variables
        self.repo = None
        self.origin_repo = None
        self.temp_dir = None

    def setup_settings_button(self):
        settings_frame = ttk.Frame(self.root)
        settings_frame.pack(fill='x', padx=10, pady=5)
        ttk.Button(settings_frame, text="⚙️ Settings", command=self.show_settings).pack(side='right')

    def setup_local_tab(self):
        # Repository selection
        repo_frame = ttk.LabelFrame(self.local_tab, text="Repository Selection")
        repo_frame.pack(fill='x', padx=10, pady=5)
        
        self.repo_var = tk.StringVar()
        self.repo_dropdown = ttk.Combobox(repo_frame, textvariable=self.repo_var)
        self.repo_dropdown.pack(fill='x', padx=5, pady=5)
        self.repo_dropdown.bind('<<ComboboxSelected>>', self.on_repo_selected)
        
        # Branch selection
        branch_frame = ttk.LabelFrame(self.local_tab, text="Branch Selection")
        branch_frame.pack(fill='x', padx=10, pady=5)
        
        self.base_branch_var = tk.StringVar()
        self.compare_branch_var = tk.StringVar()
        
        ttk.Label(branch_frame, text="Base Branch:").pack(side='left', padx=5)
        self.base_branch_dropdown = ttk.Combobox(branch_frame, textvariable=self.base_branch_var)
        self.base_branch_dropdown.pack(side='left', padx=5)
        
        ttk.Label(branch_frame, text="Compare Branch:").pack(side='left', padx=5)
        self.compare_branch_dropdown = ttk.Combobox(branch_frame, textvariable=self.compare_branch_var)
        self.compare_branch_dropdown.pack(side='left', padx=5)
        
        # Compare button
        ttk.Button(self.local_tab, text="Compare Branches", 
                  command=lambda: self.compare_branches(False)).pack(pady=10)
        
        # Results
        self.local_results = tk.Text(self.local_tab, height=20, wrap=tk.WORD)
        self.local_results.pack(fill='both', expand=True, padx=10, pady=5)

    def setup_origin_tab(self):
        # Repository selection
        repo_frame = ttk.LabelFrame(self.origin_tab, text="Repository Selection")
        repo_frame.pack(fill='x', padx=10, pady=5)
        
        self.origin_repo_var = tk.StringVar()
        self.origin_repo_dropdown = ttk.Combobox(repo_frame, textvariable=self.origin_repo_var)
        self.origin_repo_dropdown.pack(fill='x', padx=5, pady=5)
        self.origin_repo_dropdown.bind('<<ComboboxSelected>>', self.on_origin_repo_selected)
        
        # Branch selection
        branch_frame = ttk.LabelFrame(self.origin_tab, text="Branch Selection")
        branch_frame.pack(fill='x', padx=10, pady=5)
        
        self.origin_base_branch_var = tk.StringVar()
        self.origin_compare_branch_var = tk.StringVar()
        
        ttk.Label(branch_frame, text="Base Branch:").pack(side='left', padx=5)
        self.origin_base_branch_dropdown = ttk.Combobox(branch_frame, textvariable=self.origin_base_branch_var)
        self.origin_base_branch_dropdown.pack(side='left', padx=5)
        
        ttk.Label(branch_frame, text="Compare Branch:").pack(side='left', padx=5)
        self.origin_compare_branch_dropdown = ttk.Combobox(branch_frame, textvariable=self.origin_compare_branch_var)
        self.origin_compare_branch_dropdown.pack(side='left', padx=5)
        
        # Compare button
        ttk.Button(self.origin_tab, text="Compare with Origin", 
                  command=lambda: self.compare_branches(True)).pack(pady=10)
        
        # Results
        self.origin_results = tk.Text(self.origin_tab, height=20, wrap=tk.WORD)
        self.origin_results.pack(fill='both', expand=True, padx=10, pady=5)

    def load_github_token(self):
        try:
            with open('github_token.json', 'r') as f:
                data = json.load(f)
                token = data.get('token')
                if token:
                    self.gh = Github(token)
                    self.update_repo_list()
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_github_token(self, token):
        with open('github_token.json', 'w') as f:
            json.dump({'token': token}, f)

    def show_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x150")
        
        ttk.Label(settings_window, text="GitHub Token:").pack(padx=10, pady=5)
        token_entry = ttk.Entry(settings_window, width=50)
        token_entry.pack(padx=10, pady=5)
        
        try:
            with open('github_token.json', 'r') as f:
                data = json.load(f)
                token_entry.insert(0, data.get('token', ''))
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        
        def save_settings():
            token = token_entry.get().strip()
            if token:
                try:
                    # Test token
                    gh = Github(token)
                    gh.get_user().login
                    self.save_github_token(token)
                    self.gh = gh
                    self.update_repo_list()
                    messagebox.showinfo("Success", "GitHub token saved successfully!")
                    settings_window.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"Invalid GitHub token: {str(e)}")
            else:
                messagebox.showerror("Error", "Please enter a GitHub token")
        
        ttk.Button(settings_window, text="Save", command=save_settings).pack(pady=10)

    def update_repo_list(self):
        if not self.gh:
            return
        
        try:
            repos = [repo.full_name for repo in self.gh.get_user().get_repos()]
            self.repo_dropdown['values'] = repos
            self.origin_repo_dropdown['values'] = repos
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch repositories: {str(e)}")

    def on_repo_selected(self, event=None):
        if not self.gh:
            messagebox.showerror("Error", "Please set your GitHub token in settings first")
            return
        
        try:
            self.repo = self.gh.get_repo(self.repo_var.get())
            branches = [branch.name for branch in self.repo.get_branches()]
            self.base_branch_dropdown['values'] = branches
            self.compare_branch_dropdown['values'] = branches
            
            # Set default branch
            default_branch = self.repo.default_branch
            self.base_branch_var.set(default_branch)
            self.compare_branch_var.set(default_branch)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch branches: {str(e)}")

    def on_origin_repo_selected(self, event=None):
        if not self.gh:
            messagebox.showerror("Error", "Please set your GitHub token in settings first")
            return
        
        try:
            self.repo = self.gh.get_repo(self.origin_repo_var.get())
            
            # Get parent/origin repository
            if self.repo.parent:
                self.origin_repo = self.repo.parent
                branches = [branch.name for branch in self.origin_repo.get_branches()]
                self.origin_base_branch_dropdown['values'] = branches
                self.origin_compare_branch_dropdown['values'] = branches
                
                # Set default branch
                default_branch = self.origin_repo.default_branch
                self.origin_base_branch_var.set(default_branch)
                self.origin_compare_branch_var.set(default_branch)
            else:
                messagebox.showwarning("Warning", "Selected repository is not a fork")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch origin repository: {str(e)}")

    def compare_branches(self, compare_with_origin=False):
        if not self.gh:
            messagebox.showerror("Error", "Please set your GitHub token in settings first")
            return
        
        try:
            if compare_with_origin:
                if not self.origin_repo:
                    messagebox.showerror("Error", "Please select a forked repository first")
                    return
                
                base_repo = self.origin_repo
                base_branch = self.origin_base_branch_var.get()
                compare_repo = self.repo
                compare_branch = self.origin_compare_branch_var.get()
                results_widget = self.origin_results
            else:
                base_repo = self.repo
                base_branch = self.base_branch_var.get()
                compare_repo = self.repo
                compare_branch = self.compare_branch_var.get()
                results_widget = self.local_results
            
            # Clear previous results
            results_widget.delete(1.0, tk.END)
            
            # Get comparison
            comparison = base_repo.compare(base_branch, f"{compare_repo.owner.login}:{compare_branch}")
            
            # Display stats
            stats = f"Comparing {base_repo.full_name}:{base_branch} with {compare_repo.full_name}:{compare_branch}\n\n"
            stats += f"Commits ahead: {comparison.ahead_by}\n"
            stats += f"Commits behind: {comparison.behind_by}\n"
            stats += f"Total commits: {len(comparison.commits)}\n"
            stats += f"Files changed: {len(comparison.files)}\n\n"
            
            # Display commits
            stats += "Commits:\n"
            for i, commit in enumerate(comparison.commits, 1):
                stats += f"\n{i}. {commit.commit.message.splitlines()[0]}\n"
                stats += f"   SHA: {commit.sha}\n"
                stats += f"   Author: {commit.commit.author.name}\n"
                
                # Add View Diff and Merge buttons
                commit_frame = ttk.Frame(results_widget)
                ttk.Button(commit_frame, text="View Diff", 
                          command=lambda c=commit: webbrowser.open(c.html_url)).pack(side='left', padx=5)
                ttk.Button(commit_frame, text="Merge", 
                          command=lambda c=commit: self.merge_commit(c, base_branch)).pack(side='left', padx=5)
                
                results_widget.window_create(tk.END, window=commit_frame)
                results_widget.insert(tk.END, "\n")
            
            results_widget.insert(1.0, stats)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to compare branches: {str(e)}")

    def merge_commit(self, commit, target_branch):
        try:
            # Create temporary directory for git operations
            self.temp_dir = tempfile.mkdtemp()
            
            # Clone repository
            repo_url = f"https://{self.gh._Github__requester._Requester__auth.token}@github.com/{self.repo.full_name}.git"
            git_repo = git.Repo.clone_from(repo_url, self.temp_dir)
            
            # Checkout target branch
            git_repo.git.checkout(target_branch)
            
            # Cherry-pick the commit
            git_repo.git.cherry_pick(commit.sha)
            
            # Push changes
            git_repo.git.push('origin', target_branch)
            
            messagebox.showinfo("Success", f"Successfully merged commit {commit.sha[:7]}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to merge commit: {str(e)}")
        finally:
            # Cleanup
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = GitHubComparisonTool()
    app.run()
