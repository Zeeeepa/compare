import os
import tkinter as tk
from tkinter import ttk, messagebox
import json
from github import Github
import webbrowser
import tempfile
import subprocess
import shutil
from git import Repo

class GitHubCompare:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Branch Comparison Tool")
        self.root.geometry("800x600")
        
        # Initialize GitHub client
        self.github = None
        self.load_github_token()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Create tabs
        self.local_tab = ttk.Frame(self.notebook)
        self.origin_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.local_tab, text='Local Compare')
        self.notebook.add(self.origin_tab, text='Origin Compare')
        
        # Setup both tabs
        self.setup_local_tab()
        self.setup_origin_tab()
        
        # Add settings button
        self.settings_button = ttk.Button(self.root, text="⚙️ Settings", command=self.show_settings)
        self.settings_button.pack(pady=5)

    def setup_local_tab(self):
        # Repository selection
        ttk.Label(self.local_tab, text="Repository:").pack(pady=5)
        self.repo_var = tk.StringVar()
        self.repo_dropdown = ttk.Combobox(self.local_tab, textvariable=self.repo_var)
        self.repo_dropdown.pack(pady=5)
        self.repo_dropdown.bind('<<ComboboxSelected>>', self.update_branches)
        
        # Branch selection
        ttk.Label(self.local_tab, text="Base Branch:").pack(pady=5)
        self.base_branch_var = tk.StringVar()
        self.base_branch_dropdown = ttk.Combobox(self.local_tab, textvariable=self.base_branch_var)
        self.base_branch_dropdown.pack(pady=5)
        
        ttk.Label(self.local_tab, text="Compare Branch:").pack(pady=5)
        self.compare_branch_var = tk.StringVar()
        self.compare_branch_dropdown = ttk.Combobox(self.local_tab, textvariable=self.compare_branch_var)
        self.compare_branch_dropdown.pack(pady=5)
        
        # Compare button
        ttk.Button(self.local_tab, text="Compare Branches", 
                  command=lambda: self.compare_branches(False)).pack(pady=20)
        
        # Results
        self.local_results = tk.Text(self.local_tab, height=15, width=70)
        self.local_results.pack(pady=10, padx=10, expand=True, fill='both')

    def setup_origin_tab(self):
        # Repository selection
        ttk.Label(self.origin_tab, text="Repository:").pack(pady=5)
        self.origin_repo_var = tk.StringVar()
        self.origin_repo_dropdown = ttk.Combobox(self.origin_tab, textvariable=self.origin_repo_var)
        self.origin_repo_dropdown.pack(pady=5)
        self.origin_repo_dropdown.bind('<<ComboboxSelected>>', self.update_origin_branches)
        
        # Branch selection
        ttk.Label(self.origin_tab, text="Base Branch:").pack(pady=5)
        self.origin_base_branch_var = tk.StringVar()
        self.origin_base_branch_dropdown = ttk.Combobox(self.origin_tab, textvariable=self.origin_base_branch_var)
        self.origin_base_branch_dropdown.pack(pady=5)
        
        ttk.Label(self.origin_tab, text="Compare Branch:").pack(pady=5)
        self.origin_compare_branch_var = tk.StringVar()
        self.origin_compare_branch_dropdown = ttk.Combobox(self.origin_tab, textvariable=self.origin_compare_branch_var)
        self.origin_compare_branch_dropdown.pack(pady=5)
        
        # Compare button
        ttk.Button(self.origin_tab, text="Compare with Origin", 
                  command=lambda: self.compare_branches(True)).pack(pady=20)
        
        # Results
        self.origin_results = tk.Text(self.origin_tab, height=15, width=70)
        self.origin_results.pack(pady=10, padx=10, expand=True, fill='both')

    def load_github_token(self):
        try:
            with open('github_token.json', 'r') as f:
                data = json.load(f)
                token = data.get('token')
                if token:
                    self.github = Github(token)
                    self.update_repo_list()
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_github_token(self, token):
        with open('github_token.json', 'w') as f:
            json.dump({'token': token}, f)
        self.github = Github(token)
        self.update_repo_list()

    def show_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x200")
        
        ttk.Label(settings_window, text="GitHub Token:").pack(pady=10)
        token_entry = ttk.Entry(settings_window, width=40)
        token_entry.pack(pady=5)
        
        def save_settings():
            token = token_entry.get()
            if token:
                self.save_github_token(token)
                settings_window.destroy()
                messagebox.showinfo("Success", "GitHub token saved successfully!")
            else:
                messagebox.showerror("Error", "Please enter a GitHub token")
        
        ttk.Button(settings_window, text="Save", command=save_settings).pack(pady=20)

    def update_repo_list(self):
        if not self.github:
            return
        
        try:
            repos = [repo.full_name for repo in self.github.get_user().get_repos()]
            self.repo_dropdown['values'] = repos
            self.origin_repo_dropdown['values'] = repos
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch repositories: {str(e)}")

    def update_branches(self, event=None):
        if not self.github or not self.repo_var.get():
            return
        
        try:
            repo = self.github.get_repo(self.repo_var.get())
            branches = [branch.name for branch in repo.get_branches()]
            self.base_branch_dropdown['values'] = branches
            self.compare_branch_dropdown['values'] = branches
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch branches: {str(e)}")

    def update_origin_branches(self, event=None):
        if not self.github or not self.origin_repo_var.get():
            return
        
        try:
            repo = self.github.get_repo(self.origin_repo_var.get())
            branches = [branch.name for branch in repo.get_branches()]
            self.origin_base_branch_dropdown['values'] = branches
            self.origin_compare_branch_dropdown['values'] = branches
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch branches: {str(e)}")

    def compare_branches(self, is_origin=False):
        try:
            if not self.github:
                messagebox.showerror("Error", "Please set your GitHub token in settings first!")
                return

            repo_name = self.repo_var.get()
            if not repo_name:
                messagebox.showerror("Error", "Please select a repository!")
                return

            repo = self.github.get_repo(repo_name)
            base_branch = self.base_branch_var.get()
            compare_branch = self.compare_branch_var.get()

            if is_origin:
                parent = repo.parent
                if not parent:
                    messagebox.showerror("Error", "This repository has no parent/origin!")
                    return
                comparison = repo.compare(base_branch, f"{parent.owner.login}:{compare_branch}")
            else:
                comparison = repo.compare(base_branch, compare_branch)

            # Clear previous results
            for widget in self.results_frame.winfo_children():
                widget.destroy()

            # Show comparison stats
            stats = f"Comparing {base_branch} with {compare_branch}\n\n"
            
            # Get total commits ahead/behind
            ahead_commits = list(comparison.ahead_commits)
            behind_commits = list(comparison.behind_commits)
            
            stats += f"Commits ahead: {len(ahead_commits)}\n"
            stats += f"Commits behind: {len(behind_commits)}\n"
            stats += f"Total commits: {len(ahead_commits) + len(behind_commits)}\n"
            stats += f"Files changed: {len(list(comparison.files))}\n"
            
            Label(self.results_frame, text=stats).pack(pady=10)

            # Show commit list with stats
            for commit in behind_commits:
                frame = Frame(self.results_frame, relief=RAISED, borderwidth=1)
                frame.pack(fill=X, padx=5, pady=5)
                
                # Get commit stats
                files_changed = 0
                additions = 0
                deletions = 0
                try:
                    detailed_commit = repo.get_commit(commit.sha)
                    files_changed = len(list(detailed_commit.files))
                    for file in detailed_commit.files:
                        additions += file.additions
                        deletions += file.deletions
                except:
                    pass

                info_text = f"{commit.commit.message}\n{files_changed} changed files with {additions} additions and {deletions} deletions"
                Label(frame, text=info_text, justify=LEFT, wraplength=500).pack(side=LEFT, padx=5)

                Button(frame, text="View Diff", 
                       command=lambda c=commit: webbrowser.open(c.html_url)).pack(side=RIGHT, padx=5)
                
                Button(frame, text="Merge", 
                       command=lambda c=commit: self.merge_commit(c.sha, repo_name)).pack(side=RIGHT, padx=5)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to compare branches: {str(e)}")

    def merge_commit(self, commit_sha, repo_name):
        try:
            # Clone repo if not already cloned
            if not os.path.exists(self.workspace):
                os.makedirs(self.workspace)
            
            repo_path = os.path.join(self.workspace, repo_name.split('/')[-1])
            if not os.path.exists(repo_path):
                Repo.clone_from(f"https://github.com/{repo_name}.git", repo_path)
            
            repo = Repo(repo_path)
            
            # Fetch and cherry-pick the commit
            repo.git.fetch('origin', commit_sha)
            repo.git.cherry_pick(commit_sha)
            
            # Push changes
            repo.git.push('origin', 'HEAD:main')
            
            messagebox.showinfo("Success", f"Successfully merged commit {commit_sha[:7]}")
            
            # Refresh the comparison
            self.compare_branches()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to merge commit: {str(e)}")
            # Clean up workspace on error
            if os.path.exists(self.workspace):
                shutil.rmtree(self.workspace)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = GitHubCompare()
    app.run()
