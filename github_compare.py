import tkinter as tk
from tkinter import ttk, messagebox
import os
from github import Github
import webbrowser

class GitHubComparisonTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Branch Comparison Tool")
        self.root.geometry("800x600")
        
        # Initialize GitHub client
        self.github_token = os.getenv('GITHUB_TOKEN')
        if not self.github_token:
            self.show_settings()
        else:
            self.g = Github(self.github_token)
            
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Create tabs
        self.local_tab = ttk.Frame(self.notebook)
        self.origin_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.local_tab, text='Local Branch Compare')
        self.notebook.add(self.origin_tab, text='Origin Compare')
        
        # Setup both tabs
        self.setup_local_tab()
        self.setup_origin_tab()

    def setup_local_tab(self):
        # Repository selection frame
        repo_frame = ttk.LabelFrame(self.local_tab, text="Repository Selection", padding=10)
        repo_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side='left')
        self.local_repo_var = tk.StringVar()
        self.local_repo_combo = ttk.Combobox(repo_frame, textvariable=self.local_repo_var)
        self.local_repo_combo.pack(side='left', padx=5, expand=True, fill='x')
        
        # Branch selection frame
        branch_frame = ttk.LabelFrame(self.local_tab, text="Branch Selection", padding=10)
        branch_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(branch_frame, text="Base Branch:").grid(row=0, column=0, padx=5)
        self.base_branch_var = tk.StringVar()
        self.base_branch_combo = ttk.Combobox(branch_frame, textvariable=self.base_branch_var)
        self.base_branch_combo.grid(row=0, column=1, padx=5, sticky='ew')
        
        ttk.Label(branch_frame, text="Compare Branch:").grid(row=1, column=0, padx=5, pady=5)
        self.compare_branch_var = tk.StringVar()
        self.compare_branch_combo = ttk.Combobox(branch_frame, textvariable=self.compare_branch_var)
        self.compare_branch_combo.grid(row=1, column=1, padx=5, sticky='ew')
        
        branch_frame.grid_columnconfigure(1, weight=1)
        
        # Compare button
        ttk.Button(self.local_tab, text="Compare Branches", command=self.compare_local_branches).pack(pady=10)
        
        # Results frame
        self.local_results_frame = ttk.Frame(self.local_tab)
        self.local_results_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Commits list
        self.local_commits_list = tk.Text(self.local_results_frame, height=10, wrap=tk.WORD)
        self.local_commits_list.pack(fill='both', expand=True)

    def setup_origin_tab(self):
        # Repository selection frame
        repo_frame = ttk.LabelFrame(self.origin_tab, text="Repository Selection", padding=10)
        repo_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(repo_frame, text="Local Repository:").grid(row=0, column=0, padx=5)
        self.origin_repo_var = tk.StringVar()
        self.origin_repo_combo = ttk.Combobox(repo_frame, textvariable=self.origin_repo_var)
        self.origin_repo_combo.grid(row=0, column=1, padx=5, sticky='ew')
        
        ttk.Label(repo_frame, text="Origin Repository:").grid(row=1, column=0, padx=5, pady=5)
        self.origin_name_label = ttk.Label(repo_frame, text="")
        self.origin_name_label.grid(row=1, column=1, padx=5, sticky='w')
        
        repo_frame.grid_columnconfigure(1, weight=1)
        
        # Branch selection frame
        branch_frame = ttk.LabelFrame(self.origin_tab, text="Branch Selection", padding=10)
        branch_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(branch_frame, text="Local Branch:").grid(row=0, column=0, padx=5)
        self.origin_local_branch_var = tk.StringVar()
        self.origin_local_branch_combo = ttk.Combobox(branch_frame, textvariable=self.origin_local_branch_var)
        self.origin_local_branch_combo.grid(row=0, column=1, padx=5, sticky='ew')
        
        ttk.Label(branch_frame, text="Origin Branch:").grid(row=1, column=0, padx=5, pady=5)
        self.origin_branch_var = tk.StringVar()
        self.origin_branch_combo = ttk.Combobox(branch_frame, textvariable=self.origin_branch_var)
        self.origin_branch_combo.grid(row=1, column=1, padx=5, sticky='ew')
        
        branch_frame.grid_columnconfigure(1, weight=1)
        
        # Compare button
        ttk.Button(self.origin_tab, text="Compare with Origin", command=self.compare_with_origin).pack(pady=10)
        
        # Results frame
        self.origin_results_frame = ttk.Frame(self.origin_tab)
        self.origin_results_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Commits list with scrollbar
        commits_frame = ttk.Frame(self.origin_results_frame)
        commits_frame.pack(fill='both', expand=True)
        
        self.commits_scrollbar = ttk.Scrollbar(commits_frame)
        self.commits_scrollbar.pack(side='right', fill='y')
        
        self.commits_list = tk.Text(commits_frame, height=10, wrap=tk.WORD, yscrollcommand=self.commits_scrollbar.set)
        self.commits_list.pack(side='left', fill='both', expand=True)
        
        self.commits_scrollbar.config(command=self.commits_list.yview)

    def show_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x150")
        
        ttk.Label(settings_window, text="GitHub Token:").pack(pady=5)
        token_entry = ttk.Entry(settings_window, width=40)
        token_entry.pack(pady=5)
        
        def save_token():
            token = token_entry.get()
            if token:
                os.environ['GITHUB_TOKEN'] = token
                self.github_token = token
                self.g = Github(token)
                self.update_repo_lists()
                settings_window.destroy()
            else:
                messagebox.showerror("Error", "Please enter a valid GitHub token")
        
        ttk.Button(settings_window, text="Save", command=save_token).pack(pady=10)

    def update_repo_lists(self):
        try:
            # Get user's repositories
            repos = [repo.full_name for repo in self.g.get_user().get_repos()]
            
            # Update all repository comboboxes
            self.local_repo_combo['values'] = repos
            self.origin_repo_combo['values'] = repos
            
            # Set up callbacks for repository selection
            self.local_repo_combo.bind('<<ComboboxSelected>>', self.update_local_branches)
            self.origin_repo_combo.bind('<<ComboboxSelected>>', self.update_origin_info)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch repositories: {str(e)}")

    def update_local_branches(self, event=None):
        try:
            repo = self.g.get_repo(self.local_repo_var.get())
            branches = [branch.name for branch in repo.get_branches()]
            
            self.base_branch_combo['values'] = branches
            self.compare_branch_combo['values'] = branches
            
            # Set default branch as base
            default_branch = repo.default_branch
            self.base_branch_var.set(default_branch)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch branches: {str(e)}")

    def update_origin_info(self, event=None):
        try:
            repo = self.g.get_repo(self.origin_repo_var.get())
            parent = repo.parent
            
            if parent:
                self.origin_name_label.config(text=parent.full_name)
                branches = [branch.name for branch in parent.get_branches()]
                self.origin_branch_combo['values'] = branches
                self.origin_branch_combo.set(parent.default_branch)
                
                # Update local branches
                local_branches = [branch.name for branch in repo.get_branches()]
                self.origin_local_branch_combo['values'] = local_branches
                self.origin_local_branch_combo.set(repo.default_branch)
            else:
                self.origin_name_label.config(text="No parent repository found")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch origin info: {str(e)}")

    def compare_local_branches(self):
        try:
            repo = self.g.get_repo(self.local_repo_var.get())
            base = self.base_branch_var.get()
            compare = self.compare_branch_var.get()
            
            comparison = repo.compare(base, compare)
            
            self.local_commits_list.delete(1.0, tk.END)
            self.local_commits_list.insert(tk.END, f"Comparing {base}...{compare}\n")
            self.local_commits_list.insert(tk.END, f"Commits ahead: {comparison.ahead_by}\n")
            self.local_commits_list.insert(tk.END, f"Commits behind: {comparison.behind_by}\n\n")
            
            for commit in comparison.commits:
                stats = commit.stats
                self.local_commits_list.insert(tk.END, 
                    f"Commit: {commit.commit.message}\n"
                    f"Files changed: {stats.total}, "
                    f"Additions: {stats.additions}, "
                    f"Deletions: {stats.deletions}\n"
                    f"[View Diff] [Merge]\n\n"
                )
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to compare branches: {str(e)}")

    def compare_with_origin(self):
        try:
            repo = self.g.get_repo(self.origin_repo_var.get())
            parent = repo.parent
            
            if not parent:
                messagebox.showerror("Error", "No parent repository found")
                return
                
            local_branch = self.origin_local_branch_var.get()
            origin_branch = self.origin_branch_var.get()
            
            comparison = repo.compare(f"{parent.owner.login}:{origin_branch}", local_branch)
            
            self.commits_list.delete(1.0, tk.END)
            self.commits_list.insert(tk.END, 
                f"Comparing {parent.full_name}:{origin_branch} with {repo.full_name}:{local_branch}\n"
                f"Commits ahead: {comparison.ahead_by}\n"
                f"Commits behind: {comparison.behind_by}\n\n"
            )
            
            for i, commit in enumerate(comparison.commits, 1):
                stats = commit.stats
                
                # Create clickable links
                diff_link = f"https://github.com/{parent.full_name}/commit/{commit.sha}"
                
                self.commits_list.insert(tk.END, 
                    f"Commit {i}.\n"
                    f"\"{commit.commit.message}\"\n"
                    f"{stats.total} changed files with {stats.additions} additions and {stats.deletions} deletions\n"
                )
                
                # Make the links clickable
                start = self.commits_list.index("end-4c")
                end = self.commits_list.index("end-3c")
                
                self.commits_list.tag_add(f"link_{i}", start, end)
                self.commits_list.tag_config(f"link_{i}", foreground="blue", underline=True)
                self.commits_list.tag_bind(f"link_{i}", "<Button-1>", lambda e, url=diff_link: webbrowser.open(url))
                
                # Add merge button functionality
                merge_button = ttk.Button(
                    self.commits_list, 
                    text="Merge",
                    command=lambda c=commit: self.merge_commit(c, parent, repo)
                )
                self.commits_list.window_create("end-1c", window=merge_button)
                self.commits_list.insert(tk.END, "\n\n")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to compare with origin: {str(e)}")

    def merge_commit(self, commit, parent_repo, local_repo):
        try:
            # Create a cherry-pick merge
            message = f"Cherry-pick: {commit.commit.message}"
            local_repo.merge(
                commit.sha,
                message=message,
                merge_method='squash'
            )
            messagebox.showinfo("Success", f"Successfully merged commit {commit.sha[:7]}")
            
            # Refresh the comparison
            self.compare_with_origin()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to merge commit: {str(e)}")

    def run(self):
        # Add settings button
        settings_button = ttk.Button(self.root, text="⚙️", command=self.show_settings, width=3)
        settings_button.pack(anchor='ne', padx=5, pady=5)
        
        # Update repository lists if token is available
        if self.github_token:
            self.update_repo_lists()
            
        self.root.mainloop()

if __name__ == "__main__":
    app = GitHubComparisonTool()
    app.run()
