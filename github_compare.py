import os
import tkinter as tk
from tkinter import ttk, messagebox
import json
from github import Github
import webbrowser
import tempfile
import subprocess

class GitHubComparisonTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Branch Comparison Tool")
        self.root.geometry("800x600")
        
        # Initialize GitHub client
        self.gh = None
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
                    self.gh = Github(token)
                    self.update_repo_list()
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_github_token(self, token):
        with open('github_token.json', 'w') as f:
            json.dump({'token': token}, f)
        self.gh = Github(token)
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
        if not self.gh:
            return
        
        try:
            repos = [repo.full_name for repo in self.gh.get_user().get_repos()]
            self.repo_dropdown['values'] = repos
            self.origin_repo_dropdown['values'] = repos
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch repositories: {str(e)}")

    def update_branches(self, event=None):
        if not self.gh or not self.repo_var.get():
            return
        
        try:
            repo = self.gh.get_repo(self.repo_var.get())
            branches = [branch.name for branch in repo.get_branches()]
            self.base_branch_dropdown['values'] = branches
            self.compare_branch_dropdown['values'] = branches
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch branches: {str(e)}")

    def update_origin_branches(self, event=None):
        if not self.gh or not self.origin_repo_var.get():
            return
        
        try:
            repo = self.gh.get_repo(self.origin_repo_var.get())
            branches = [branch.name for branch in repo.get_branches()]
            self.origin_base_branch_dropdown['values'] = branches
            self.origin_compare_branch_dropdown['values'] = branches
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch branches: {str(e)}")

    def compare_branches(self, is_origin=False):
        if not self.gh:
            messagebox.showerror("Error", "Please set your GitHub token in settings first")
            return
        
        try:
            if is_origin:
                repo_name = self.origin_repo_var.get()
                base = self.origin_base_branch_var.get()
                compare = self.origin_compare_branch_var.get()
                results_widget = self.origin_results
            else:
                repo_name = self.repo_var.get()
                base = self.base_branch_var.get()
                compare = self.compare_branch_var.get()
                results_widget = self.local_results
            
            if not all([repo_name, base, compare]):
                messagebox.showerror("Error", "Please select repository and branches")
                return
            
            repo = self.gh.get_repo(repo_name)
            comparison = repo.compare(base, compare)
            
            # Clear previous results
            results_widget.delete(1.0, tk.END)
            
            # Show comparison stats
            stats = f"Comparing {base}...{compare}\n\n"
            stats += f"Commits ahead: {len(comparison.commits)}\n"
            stats += f"Total changes: {comparison.total_commits} commits\n"
            stats += f"Files changed: {comparison.files}\n"
            stats += f"Additions: {comparison.ahead_by}\n"
            stats += f"Deletions: {comparison.behind_by}\n\n"
            results_widget.insert(tk.END, stats)
            
            # Show commits
            results_widget.insert(tk.END, "Commits:\n")
            for commit in comparison.commits:
                frame = ttk.Frame(results_widget)
                
                # Commit info
                info_text = f"{commit.commit.message}\n"
                info_text += f"Files changed: {len(list(commit.files))} with {commit.stats.additions} additions and {commit.stats.deletions} deletions"
                
                ttk.Label(frame, text=info_text, wraplength=500).pack(side=tk.LEFT, padx=5)
                
                # View button
                view_btn = ttk.Button(frame, text="View Diff", 
                                    command=lambda url=commit.html_url: webbrowser.open(url))
                view_btn.pack(side=tk.LEFT, padx=5)
                
                # Merge button
                merge_btn = ttk.Button(frame, text="Merge", 
                                     command=lambda c=commit: self.merge_commit(repo, c))
                merge_btn.pack(side=tk.LEFT, padx=5)
                
                results_widget.window_create(tk.END, window=frame)
                results_widget.insert(tk.END, "\n\n")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to compare branches: {str(e)}")

    def merge_commit(self, repo, commit):
        try:
            # Create a temporary directory for cloning
            with tempfile.TemporaryDirectory() as temp_dir:
                # Clone the repository
                clone_url = f"https://github.com/{repo.full_name}.git"
                subprocess.run(['git', 'clone', clone_url, temp_dir], check=True)
                
                # Configure git
                subprocess.run(['git', 'config', 'user.name', 'GitHub Comparison Tool'], cwd=temp_dir)
                subprocess.run(['git', 'config', 'user.email', 'noreply@github.com'], cwd=temp_dir)
                
                # Cherry-pick the commit
                subprocess.run(['git', 'cherry-pick', commit.sha], cwd=temp_dir)
                
                # Push changes
                subprocess.run(['git', 'push', 'origin', 'HEAD'], cwd=temp_dir)
                
            messagebox.showinfo("Success", f"Successfully merged commit {commit.sha[:7]}")
            
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to merge commit: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = GitHubComparisonTool()
    app.run()
