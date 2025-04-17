import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from github import Github, GithubException
import webbrowser
import tempfile
import subprocess

class GitHubCompare:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Branch Comparison Tool")
        self.root.geometry("800x600")
        
        # Initialize GitHub API
        self.github = None
        self.user = None
        self.load_github_token()
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Create tabs
        self.local_tab = ttk.Frame(self.notebook)
        self.origin_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.local_tab, text='Local Compare')
        self.notebook.add(self.origin_tab, text='Origin Compare')
        
        # Initialize UI components
        self.init_local_tab()
        self.init_origin_tab()
        self.init_settings_button()

    def init_local_tab(self):
        # Repository selection
        repo_frame = ttk.LabelFrame(self.local_tab, text="Repository Selection", padding=10)
        repo_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side='left')
        self.repo_dropdown = ttk.Combobox(repo_frame, width=40)
        self.repo_dropdown.pack(side='left', padx=5)
        
        # Branch selection
        branch_frame = ttk.LabelFrame(self.local_tab, text="Branch Selection", padding=10)
        branch_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(branch_frame, text="Base Branch:").pack(side='left')
        self.base_branch_dropdown = ttk.Combobox(branch_frame, width=30)
        self.base_branch_dropdown.pack(side='left', padx=5)
        
        ttk.Label(branch_frame, text="Compare Branch:").pack(side='left')
        self.compare_branch_dropdown = ttk.Combobox(branch_frame, width=30)
        self.compare_branch_dropdown.pack(side='left', padx=5)
        
        # Compare button
        ttk.Button(self.local_tab, text="Compare Branches", 
                  command=lambda: self.compare_branches(False)).pack(pady=10)
        
        # Results
        self.local_results = tk.Text(self.local_tab, height=20, width=80)
        self.local_results.pack(padx=5, pady=5)

    def init_origin_tab(self):
        # Repository selection
        repo_frame = ttk.LabelFrame(self.origin_tab, text="Repository Selection", padding=10)
        repo_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side='left')
        self.origin_repo_dropdown = ttk.Combobox(repo_frame, width=40)
        self.origin_repo_dropdown.pack(side='left', padx=5)
        
        # Branch selection
        branch_frame = ttk.LabelFrame(self.origin_tab, text="Branch Selection", padding=10)
        branch_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(branch_frame, text="Base Branch:").pack(side='left')
        self.origin_base_branch = ttk.Combobox(branch_frame, width=30)
        self.origin_base_branch.pack(side='left', padx=5)
        
        # Compare button
        ttk.Button(self.origin_tab, text="Compare with Origin", 
                  command=lambda: self.compare_branches(True)).pack(pady=10)
        
        # Results
        self.origin_results = tk.Text(self.origin_tab, height=20, width=80)
        self.origin_results.pack(padx=5, pady=5)

    def init_settings_button(self):
        settings_frame = ttk.Frame(self.root)
        settings_frame.pack(fill='x', padx=5, pady=5)
        ttk.Button(settings_frame, text="⚙️ Settings", command=self.show_settings).pack(side='right')

    def show_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x200")
        
        ttk.Label(settings_window, text="GitHub Token:").pack(pady=5)
        token_entry = ttk.Entry(settings_window, width=40)
        token_entry.pack(pady=5)
        if self.github:
            token_entry.insert(0, self.github._Github__requester._Requester__auth.token)
        
        def save_token():
            token = token_entry.get().strip()
            if token:
                try:
                    # Test token
                    g = Github(token)
                    g.get_user().login
                    # Save token
                    with open('github_token.json', 'w') as f:
                        json.dump({'token': token}, f)
                    self.load_github_token()
                    self.update_repo_lists()
                    messagebox.showinfo("Success", "Token saved successfully!")
                    settings_window.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"Invalid token: {str(e)}")
            else:
                messagebox.showerror("Error", "Please enter a valid token")
        
        ttk.Button(settings_window, text="Save", command=save_token).pack(pady=10)

    def load_github_token(self):
        try:
            with open('github_token.json', 'r') as f:
                data = json.load(f)
                self.github = Github(data['token'])
                self.user = self.github.get_user()
                self.update_repo_lists()
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load GitHub token: {str(e)}")

    def update_repo_lists(self):
        if not self.github or not self.user:
            messagebox.showerror("Error", "Please set your GitHub token in settings first")
            return
        
        try:
            # Get repositories
            repos = [repo.full_name for repo in self.user.get_repos()]
            
            # Update dropdowns
            self.repo_dropdown['values'] = repos
            self.origin_repo_dropdown['values'] = repos
            
            # Bind selection events
            self.repo_dropdown.bind('<<ComboboxSelected>>', self.update_branch_lists)
            self.origin_repo_dropdown.bind('<<ComboboxSelected>>', self.update_origin_branch_lists)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch repositories: {str(e)}")

    def update_branch_lists(self, event=None):
        if not self.repo_dropdown.get():
            return
            
        try:
            repo = self.github.get_repo(self.repo_dropdown.get())
            branches = [branch.name for branch in repo.get_branches()]
            
            self.base_branch_dropdown['values'] = branches
            self.compare_branch_dropdown['values'] = branches
            
            # Set defaults
            if 'main' in branches:
                self.base_branch_dropdown.set('main')
            elif 'master' in branches:
                self.base_branch_dropdown.set('master')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch branches: {str(e)}")

    def update_origin_branch_lists(self, event=None):
        if not self.origin_repo_dropdown.get():
            return
            
        try:
            repo = self.github.get_repo(self.origin_repo_dropdown.get())
            parent = repo.parent
            if parent:
                branches = [branch.name for branch in parent.get_branches()]
                self.origin_base_branch['values'] = branches
                
                # Set default
                if 'main' in branches:
                    self.origin_base_branch.set('main')
                elif 'master' in branches:
                    self.origin_base_branch.set('master')
            else:
                messagebox.showinfo("Info", "This repository has no parent/origin repository")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch origin branches: {str(e)}")

    def compare_branches(self, compare_with_origin=False):
        try:
            if compare_with_origin:
                if not all([self.origin_repo_dropdown.get(), self.origin_base_branch.get()]):
                    messagebox.showerror("Error", "Please select repository and branch")
                    return
                    
                repo = self.github.get_repo(self.origin_repo_dropdown.get())
                parent = repo.parent
                if not parent:
                    messagebox.showerror("Error", "Selected repository has no parent/origin")
                    return
                
                comparison = repo.compare(
                    base=f"{parent.owner.login}:{self.origin_base_branch.get()}", 
                    head=f"{repo.owner.login}:{self.origin_base_branch.get()}"
                )
                
                # Clear previous results
                self.origin_results.delete(1.0, tk.END)
                
                # Show comparison stats
                stats = f"Comparing with origin repository: {parent.full_name}\n"
                stats += f"Total commits different: {comparison.total_commits}\n"
                stats += f"Files changed: {len(list(comparison.files))}\n"
                stats += f"Additions: {comparison.ahead_by}\n"
                stats += f"Deletions: {comparison.behind_by}\n\n"
                
                # Show commits
                stats += "Commits:\n"
                for i, commit in enumerate(comparison.commits, 1):
                    stats += f"\n{i}. {commit.commit.message.splitlines()[0]}\n"
                    stats += f"   Author: {commit.commit.author.name}\n"
                    stats += f"   SHA: {commit.sha}\n"
                    
                    # Add view/merge buttons
                    view_button = ttk.Button(
                        self.origin_results,
                        text="View Diff",
                        command=lambda c=commit: webbrowser.open(c.html_url)
                    )
                    merge_button = ttk.Button(
                        self.origin_results,
                        text="Merge",
                        command=lambda c=commit: self.merge_commit(c, repo)
                    )
                    
                    self.origin_results.insert(tk.END, stats)
                    self.origin_results.window_create(tk.END, window=view_button)
                    self.origin_results.window_create(tk.END, window=merge_button)
                    self.origin_results.insert(tk.END, "\n")
                    
                    stats = ""  # Reset for next iteration
                
            else:
                if not all([self.repo_dropdown.get(), self.base_branch_dropdown.get(), self.compare_branch_dropdown.get()]):
                    messagebox.showerror("Error", "Please select repository and both branches")
                    return
                    
                repo = self.github.get_repo(self.repo_dropdown.get())
                comparison = repo.compare(
                    base=self.base_branch_dropdown.get(),
                    head=self.compare_branch_dropdown.get()
                )
                
                # Clear previous results
                self.local_results.delete(1.0, tk.END)
                
                # Show comparison stats
                stats = f"Comparing branches in {repo.full_name}\n"
                stats += f"Base: {self.base_branch_dropdown.get()}\n"
                stats += f"Compare: {self.compare_branch_dropdown.get()}\n"
                stats += f"Total commits different: {comparison.total_commits}\n"
                stats += f"Files changed: {len(list(comparison.files))}\n"
                stats += f"Additions: {comparison.ahead_by}\n"
                stats += f"Deletions: {comparison.behind_by}\n\n"
                
                # Show commits
                stats += "Commits:\n"
                for i, commit in enumerate(comparison.commits, 1):
                    stats += f"\n{i}. {commit.commit.message.splitlines()[0]}\n"
                    stats += f"   Author: {commit.commit.author.name}\n"
                    stats += f"   SHA: {commit.sha}\n"
                    
                    # Add view button
                    view_button = ttk.Button(
                        self.local_results,
                        text="View Diff",
                        command=lambda c=commit: webbrowser.open(c.html_url)
                    )
                    
                    self.local_results.insert(tk.END, stats)
                    self.local_results.window_create(tk.END, window=view_button)
                    self.local_results.insert(tk.END, "\n")
                    
                    stats = ""  # Reset for next iteration
                
        except Exception as e:
            messagebox.showerror("Error", f"Comparison failed: {str(e)}")

    def merge_commit(self, commit, repo):
        try:
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Clone repository
                clone_url = repo.clone_url.replace(
                    "https://", 
                    f"https://{self.github._Github__requester._Requester__auth.token}@"
                )
                subprocess.run(["git", "clone", clone_url, temp_dir], check=True)
                
                # Configure git
                subprocess.run(["git", "config", "user.name", self.user.login], cwd=temp_dir, check=True)
                subprocess.run(["git", "config", "user.email", self.user.email], cwd=temp_dir, check=True)
                
                # Cherry-pick commit
                subprocess.run(["git", "cherry-pick", commit.sha], cwd=temp_dir, check=True)
                
                # Push changes
                subprocess.run(["git", "push", "origin", "HEAD"], cwd=temp_dir, check=True)
                
            messagebox.showinfo("Success", f"Successfully merged commit {commit.sha[:7]}")
            
            # Refresh comparison
            self.compare_branches(True)
            
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Merge failed: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Merge failed: {str(e)}")

    def run(self):
        if not self.github:
            self.show_settings()
        self.root.mainloop()

if __name__ == "__main__":
    app = GitHubCompare()
    app.run()
