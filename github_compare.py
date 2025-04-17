import os
import tkinter as tk
from tkinter import ttk, messagebox
import json
from github import Github, GithubException
import webbrowser
import tempfile
import git
import shutil

class GitHubCompare:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Branch Comparison Tool")
        self.root.geometry("800x600")
        
        # Initialize GitHub API
        self.gh = None
        self.load_token()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Create tabs
        self.local_tab = ttk.Frame(self.notebook)
        self.origin_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.local_tab, text='Local Compare')
        self.notebook.add(self.origin_tab, text='Origin Compare')
        
        # Setup UI elements
        self.setup_local_tab()
        self.setup_origin_tab()
        self.setup_settings_button()
        
        # Initialize variables
        self.repo = None
        self.origin_repo = None
        self.temp_dir = None
        self.local_repo = None

    def load_token(self):
        try:
            if os.path.exists('github_token.json'):
                with open('github_token.json', 'r') as f:
                    data = json.load(f)
                    token = data.get('token')
                    if token:
                        self.gh = Github(token)
                        return
        except Exception:
            pass
        self.show_settings()

    def save_token(self, token):
        try:
            self.gh = Github(token)
            # Test the token
            self.gh.get_user().login
            with open('github_token.json', 'w') as f:
                json.dump({'token': token}, f)
            messagebox.showinfo("Success", "GitHub token saved successfully!")
            self.settings_window.destroy()
            self.update_repo_lists()
        except Exception as e:
            messagebox.showerror("Error", f"Invalid token: {str(e)}")

    def setup_settings_button(self):
        settings_btn = ttk.Button(self.root, text="⚙️ Settings", command=self.show_settings)
        settings_btn.pack(side=tk.TOP, anchor=tk.NE, padx=10, pady=5)

    def show_settings(self):
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("Settings")
        self.settings_window.geometry("400x150")
        
        ttk.Label(self.settings_window, text="GitHub Token:").pack(pady=10)
        token_entry = ttk.Entry(self.settings_window, width=50)
        token_entry.pack(pady=5)
        
        save_btn = ttk.Button(self.settings_window, text="Save",
                            command=lambda: self.save_token(token_entry.get()))
        save_btn.pack(pady=10)

    def setup_local_tab(self):
        # Repository selection
        repo_frame = ttk.LabelFrame(self.local_tab, text="Repository Selection")
        repo_frame.pack(fill='x', padx=10, pady=5)
        
        self.local_repo_var = tk.StringVar()
        self.local_repo_dropdown = ttk.Combobox(repo_frame, textvariable=self.local_repo_var)
        self.local_repo_dropdown.pack(fill='x', padx=5, pady=5)
        self.local_repo_dropdown.bind('<<ComboboxSelected>>', self.update_local_branches)
        
        # Branch selection
        branch_frame = ttk.LabelFrame(self.local_tab, text="Branch Selection")
        branch_frame.pack(fill='x', padx=10, pady=5)
        
        self.base_branch_var = tk.StringVar()
        self.compare_branch_var = tk.StringVar()
        
        ttk.Label(branch_frame, text="Base Branch:").pack(side=tk.LEFT, padx=5)
        self.base_branch_dropdown = ttk.Combobox(branch_frame, textvariable=self.base_branch_var)
        self.base_branch_dropdown.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(branch_frame, text="Compare Branch:").pack(side=tk.LEFT, padx=5)
        self.compare_branch_dropdown = ttk.Combobox(branch_frame, textvariable=self.compare_branch_var)
        self.compare_branch_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Compare button
        ttk.Button(self.local_tab, text="Compare Branches",
                  command=lambda: self.compare_branches(False)).pack(pady=10)
        
        # Results
        self.local_results = tk.Text(self.local_tab, height=20, width=80)
        self.local_results.pack(padx=10, pady=5, fill='both', expand=True)

    def setup_origin_tab(self):
        # Repository selection
        repo_frame = ttk.LabelFrame(self.origin_tab, text="Repository Selection")
        repo_frame.pack(fill='x', padx=10, pady=5)
        
        self.origin_repo_var = tk.StringVar()
        self.origin_repo_dropdown = ttk.Combobox(repo_frame, textvariable=self.origin_repo_var)
        self.origin_repo_dropdown.pack(fill='x', padx=5, pady=5)
        self.origin_repo_dropdown.bind('<<ComboboxSelected>>', self.update_origin_branches)
        
        # Branch selection
        branch_frame = ttk.LabelFrame(self.origin_tab, text="Branch Selection")
        branch_frame.pack(fill='x', padx=10, pady=5)
        
        self.origin_base_branch_var = tk.StringVar()
        self.origin_compare_branch_var = tk.StringVar()
        
        ttk.Label(branch_frame, text="Base Branch:").pack(side=tk.LEFT, padx=5)
        self.origin_base_branch_dropdown = ttk.Combobox(branch_frame, textvariable=self.origin_base_branch_var)
        self.origin_base_branch_dropdown.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(branch_frame, text="Compare Branch:").pack(side=tk.LEFT, padx=5)
        self.origin_compare_branch_dropdown = ttk.Combobox(branch_frame, textvariable=self.origin_compare_branch_var)
        self.origin_compare_branch_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Compare button
        ttk.Button(self.origin_tab, text="Compare with Origin",
                  command=lambda: self.compare_branches(True)).pack(pady=10)
        
        # Results
        self.origin_results = tk.Text(self.origin_tab, height=20, width=80)
        self.origin_results.pack(padx=10, pady=5, fill='both', expand=True)

    def update_repo_lists(self):
        if not self.gh:
            return
            
        try:
            # Get user's repositories
            user = self.gh.get_user()
            repos = [repo.full_name for repo in user.get_repos()]
            
            # Update dropdowns
            self.local_repo_dropdown['values'] = repos
            self.origin_repo_dropdown['values'] = repos
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch repositories: {str(e)}")

    def update_local_branches(self, event=None):
        if not self.gh or not self.local_repo_var.get():
            return
            
        try:
            repo = self.gh.get_repo(self.local_repo_var.get())
            branches = [branch.name for branch in repo.get_branches()]
            
            self.base_branch_dropdown['values'] = branches
            self.compare_branch_dropdown['values'] = branches
            
            # Set defaults
            default_branch = repo.default_branch
            self.base_branch_var.set(default_branch)
            self.compare_branch_var.set(default_branch)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch branches: {str(e)}")

    def update_origin_branches(self, event=None):
        if not self.gh or not self.origin_repo_var.get():
            return
            
        try:
            repo = self.gh.get_repo(self.origin_repo_var.get())
            parent = repo.parent
            
            if parent:
                branches = [branch.name for branch in parent.get_branches()]
                
                self.origin_base_branch_dropdown['values'] = branches
                self.origin_compare_branch_dropdown['values'] = branches
                
                # Set defaults
                default_branch = parent.default_branch
                self.origin_base_branch_var.set(default_branch)
                self.origin_compare_branch_var.set(default_branch)
            else:
                messagebox.showwarning("Warning", "Selected repository is not a fork!")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch origin branches: {str(e)}")

    def compare_branches(self, compare_with_origin=False):
        if not self.gh:
            messagebox.showerror("Error", "Please set up GitHub token first!")
            return
            
        try:
            if compare_with_origin:
                repo_name = self.origin_repo_var.get()
                base_branch = self.origin_base_branch_var.get()
                compare_branch = self.origin_compare_branch_var.get()
                results_widget = self.origin_results
            else:
                repo_name = self.local_repo_var.get()
                base_branch = self.base_branch_var.get()
                compare_branch = self.compare_branch_var.get()
                results_widget = self.local_results
                
            if not repo_name or not base_branch or not compare_branch:
                messagebox.showerror("Error", "Please select repository and branches!")
                return
                
            repo = self.gh.get_repo(repo_name)
            
            if compare_with_origin:
                parent = repo.parent
                if not parent:
                    messagebox.showerror("Error", "Selected repository is not a fork!")
                    return
                comparison = repo.compare(f"{parent.owner.login}:{base_branch}", f"{repo.owner.login}:{compare_branch}")
            else:
                comparison = repo.compare(base_branch, compare_branch)
                
            # Clear previous results
            results_widget.delete(1.0, tk.END)
            
            # Show comparison stats
            stats = f"Comparing {base_branch} with {compare_branch}\n\n"
            stats += f"Total commits: {len(list(comparison.commits))}\n"
            stats += f"Files changed: {comparison.files}\n"
            stats += f"Additions: {comparison.ahead_by}\n"
            stats += f"Deletions: {comparison.behind_by}\n\n"
            stats += "Commits:\n"
            
            results_widget.insert(tk.END, stats)
            
            # Add commit list with buttons
            for commit in comparison.commits:
                frame = ttk.Frame(results_widget)
                results_widget.window_create(tk.END, window=frame)
                
                # Commit info
                commit_info = f"{commit.commit.message}\n"
                ttk.Label(frame, text=commit_info).pack(side=tk.LEFT)
                
                # View button
                view_btn = ttk.Button(frame, text="View Diff",
                                    command=lambda c=commit: webbrowser.open(c.html_url))
                view_btn.pack(side=tk.LEFT, padx=5)
                
                # Merge button
                merge_btn = ttk.Button(frame, text="Merge",
                                     command=lambda c=commit: self.merge_commit(c, repo_name))
                merge_btn.pack(side=tk.LEFT, padx=5)
                
                results_widget.insert(tk.END, "\n")
                
        except Exception as e:
            messagebox.showerror("Error", f"Comparison failed: {str(e)}")

    def merge_commit(self, commit, repo_name):
        try:
            # Create temp directory if needed
            if not self.temp_dir:
                self.temp_dir = tempfile.mkdtemp()
                
            # Clone repository if needed
            if not self.local_repo:
                repo_url = f"https://github.com/{repo_name}.git"
                self.local_repo = git.Repo.clone_from(repo_url, self.temp_dir)
                
            # Cherry-pick the commit
            self.local_repo.git.cherry_pick(commit.sha)
            
            # Push changes
            self.local_repo.git.push()
            
            messagebox.showinfo("Success", f"Successfully merged commit {commit.sha[:7]}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to merge commit: {str(e)}")
            
            # Cleanup on error
            if self.local_repo:
                self.local_repo.git.cherry_pick('--abort')
                
    def cleanup(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.cleanup)
        self.root.mainloop()

if __name__ == "__main__":
    app = GitHubCompare()
    app.run()
