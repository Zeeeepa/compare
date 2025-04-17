import tkinter as tk
from tkinter import ttk, messagebox
import os
from github import Github, GithubException
import webbrowser

class GitHubCompare:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Branch Comparison Tool")
        self.root.geometry("800x600")
        
        # Initialize GitHub client
        self.github_token = os.getenv("GITHUB_TOKEN")
        if not self.github_token:
            self.show_settings_dialog()
        else:
            self.github = Github(self.github_token)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create tabs
        self.local_tab = ttk.Frame(self.notebook)
        self.origin_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.local_tab, text='Local Branch Compare')
        self.notebook.add(self.origin_tab, text='Origin Compare')
        
        # Setup local compare tab
        self.setup_local_tab()
        
        # Setup origin compare tab
        self.setup_origin_tab()
        
        # Add settings button
        self.settings_button = ttk.Button(self.root, text="⚙️ Settings", command=self.show_settings_dialog)
        self.settings_button.pack(side='bottom', pady=5)

    def setup_local_tab(self):
        # Repository selection
        repo_frame = ttk.LabelFrame(self.local_tab, text="Repository Selection", padding=10)
        repo_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side='left')
        self.repo_var = tk.StringVar()
        self.repo_combo = ttk.Combobox(repo_frame, textvariable=self.repo_var)
        self.repo_combo.pack(side='left', padx=5)
        self.repo_combo.bind('<<ComboboxSelected>>', self.update_branches)
        
        # Branch selection
        branch_frame = ttk.LabelFrame(self.local_tab, text="Branch Selection", padding=10)
        branch_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(branch_frame, text="Base Branch:").pack(side='left')
        self.base_branch_var = tk.StringVar()
        self.base_branch_combo = ttk.Combobox(branch_frame, textvariable=self.base_branch_var)
        self.base_branch_combo.pack(side='left', padx=5)
        
        ttk.Label(branch_frame, text="Compare Branch:").pack(side='left', padx=5)
        self.compare_branch_var = tk.StringVar()
        self.compare_branch_combo = ttk.Combobox(branch_frame, textvariable=self.compare_branch_var)
        self.compare_branch_combo.pack(side='left', padx=5)
        
        # Compare button
        self.compare_button = ttk.Button(self.local_tab, text="Compare Branches", command=self.compare_branches)
        self.compare_button.pack(pady=10)
        
        # Results frame
        self.results_frame = ttk.Frame(self.local_tab)
        self.results_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Scrollable results
        self.canvas = tk.Canvas(self.results_frame)
        scrollbar = ttk.Scrollbar(self.results_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def setup_origin_tab(self):
        # Repository selection
        repo_frame = ttk.LabelFrame(self.origin_tab, text="Repository Selection", padding=10)
        repo_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side='left')
        self.origin_repo_var = tk.StringVar()
        self.origin_repo_combo = ttk.Combobox(repo_frame, textvariable=self.origin_repo_var)
        self.origin_repo_combo.pack(side='left', padx=5)
        self.origin_repo_combo.bind('<<ComboboxSelected>>', self.update_origin_branches)
        
        # Branch selection
        branch_frame = ttk.LabelFrame(self.origin_tab, text="Branch Selection", padding=10)
        branch_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(branch_frame, text="Local Branch:").pack(side='left')
        self.origin_local_branch_var = tk.StringVar()
        self.origin_local_branch_combo = ttk.Combobox(branch_frame, textvariable=self.origin_local_branch_var)
        self.origin_local_branch_combo.pack(side='left', padx=5)
        
        # Compare button
        self.origin_compare_button = ttk.Button(self.origin_tab, text="Compare with Origin", command=self.compare_with_origin)
        self.origin_compare_button.pack(pady=10)
        
        # Results frame
        self.origin_results_frame = ttk.Frame(self.origin_tab)
        self.origin_results_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Scrollable results
        self.origin_canvas = tk.Canvas(self.origin_results_frame)
        origin_scrollbar = ttk.Scrollbar(self.origin_results_frame, orient="vertical", command=self.origin_canvas.yview)
        self.origin_scrollable_frame = ttk.Frame(self.origin_canvas)
        
        self.origin_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.origin_canvas.configure(scrollregion=self.origin_canvas.bbox("all"))
        )
        
        self.origin_canvas.create_window((0, 0), window=self.origin_scrollable_frame, anchor="nw")
        self.origin_canvas.configure(yscrollcommand=origin_scrollbar.set)
        
        self.origin_canvas.pack(side="left", fill="both", expand=True)
        origin_scrollbar.pack(side="right", fill="y")

    def show_settings_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Settings")
        dialog.geometry("400x150")
        dialog.transient(self.root)
        
        ttk.Label(dialog, text="GitHub Token:").pack(pady=10)
        token_entry = ttk.Entry(dialog, width=50)
        token_entry.pack(pady=5)
        if self.github_token:
            token_entry.insert(0, self.github_token)
        
        def save_settings():
            token = token_entry.get().strip()
            if token:
                os.environ["GITHUB_TOKEN"] = token
                self.github_token = token
                self.github = Github(token)
                self.update_repo_list()
                dialog.destroy()
                messagebox.showinfo("Success", "Settings saved successfully!")
            else:
                messagebox.showerror("Error", "Please enter a valid GitHub token!")
        
        ttk.Button(dialog, text="Save", command=save_settings).pack(pady=10)

    def update_repo_list(self):
        try:
            repos = [repo.full_name for repo in self.github.get_user().get_repos()]
            self.repo_combo['values'] = repos
            self.origin_repo_combo['values'] = repos
        except GithubException as e:
            messagebox.showerror("Error", f"Failed to fetch repositories: {str(e)}")

    def update_branches(self, event=None):
        try:
            repo = self.github.get_repo(self.repo_var.get())
            branches = [branch.name for branch in repo.get_branches()]
            self.base_branch_combo['values'] = branches
            self.compare_branch_combo['values'] = branches
            
            # Set default branch as base
            default_branch = repo.default_branch
            if default_branch in branches:
                self.base_branch_var.set(default_branch)
        except GithubException as e:
            messagebox.showerror("Error", f"Failed to fetch branches: {str(e)}")

    def update_origin_branches(self, event=None):
        try:
            repo = self.github.get_repo(self.origin_repo_var.get())
            branches = [branch.name for branch in repo.get_branches()]
            self.origin_local_branch_combo['values'] = branches
            
            # Set default branch
            default_branch = repo.default_branch
            if default_branch in branches:
                self.origin_local_branch_var.set(default_branch)
        except GithubException as e:
            messagebox.showerror("Error", f"Failed to fetch branches: {str(e)}")

    def compare_branches(self):
        try:
            repo = self.github.get_repo(self.repo_var.get())
            base = self.base_branch_var.get()
            compare = self.compare_branch_var.get()
            
            # Clear previous results
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            
            comparison = repo.compare(base, compare)
            
            # Show comparison summary
            summary = f"Comparing {base}...{compare}\n"
            summary += f"Total commits: {len(comparison.commits)}\n"
            summary += f"Files changed: {comparison.total_commits}\n"
            ttk.Label(self.scrollable_frame, text=summary, wraplength=700).pack(pady=10)
            
            # Show commits
            for commit in comparison.commits:
                frame = ttk.Frame(self.scrollable_frame)
                frame.pack(fill='x', pady=5)
                
                # Commit info
                info_text = f"{commit.commit.message}\n"
                stats = commit.stats
                info_text += f"{stats.total} changed files with {stats.additions} additions and {stats.deletions} deletions"
                ttk.Label(frame, text=info_text, wraplength=500).pack(side='left', padx=5)
                
                # View diff button
                diff_url = f"https://github.com/{repo.full_name}/commit/{commit.sha}"
                ttk.Button(frame, text="View Diff", 
                          command=lambda url=diff_url: webbrowser.open(url)).pack(side='right', padx=5)
                
                # Merge button
                ttk.Button(frame, text="Merge", 
                          command=lambda c=commit: self.merge_commit(repo, c)).pack(side='right', padx=5)
                
                ttk.Separator(self.scrollable_frame, orient='horizontal').pack(fill='x', pady=5)
                
        except GithubException as e:
            messagebox.showerror("Error", f"Failed to compare branches: {str(e)}")

    def compare_with_origin(self):
        try:
            repo = self.github.get_repo(self.origin_repo_var.get())
            parent = repo.parent
            if not parent:
                messagebox.showerror("Error", "Selected repository is not a fork!")
                return
            
            # Clear previous results
            for widget in self.origin_scrollable_frame.winfo_children():
                widget.destroy()
            
            local_branch = self.origin_local_branch_var.get()
            parent_branch = parent.default_branch
            
            comparison = repo.compare(parent_branch, local_branch)
            
            # Show comparison summary
            summary = f"Comparing with origin: {parent.full_name}:{parent_branch}...{repo.full_name}:{local_branch}\n"
            summary += f"Commits behind: {comparison.behind_by}\n"
            summary += f"Commits ahead: {comparison.ahead_by}\n"
            ttk.Label(self.origin_scrollable_frame, text=summary, wraplength=700).pack(pady=10)
            
            if comparison.behind_by > 0:
                ttk.Label(self.origin_scrollable_frame, text="Commits you are behind:", wraplength=700).pack(pady=5)
                
                # Show commits
                for commit in comparison.commits:
                    frame = ttk.Frame(self.origin_scrollable_frame)
                    frame.pack(fill='x', pady=5)
                    
                    # Commit info
                    info_text = f"{commit.commit.message}\n"
                    stats = commit.stats
                    info_text += f"{stats.total} changed files with {stats.additions} additions and {stats.deletions} deletions"
                    ttk.Label(frame, text=info_text, wraplength=500).pack(side='left', padx=5)
                    
                    # View diff button
                    diff_url = f"https://github.com/{parent.full_name}/commit/{commit.sha}"
                    ttk.Button(frame, text="View Diff", 
                              command=lambda url=diff_url: webbrowser.open(url)).pack(side='right', padx=5)
                    
                    # Merge button
                    ttk.Button(frame, text="Merge", 
                              command=lambda c=commit: self.merge_commit(repo, c)).pack(side='right', padx=5)
                    
                    ttk.Separator(self.origin_scrollable_frame, orient='horizontal').pack(fill='x', pady=5)
                
        except GithubException as e:
            messagebox.showerror("Error", f"Failed to compare with origin: {str(e)}")

    def merge_commit(self, repo, commit):
        try:
            # Create a new branch for the cherry-pick
            base_branch = repo.default_branch
            new_branch = f"cherry-pick-{commit.sha[:7]}"
            base_ref = repo.get_git_ref(f"heads/{base_branch}")
            repo.create_git_ref(ref=f"refs/heads/{new_branch}", sha=base_ref.object.sha)
            
            # Cherry-pick the commit
            repo.merge(new_branch, commit.sha, f"Cherry-pick: {commit.commit.message}")
            
            messagebox.showinfo("Success", f"Successfully merged commit {commit.sha[:7]}")
            
            # Refresh the comparison
            if self.notebook.select() == str(self.local_tab):
                self.compare_branches()
            else:
                self.compare_with_origin()
                
        except GithubException as e:
            messagebox.showerror("Error", f"Failed to merge commit: {str(e)}")

    def run(self):
        if self.github_token:
            self.update_repo_list()
        self.root.mainloop()

if __name__ == "__main__":
    app = GitHubCompare()
    app.run()
