import tkinter as tk
from tkinter import ttk, messagebox
import os
from github import Github, GithubException
import json

class GitHubCompareApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Branch Comparison Tool")
        self.root.geometry("800x600")
        
        # GitHub token
        self.token = os.getenv("GITHUB_TOKEN")
        self.g = None
        if self.token:
            self.g = Github(self.token)
        
        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Settings button
        self.settings_btn = ttk.Button(self.main_frame, text="⚙️ Settings", command=self.show_settings)
        self.settings_btn.grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # Repository selection
        ttk.Label(self.main_frame, text="Repository:").grid(row=1, column=0, sticky=tk.W)
        self.repo_var = tk.StringVar()
        self.repo_combo = ttk.Combobox(self.main_frame, textvariable=self.repo_var)
        self.repo_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        self.repo_combo.bind('<<ComboboxSelected>>', self.on_repo_selected)
        
        # Compare with origin checkbox
        self.compare_origin_var = tk.BooleanVar()
        self.compare_origin_check = ttk.Checkbutton(
            self.main_frame, 
            text="Compare with Origin Repository", 
            variable=self.compare_origin_var,
            command=self.on_compare_origin_changed
        )
        self.compare_origin_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Branch selection
        ttk.Label(self.main_frame, text="Base Branch:").grid(row=3, column=0, sticky=tk.W)
        self.base_branch_var = tk.StringVar()
        self.base_branch_combo = ttk.Combobox(self.main_frame, textvariable=self.base_branch_var)
        self.base_branch_combo.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(self.main_frame, text="Compare Branch:").grid(row=4, column=0, sticky=tk.W)
        self.compare_branch_var = tk.StringVar()
        self.compare_branch_combo = ttk.Combobox(self.main_frame, textvariable=self.compare_branch_var)
        self.compare_branch_combo.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Compare button
        self.compare_btn = ttk.Button(self.main_frame, text="Compare Branches", command=self.compare_branches)
        self.compare_btn.grid(row=5, column=0, columnspan=2, pady=10)
        
        # Results frame
        self.results_frame = ttk.Frame(self.main_frame)
        self.results_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Commit list
        self.commit_list = tk.Text(self.results_frame, height=15, wrap=tk.WORD)
        self.commit_list.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for commit list
        self.scrollbar = ttk.Scrollbar(self.results_frame, orient=tk.VERTICAL, command=self.commit_list.yview)
        self.scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.commit_list.configure(yscrollcommand=self.scrollbar.set)
        
        # Configure grid weights
        self.main_frame.columnconfigure(1, weight=1)
        self.results_frame.columnconfigure(0, weight=1)
        
        # Initialize
        self.current_repo = None
        self.update_repo_list()
        
    def show_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x200")
        
        frame = ttk.Frame(settings_window, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(frame, text="GitHub Token:").grid(row=0, column=0, sticky=tk.W)
        token_entry = ttk.Entry(frame, width=40)
        token_entry.grid(row=0, column=1, pady=5)
        token_entry.insert(0, self.token if self.token else "")
        
        def save_settings():
            new_token = token_entry.get().strip()
            if new_token:
                os.environ["GITHUB_TOKEN"] = new_token
                self.token = new_token
                self.g = Github(self.token)
                self.update_repo_list()
                messagebox.showinfo("Success", "Settings saved successfully!")
                settings_window.destroy()
            else:
                messagebox.showerror("Error", "Please enter a GitHub token")
        
        save_btn = ttk.Button(frame, text="Save", command=save_settings)
        save_btn.grid(row=1, column=0, columnspan=2, pady=10)
        
    def update_repo_list(self):
        if not self.g:
            messagebox.showerror("Error", "Please set your GitHub token in settings")
            return
        
        try:
            repos = [repo.full_name for repo in self.g.get_user().get_repos()]
            self.repo_combo['values'] = repos
        except GithubException as e:
            messagebox.showerror("Error", f"Failed to fetch repositories: {str(e)}")
    
    def on_repo_selected(self, event=None):
        repo_name = self.repo_var.get()
        try:
            self.current_repo = self.g.get_repo(repo_name)
            branches = [branch.name for branch in self.current_repo.get_branches()]
            self.base_branch_combo['values'] = branches
            self.compare_branch_combo['values'] = branches
            
            # If comparing with origin, update branch list
            if self.compare_origin_var.get():
                self.update_origin_branches()
        except GithubException as e:
            messagebox.showerror("Error", f"Failed to fetch branches: {str(e)}")
    
    def on_compare_origin_changed(self):
        if self.current_repo and self.compare_origin_var.get():
            self.update_origin_branches()
        else:
            self.on_repo_selected()
    
    def update_origin_branches(self):
        try:
            # Get the parent/origin repository
            parent_repo = self.current_repo.parent
            if parent_repo:
                origin_branches = [branch.name for branch in parent_repo.get_branches()]
                self.compare_branch_combo['values'] = origin_branches
            else:
                messagebox.showwarning("Warning", "This repository doesn't have a parent/origin repository")
                self.compare_origin_var.set(False)
        except GithubException as e:
            messagebox.showerror("Error", f"Failed to fetch origin branches: {str(e)}")
            self.compare_origin_var.set(False)
    
    def compare_branches(self):
        if not self.current_repo:
            messagebox.showerror("Error", "Please select a repository first")
            return
        
        base_branch = self.base_branch_var.get()
        compare_branch = self.compare_branch_var.get()
        
        if not base_branch or not compare_branch:
            messagebox.showerror("Error", "Please select both branches to compare")
            return
        
        try:
            # Clear previous results
            self.commit_list.delete(1.0, tk.END)
            
            # Get the comparison repository (origin or current)
            compare_repo = self.current_repo.parent if self.compare_origin_var.get() else self.current_repo
            if not compare_repo and self.compare_origin_var.get():
                messagebox.showerror("Error", "No origin repository found")
                return
            
            # Get commits that are in compare_branch but not in base_branch
            comparison = compare_repo.compare(base_branch, compare_branch)
            
            if not comparison.commits:
                self.commit_list.insert(tk.END, "No differences found between branches")
                return
            
            for commit in comparison.commits:
                # Get detailed commit info
                detailed_commit = compare_repo.get_commit(commit.sha)
                files_changed = len(list(detailed_commit.files))
                
                # Format commit info
                info_text = f"Commit: {commit.sha[:7]}\n"
                info_text += f"Title: {commit.commit.message.split('\n')[0]}\n"
                info_text += f"{files_changed} changed files with {detailed_commit.stats.additions} additions and {detailed_commit.stats.deletions} deletions\n"
                
                # Add buttons for this commit
                view_url = commit.html_url
                info_text += f"View Diff: {view_url}\n"
                
                # Add separator
                info_text += "-" * 80 + "\n\n"
                
                self.commit_list.insert(tk.END, info_text)
        
        except GithubException as e:
            messagebox.showerror("Error", f"Failed to compare branches: {str(e)}")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = GitHubCompareApp()
    app.run()
