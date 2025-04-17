import tkinter as tk
from tkinter import ttk, messagebox
import os
import webbrowser
from github import Github, GithubException

class GitHubCompare:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Branch Comparison Tool")
        
        # Initialize GitHub client
        self.github_token = os.getenv("GITHUB_TOKEN")
        if not self.github_token:
            self.show_settings()
        else:
            self.g = Github(self.github_token)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(pady=10, expand=True)
        
        # Create tabs
        self.local_tab = ttk.Frame(self.notebook)
        self.origin_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.local_tab, text="Local Compare")
        self.notebook.add(self.origin_tab, text="Origin Compare")
        
        # Setup local compare tab
        self.setup_local_tab()
        
        # Setup origin compare tab
        self.setup_origin_tab()
        
        # Add settings button
        settings_btn = ttk.Button(self.root, text="⚙️ Settings", command=self.show_settings)
        settings_btn.pack(pady=5)

    def setup_local_tab(self):
        # Repository selection
        repo_frame = ttk.Frame(self.local_tab)
        repo_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side='left')
        self.repo_var = tk.StringVar()
        self.repo_combo = ttk.Combobox(repo_frame, textvariable=self.repo_var)
        self.repo_combo.pack(side='left', padx=5, expand=True, fill='x')
        self.repo_combo.bind('<<ComboboxSelected>>', self.update_branches)
        
        # Branch selection
        branches_frame = ttk.Frame(self.local_tab)
        branches_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(branches_frame, text="Base Branch:").pack(side='left')
        self.base_branch_var = tk.StringVar()
        self.base_branch_combo = ttk.Combobox(branches_frame, textvariable=self.base_branch_var)
        self.base_branch_combo.pack(side='left', padx=5, expand=True, fill='x')
        
        ttk.Label(branches_frame, text="Compare Branch:").pack(side='left')
        self.compare_branch_var = tk.StringVar()
        self.compare_branch_combo = ttk.Combobox(branches_frame, textvariable=self.compare_branch_var)
        self.compare_branch_combo.pack(side='left', padx=5, expand=True, fill='x')
        
        # Compare button
        compare_btn = ttk.Button(self.local_tab, text="Compare Branches", command=self.compare_branches)
        compare_btn.pack(pady=10)
        
        # Results
        self.local_results = ttk.Frame(self.local_tab)
        self.local_results.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.local_text = tk.Text(self.local_results, height=10, wrap='word')
        self.local_text.pack(fill='both', expand=True)
        
        # Update repository list
        self.update_repos()

    def setup_origin_tab(self):
        # Repository selection
        repo_frame = ttk.Frame(self.origin_tab)
        repo_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side='left')
        self.origin_repo_var = tk.StringVar()
        self.origin_repo_combo = ttk.Combobox(repo_frame, textvariable=self.origin_repo_var)
        self.origin_repo_combo.pack(side='left', padx=5, expand=True, fill='x')
        self.origin_repo_combo.bind('<<ComboboxSelected>>', self.update_origin_info)
        
        # Branch selection
        branches_frame = ttk.Frame(self.origin_tab)
        branches_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(branches_frame, text="Base Branch:").pack(side='left')
        self.origin_base_branch_var = tk.StringVar()
        self.origin_base_branch_combo = ttk.Combobox(branches_frame, textvariable=self.origin_base_branch_var)
        self.origin_base_branch_combo.pack(side='left', padx=5, expand=True, fill='x')
        
        ttk.Label(branches_frame, text="Compare Branch:").pack(side='left')
        self.origin_compare_branch_var = tk.StringVar()
        self.origin_compare_branch_combo = ttk.Combobox(branches_frame, textvariable=self.origin_compare_branch_var)
        self.origin_compare_branch_combo.pack(side='left', padx=5, expand=True, fill='x')
        
        # Compare button
        compare_btn = ttk.Button(self.origin_tab, text="Compare with Origin", command=self.compare_with_origin)
        compare_btn.pack(pady=10)
        
        # Results
        self.origin_results = ttk.Frame(self.origin_tab)
        self.origin_results.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.origin_text = tk.Text(self.origin_results, height=10, wrap='word')
        self.origin_text.pack(fill='both', expand=True)
        
        # Update repository list
        self.update_repos()

    def update_repos(self):
        try:
            repos = [repo.full_name for repo in self.g.get_user().get_repos()]
            self.repo_combo['values'] = repos
            self.origin_repo_combo['values'] = repos
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch repositories: {str(e)}")

    def update_branches(self, event=None):
        try:
            repo = self.g.get_repo(self.repo_var.get())
            branches = [branch.name for branch in repo.get_branches()]
            self.base_branch_combo['values'] = branches
            self.compare_branch_combo['values'] = branches
            
            # Set default branch
            default_branch = repo.default_branch
            self.base_branch_var.set(default_branch)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch branches: {str(e)}")

    def update_origin_info(self, event=None):
        try:
            repo = self.g.get_repo(self.origin_repo_var.get())
            parent = repo.parent
            if parent:
                # Get branches from both repos
                repo_branches = [branch.name for branch in repo.get_branches()]
                parent_branches = [branch.name for branch in parent.get_branches()]
                
                # Update branch dropdowns
                self.origin_base_branch_combo['values'] = repo_branches
                self.origin_compare_branch_combo['values'] = parent_branches
                
                # Set default branches
                self.origin_base_branch_var.set(repo.default_branch)
                self.origin_compare_branch_var.set(parent.default_branch)
            else:
                messagebox.showwarning("Warning", "This repository is not a fork. Cannot compare with origin.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch origin info: {str(e)}")

    def compare_branches(self):
        try:
            repo = self.g.get_repo(self.repo_var.get())
            base = self.base_branch_var.get()
            compare = self.compare_branch_var.get()
            
            comparison = repo.compare(base, compare)
            self.local_text.delete(1.0, tk.END)
            
            # Display comparison info
            self.local_text.insert(tk.END, f"Comparing {base}...{compare}\n")
            self.local_text.insert(tk.END, f"Commits ahead: {comparison.ahead_by}\n")
            self.local_text.insert(tk.END, f"Commits behind: {comparison.behind_by}\n\n")
            
            # Display commits
            for commit in comparison.commits:
                stats = commit.stats
                info_text = f"{commit.commit.message}\n{stats.total} changed files with {stats.additions} additions and {stats.deletions} deletions"
                self.local_text.insert(tk.END, f"Commit: {commit.sha[:7]}\n{info_text}\n")
                
                # Add view and merge buttons
                view_btn = ttk.Button(self.local_results, text="View Diff", 
                                    command=lambda c=commit: webbrowser.open(c.html_url))
                self.local_text.window_create(tk.END, window=view_btn)
                
                merge_btn = ttk.Button(self.local_results, text="Merge", 
                                     command=lambda c=commit: self.merge_commit(c.sha))
                self.local_text.window_create(tk.END, window=merge_btn)
                self.local_text.insert(tk.END, "\n\n")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to compare branches: {str(e)}")

    def compare_with_origin(self):
        try:
            repo = self.g.get_repo(self.origin_repo_var.get())
            parent = repo.parent
            
            if not parent:
                messagebox.showwarning("Warning", "This repository is not a fork. Cannot compare with origin.")
                return
                
            base = self.origin_base_branch_var.get()
            compare = self.origin_compare_branch_var.get()
            
            # Compare with parent repository
            comparison = repo.compare(base, f"{parent.owner.login}:{compare}")
            self.origin_text.delete(1.0, tk.END)
            
            # Display comparison info
            self.origin_text.insert(tk.END, f"Comparing {repo.full_name}:{base}...{parent.full_name}:{compare}\n")
            self.origin_text.insert(tk.END, f"Commits ahead: {comparison.ahead_by}\n")
            self.origin_text.insert(tk.END, f"Commits behind: {comparison.behind_by}\n\n")
            
            # Display commits
            for commit in comparison.commits:
                stats = commit.stats
                info_text = f"{commit.commit.message}\n{stats.total} changed files with {stats.additions} additions and {stats.deletions} deletions"
                self.origin_text.insert(tk.END, f"Commit: {commit.sha[:7]}\n{info_text}\n")
                
                # Add view and merge buttons
                view_btn = ttk.Button(self.origin_results, text="View Diff", 
                                    command=lambda c=commit: webbrowser.open(c.html_url))
                self.origin_text.window_create(tk.END, window=view_btn)
                
                merge_btn = ttk.Button(self.origin_results, text="Merge", 
                                     command=lambda c=commit: self.merge_commit(c.sha))
                self.origin_text.window_create(tk.END, window=merge_btn)
                self.origin_text.insert(tk.END, "\n\n")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to compare with origin: {str(e)}")

    def merge_commit(self, commit_sha):
        try:
            repo = self.g.get_repo(self.repo_var.get())
            # Create a cherry-pick merge
            base_branch = self.base_branch_var.get()
            repo.merge(base_branch, commit_sha, f"Cherry-pick merge of {commit_sha[:7]}")
            messagebox.showinfo("Success", f"Successfully merged commit {commit_sha[:7]}")
            # Refresh the comparison
            self.compare_branches()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to merge commit: {str(e)}")

    def show_settings(self):
        settings = tk.Toplevel(self.root)
        settings.title("Settings")
        settings.geometry("400x150")
        
        ttk.Label(settings, text="GitHub Token:").pack(pady=5)
        token_entry = ttk.Entry(settings, show="*", width=50)
        token_entry.pack(pady=5)
        if self.github_token:
            token_entry.insert(0, self.github_token)
        
        def save_settings():
            token = token_entry.get().strip()
            if token:
                os.environ["GITHUB_TOKEN"] = token
                self.github_token = token
                self.g = Github(token)
                self.update_repos()
                settings.destroy()
            else:
                messagebox.showerror("Error", "Please enter a valid GitHub token")
        
        ttk.Button(settings, text="Save", command=save_settings).pack(pady=10)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = GitHubCompare()
    app.run()
