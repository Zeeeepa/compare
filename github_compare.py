import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import subprocess
from github import Github
from github.Repository import Repository
from github.GithubException import GithubException
import webbrowser
import tempfile

class GitHubCompare:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Repository Comparison Tool")
        self.root.geometry("800x600")
        
        # Initialize GitHub connection
        self.gh = None
        self.user = None
        self.load_token()
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Create tabs
        self.local_tab = ttk.Frame(self.notebook)
        self.origin_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.local_tab, text='Local Branch Compare')
        self.notebook.add(self.origin_tab, text='Origin Compare')
        
        # Setup UI elements
        self.setup_local_tab()
        self.setup_origin_tab()
        self.setup_settings_button()

    def setup_settings_button(self):
        settings_btn = ttk.Button(self.root, text="⚙️ Settings", command=self.show_settings)
        settings_btn.pack(pady=5)

    def setup_local_tab(self):
        # Repository selection
        repo_frame = ttk.Frame(self.local_tab)
        repo_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side='left')
        self.local_repo_var = tk.StringVar()
        self.local_repo_dropdown = ttk.Combobox(repo_frame, textvariable=self.local_repo_var)
        self.local_repo_dropdown.pack(side='left', fill='x', expand=True, padx=5)
        
        # Branch selection frame
        branch_frame = ttk.Frame(self.local_tab)
        branch_frame.pack(fill='x', padx=5, pady=5)
        
        # Base branch
        base_frame = ttk.Frame(branch_frame)
        base_frame.pack(fill='x', pady=2)
        ttk.Label(base_frame, text="Base Branch:").pack(side='left')
        self.base_branch_var = tk.StringVar()
        self.base_branch_dropdown = ttk.Combobox(base_frame, textvariable=self.base_branch_var)
        self.base_branch_dropdown.pack(side='left', fill='x', expand=True, padx=5)
        
        # Compare branch
        compare_frame = ttk.Frame(branch_frame)
        compare_frame.pack(fill='x', pady=2)
        ttk.Label(compare_frame, text="Compare Branch:").pack(side='left')
        self.compare_branch_var = tk.StringVar()
        self.compare_branch_dropdown = ttk.Combobox(compare_frame, textvariable=self.compare_branch_var)
        self.compare_branch_dropdown.pack(side='left', fill='x', expand=True, padx=5)
        
        # Compare button
        ttk.Button(self.local_tab, text="Compare Branches", 
                  command=lambda: self.compare_branches(False)).pack(pady=20)
        
        # Results
        self.local_results_text = tk.Text(self.local_tab, height=20, wrap=tk.WORD)
        self.local_results_text.pack(fill='both', expand=True, padx=5, pady=5)

    def setup_origin_tab(self):
        # Repository selection
        repo_frame = ttk.Frame(self.origin_tab)
        repo_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side='left')
        self.origin_repo_var = tk.StringVar()
        self.origin_repo_dropdown = ttk.Combobox(repo_frame, textvariable=self.origin_repo_var)
        self.origin_repo_dropdown.pack(side='left', fill='x', expand=True, padx=5)
        
        # Compare button
        ttk.Button(self.origin_tab, text="Compare with Origin", 
                  command=lambda: self.compare_branches(True)).pack(pady=20)
        
        # Results
        self.origin_results_text = tk.Text(self.origin_tab, height=20, wrap=tk.WORD)
        self.origin_results_text.pack(fill='both', expand=True, padx=5, pady=5)

    def load_token(self):
        try:
            token_file = os.path.expanduser('~/.github_token')
            if os.path.exists(token_file):
                with open(token_file, 'r') as f:
                    token = f.read().strip()
                    if token:
                        self.gh = Github(token)
                        self.user = self.gh.get_user()
                        self.update_repo_lists()
        except Exception as e:
            print(f"Error loading token: {e}")

    def save_token(self, token):
        try:
            token_file = os.path.expanduser('~/.github_token')
            with open(token_file, 'w') as f:
                f.write(token)
            self.gh = Github(token)
            self.user = self.gh.get_user()
            self.update_repo_lists()
            messagebox.showinfo("Success", "GitHub token saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save token: {e}")

    def show_settings(self):
        settings = tk.Toplevel(self.root)
        settings.title("Settings")
        settings.geometry("400x150")
        
        ttk.Label(settings, text="GitHub Token:").pack(pady=5)
        token_entry = ttk.Entry(settings, width=50)
        token_entry.pack(pady=5)
        
        if os.path.exists(os.path.expanduser('~/.github_token')):
            with open(os.path.expanduser('~/.github_token'), 'r') as f:
                token_entry.insert(0, f.read().strip())
        
        ttk.Button(settings, text="Save", 
                  command=lambda: self.save_token(token_entry.get())).pack(pady=10)

    def update_repo_lists(self):
        if self.gh and self.user:
            repos = [repo.name for repo in self.user.get_repos()]
            self.local_repo_dropdown['values'] = repos
            self.origin_repo_dropdown['values'] = repos
            
            # Update branch dropdowns when repo is selected
            self.local_repo_var.trace('w', lambda *args: self.update_branch_lists())
            self.origin_repo_var.trace('w', lambda *args: self.update_branch_lists())

    def update_branch_lists(self):
        if self.gh and self.local_repo_var.get():
            try:
                repo = self.gh.get_user().get_repo(self.local_repo_var.get())
                branches = [branch.name for branch in repo.get_branches()]
                self.base_branch_dropdown['values'] = branches
                self.compare_branch_dropdown['values'] = branches
            except Exception as e:
                print(f"Error updating branch lists: {e}")

    def get_commit_stats(self, commit):
        try:
            total_changes = 0
            additions = 0
            deletions = 0
            for file in commit.get_files():
                total_changes += 1
                additions += file.additions
                deletions += file.deletions
            return total_changes, additions, deletions
        except Exception as e:
            print(f"Error getting commit stats: {e}")
            return 0, 0, 0

    def compare_branches(self, compare_with_origin=False):
        if not self.gh:
            messagebox.showerror("Error", "Please set your GitHub token in settings first!")
            return

        try:
            if compare_with_origin:
                # Get the repository and its parent
                repo = self.gh.get_user().get_repo(self.origin_repo_var.get())
                if not repo.parent:
                    messagebox.showerror("Error", "This repository has no parent/origin repository!")
                    return
                
                parent_repo = repo.parent
                base_branch = parent_repo.default_branch
                compare_branch = repo.default_branch
                
                # Get comparison
                comparison = parent_repo.compare(base_branch, f"{repo.owner.login}:{compare_branch}")
                
                # Clear previous results
                self.origin_results_text.delete(1.0, tk.END)
                
                # Show comparison stats
                stats = f"Comparing with origin repository: {parent_repo.full_name}\n"
                stats += f"Base branch: {base_branch}\n"
                stats += f"Compare branch: {compare_branch}\n\n"
                stats += f"Commits ahead: {len(comparison.ahead_by)}\n"
                stats += f"Commits behind: {len(comparison.behind_by)}\n\n"
                stats += "Behind commits:\n"
                
                self.origin_results_text.insert(tk.END, stats)
                
                # Show behind commits with buttons
                for i, commit in enumerate(comparison.behind_by, 1):
                    changes, adds, dels = self.get_commit_stats(commit)
                    commit_frame = ttk.Frame(self.origin_tab)
                    
                    # Commit info
                    info_text = f"\n{i}. {commit.commit.message}\n"
                    info_text += f"{changes} changed files with {adds} additions and {dels} deletions\n"
                    self.origin_results_text.insert(tk.END, info_text)
                    
                    # Add buttons
                    btn_frame = ttk.Frame(self.origin_tab)
                    btn_frame.pack(fill='x', padx=5, pady=2)
                    
                    ttk.Button(btn_frame, text="View Diff", 
                             command=lambda c=commit: webbrowser.open(c.html_url)).pack(side='left', padx=5)
                    
                    ttk.Button(btn_frame, text="Merge", 
                             command=lambda c=commit: self.merge_commit(c, repo)).pack(side='left', padx=5)
                    
                    self.origin_results_text.window_create(tk.END, window=btn_frame)
                    self.origin_results_text.insert(tk.END, "\n")
                
            else:
                # Local branch comparison
                repo = self.gh.get_user().get_repo(self.local_repo_var.get())
                base = self.base_branch_var.get()
                compare = self.compare_branch_var.get()
                
                if not base or not compare:
                    messagebox.showerror("Error", "Please select both base and compare branches!")
                    return
                
                comparison = repo.compare(base, compare)
                
                # Clear previous results
                self.local_results_text.delete(1.0, tk.END)
                
                # Show comparison stats
                stats = f"Comparing branches in {repo.full_name}\n"
                stats += f"Base: {base}\n"
                stats += f"Compare: {compare}\n\n"
                stats += f"Commits ahead: {len(comparison.ahead_by)}\n"
                stats += f"Commits behind: {len(comparison.behind_by)}\n\n"
                stats += "Commits:\n"
                
                self.local_results_text.insert(tk.END, stats)
                
                # Show commits with buttons
                for i, commit in enumerate(comparison.commits, 1):
                    changes, adds, dels = self.get_commit_stats(commit)
                    
                    # Commit info
                    info_text = f"\n{i}. {commit.commit.message}\n"
                    info_text += f"{changes} changed files with {adds} additions and {dels} deletions\n"
                    self.local_results_text.insert(tk.END, info_text)
                    
                    # Add buttons
                    btn_frame = ttk.Frame(self.local_tab)
                    btn_frame.pack(fill='x', padx=5, pady=2)
                    
                    ttk.Button(btn_frame, text="View Diff", 
                             command=lambda c=commit: webbrowser.open(c.html_url)).pack(side='left', padx=5)
                    
                    self.local_results_text.window_create(tk.END, window=btn_frame)
                    self.local_results_text.insert(tk.END, "\n")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to compare branches: {str(e)}")

    def merge_commit(self, commit, repo):
        try:
            # Create a temporary directory for the clone
            with tempfile.TemporaryDirectory() as temp_dir:
                # Clone the repository
                clone_url = repo.clone_url.replace("https://", f"https://{self.gh._Github__requester._Requester__authorizationHeader.split(' ')[1]}@")
                subprocess.run(['git', 'clone', clone_url, temp_dir], check=True)
                
                # Configure git
                subprocess.run(['git', 'config', 'user.name', 'GitHub Compare Tool'], cwd=temp_dir, check=True)
                subprocess.run(['git', 'config', 'user.email', 'noreply@github.com'], cwd=temp_dir, check=True)
                
                # Cherry-pick the commit
                subprocess.run(['git', 'cherry-pick', commit.sha], cwd=temp_dir, check=True)
                
                # Push the changes
                subprocess.run(['git', 'push', 'origin', 'HEAD'], cwd=temp_dir, check=True)
                
                messagebox.showinfo("Success", f"Successfully merged commit {commit.sha[:7]}")
                
                # Refresh the comparison
                self.compare_branches(True)
                
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to merge commit: {e.output if hasattr(e, 'output') else str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to merge commit: {str(e)}")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = GitHubCompare()
    app.run()
