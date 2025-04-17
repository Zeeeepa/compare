import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from github import Github, GithubException
import webbrowser
import tempfile
import subprocess
import configparser

class GitHubCompare:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Repository Comparison")
        self.root.geometry("800x600")
        
        # Initialize GitHub token
        self.token = self.load_token()
        self.github = None
        if self.token:
            try:
                self.github = Github(self.token)
                self.user = self.github.get_user()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to initialize GitHub client: {str(e)}")
                self.token = None
        
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
        
        # Add settings button
        self.settings_button = ttk.Button(self.root, text="⚙️ Settings", command=self.show_settings)
        self.settings_button.pack(pady=5)

    def load_token(self):
        config = configparser.ConfigParser()
        if os.path.exists('github_config.ini'):
            config.read('github_config.ini')
            return config.get('GitHub', 'token', fallback=None)
        return None

    def save_token(self, token):
        config = configparser.ConfigParser()
        config['GitHub'] = {'token': token}
        with open('github_config.ini', 'w') as f:
            config.write(f)

    def show_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x200")
        
        ttk.Label(settings_window, text="GitHub Token:").pack(pady=10)
        token_entry = ttk.Entry(settings_window, width=40)
        if self.token:
            token_entry.insert(0, self.token)
        token_entry.pack(pady=5)
        
        def save_settings():
            new_token = token_entry.get().strip()
            if new_token:
                try:
                    # Test token
                    test_github = Github(new_token)
                    test_github.get_user()
                    self.token = new_token
                    self.github = test_github
                    self.save_token(new_token)
                    self.refresh_repo_lists()
                    messagebox.showinfo("Success", "GitHub token saved successfully!")
                    settings_window.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"Invalid GitHub token: {str(e)}")
            else:
                messagebox.showerror("Error", "Please enter a valid GitHub token")
        
        ttk.Button(settings_window, text="Save", command=save_settings).pack(pady=20)

    def setup_local_tab(self):
        # Repository selection
        repo_frame = ttk.LabelFrame(self.local_tab, text="Repository Selection")
        repo_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side='left', padx=5)
        self.local_repo_var = tk.StringVar()
        self.local_repo_dropdown = ttk.Combobox(repo_frame, textvariable=self.local_repo_var, state='readonly')
        self.local_repo_dropdown.pack(side='left', padx=5, fill='x', expand=True)
        
        # Branch selection
        branch_frame = ttk.LabelFrame(self.local_tab, text="Branch Selection")
        branch_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(branch_frame, text="Base Branch:").pack(side='left', padx=5)
        self.base_branch_var = tk.StringVar()
        self.base_branch_dropdown = ttk.Combobox(branch_frame, textvariable=self.base_branch_var, state='readonly')
        self.base_branch_dropdown.pack(side='left', padx=5, fill='x', expand=True)
        
        ttk.Label(branch_frame, text="Compare Branch:").pack(side='left', padx=5)
        self.compare_branch_var = tk.StringVar()
        self.compare_branch_dropdown = ttk.Combobox(branch_frame, textvariable=self.compare_branch_var, state='readonly')
        self.compare_branch_dropdown.pack(side='left', padx=5, fill='x', expand=True)
        
        # Compare button
        ttk.Button(self.local_tab, text="Compare Branches", 
                  command=lambda: self.compare_branches(False)).pack(pady=20)
        
        # Results
        self.local_results = tk.Text(self.local_tab, height=20, wrap='word')
        self.local_results.pack(fill='both', expand=True, padx=10, pady=5)

    def setup_origin_tab(self):
        # Repository selection
        repo_frame = ttk.LabelFrame(self.origin_tab, text="Repository Selection")
        repo_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side='left', padx=5)
        self.origin_repo_var = tk.StringVar()
        self.origin_repo_dropdown = ttk.Combobox(repo_frame, textvariable=self.origin_repo_var, state='readonly')
        self.origin_repo_dropdown.pack(side='left', padx=5, fill='x', expand=True)
        
        # Compare button
        ttk.Button(self.origin_tab, text="Compare with Origin", 
                  command=lambda: self.compare_branches(True)).pack(pady=20)
        
        # Results
        self.origin_results = tk.Text(self.origin_tab, height=20, wrap='word')
        self.origin_results.pack(fill='both', expand=True, padx=10, pady=5)

    def refresh_repo_lists(self):
        if not self.github:
            messagebox.showerror("Error", "Please set your GitHub token in Settings first")
            return
        
        try:
            # Get user's repositories
            repos = [repo.name for repo in self.user.get_repos()]
            
            # Update dropdowns
            self.local_repo_dropdown['values'] = repos
            self.origin_repo_dropdown['values'] = repos
            
            # Set up callbacks
            self.local_repo_var.trace('w', lambda *args: self.update_branch_lists())
            self.origin_repo_var.trace('w', lambda *args: self.update_branch_lists())
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch repositories: {str(e)}")

    def update_branch_lists(self):
        if not self.github:
            return
            
        try:
            repo_name = self.local_repo_var.get()
            if repo_name:
                repo = self.github.get_user().get_repo(repo_name)
                branches = [branch.name for branch in repo.get_branches()]
                self.base_branch_dropdown['values'] = branches
                self.compare_branch_dropdown['values'] = branches
                
                # Set default branch
                default_branch = repo.default_branch
                if default_branch in branches:
                    self.base_branch_var.set(default_branch)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch branches: {str(e)}")

    def compare_branches(self, compare_with_origin=False):
        if not self.github:
            messagebox.showerror("Error", "Please set your GitHub token in Settings first")
            return
            
        try:
            if compare_with_origin:
                repo_name = self.origin_repo_var.get()
                if not repo_name:
                    messagebox.showerror("Error", "Please select a repository")
                    return
                    
                repo = self.github.get_user().get_repo(repo_name)
                parent = repo.parent
                
                if not parent:
                    messagebox.showerror("Error", "Selected repository has no parent/origin repository")
                    return
                    
                # Compare with parent's default branch
                comparison = repo.compare(repo.default_branch, f"{parent.owner.login}:{parent.default_branch}")
                
                # Display results
                self.origin_results.delete(1.0, tk.END)
                self.origin_results.insert(tk.END, f"Comparing with origin repository: {parent.full_name}\n\n")
                self.origin_results.insert(tk.END, f"Commits ahead: {comparison.ahead_by}\n")
                self.origin_results.insert(tk.END, f"Commits behind: {comparison.behind_by}\n\n")
                
                if comparison.behind_by > 0:
                    self.origin_results.insert(tk.END, "Commits you are behind:\n\n")
                    for commit in comparison.commits:
                        commit_info = f"Commit: {commit.commit.message.splitlines()[0]}\n"
                        commit_info += f"Author: {commit.commit.author.name}\n"
                        commit_info += f"Files changed: {len(commit.files)}\n"
                        
                        # Add buttons frame
                        buttons_frame = ttk.Frame(self.origin_tab)
                        view_button = ttk.Button(buttons_frame, text="View Diff",
                                               command=lambda c=commit: webbrowser.open(c.html_url))
                        merge_button = ttk.Button(buttons_frame, text="Merge",
                                                command=lambda c=commit: self.merge_commit(repo, c))
                        view_button.pack(side='left', padx=5)
                        merge_button.pack(side='left', padx=5)
                        
                        self.origin_results.insert(tk.END, commit_info + "\n")
                        self.origin_results.window_create(tk.END, window=buttons_frame)
                        self.origin_results.insert(tk.END, "\n\n")
            else:
                repo_name = self.local_repo_var.get()
                base = self.base_branch_var.get()
                compare = self.compare_branch_var.get()
                
                if not all([repo_name, base, compare]):
                    messagebox.showerror("Error", "Please select repository and branches")
                    return
                    
                repo = self.github.get_user().get_repo(repo_name)
                comparison = repo.compare(base, compare)
                
                # Display results
                self.local_results.delete(1.0, tk.END)
                self.local_results.insert(tk.END, f"Comparing {base}...{compare}\n\n")
                self.local_results.insert(tk.END, f"Total commits: {len(comparison.commits)}\n")
                self.local_results.insert(tk.END, f"Files changed: {len(comparison.files)}\n")
                self.local_results.insert(tk.END, f"Total additions: {comparison.total_additions}\n")
                self.local_results.insert(tk.END, f"Total deletions: {comparison.total_deletions}\n\n")
                
                for commit in comparison.commits:
                    commit_info = f"Commit: {commit.commit.message.splitlines()[0]}\n"
                    commit_info += f"Author: {commit.commit.author.name}\n"
                    commit_info += f"Files changed: {len(commit.files)}\n"
                    
                    # Add view button
                    button_frame = ttk.Frame(self.local_tab)
                    view_button = ttk.Button(button_frame, text="View Diff",
                                           command=lambda c=commit: webbrowser.open(c.html_url))
                    view_button.pack(padx=5)
                    
                    self.local_results.insert(tk.END, commit_info + "\n")
                    self.local_results.window_create(tk.END, window=button_frame)
                    self.local_results.insert(tk.END, "\n\n")
                    
        except Exception as e:
            messagebox.showerror("Error", f"Comparison failed: {str(e)}")

    def merge_commit(self, repo, commit):
        try:
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Clone repository
                clone_url = repo.clone_url.replace("https://", f"https://{self.token}@")
                subprocess.run(["git", "clone", clone_url, temp_dir], check=True)
                
                # Configure git
                subprocess.run(["git", "config", "user.name", "GitHub Compare Tool"], cwd=temp_dir)
                subprocess.run(["git", "config", "user.email", "noreply@github.com"], cwd=temp_dir)
                
                # Cherry-pick commit
                subprocess.run(["git", "cherry-pick", commit.sha], cwd=temp_dir)
                
                # Push changes
                subprocess.run(["git", "push", "origin", "HEAD"], cwd=temp_dir)
                
            messagebox.showinfo("Success", "Commit merged successfully!")
            
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to merge commit: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to merge commit: {str(e)}")

    def run(self):
        if self.token:
            self.refresh_repo_lists()
        self.root.mainloop()

if __name__ == "__main__":
    app = GitHubCompare()
    app.run()
