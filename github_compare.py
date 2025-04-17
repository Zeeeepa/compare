import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from github import Github
from github.GithubException import GithubException
import webbrowser

class GithubCompareApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Branch Comparison Tool")
        self.root.geometry("800x600")
        
        # Initialize GitHub API token from environment or settings
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.github = None
        self.selected_repo = None
        self.source_branch = None
        self.target_branch = None
        
        self.setup_ui()
        
        # If no token is set, show settings dialog
        if not self.github_token:
            self.show_settings_dialog()
    
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Settings button
        settings_btn = ttk.Button(main_frame, text="⚙️ Settings", command=self.show_settings_dialog)
        settings_btn.grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # Repository selection
        ttk.Label(main_frame, text="Repository:").grid(row=1, column=0, sticky=tk.W)
        self.repo_combo = ttk.Combobox(main_frame, width=50)
        self.repo_combo.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=5)
        self.repo_combo.bind("<<ComboboxSelected>>", self.on_repo_selected)
        
        # Branch selection
        ttk.Label(main_frame, text="Source Branch:").grid(row=2, column=0, sticky=tk.W)
        self.source_branch_combo = ttk.Combobox(main_frame, width=50)
        self.source_branch_combo.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Label(main_frame, text="Target Branch:").grid(row=3, column=0, sticky=tk.W)
        self.target_branch_combo = ttk.Combobox(main_frame, width=50)
        self.target_branch_combo.grid(row=3, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        # Compare button
        compare_btn = ttk.Button(main_frame, text="Compare Branches", command=self.compare_branches)
        compare_btn.grid(row=4, column=0, columnspan=3, pady=10)
        
        # Commits list
        self.commits_frame = ttk.Frame(main_frame)
        self.commits_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for commits list
        self.canvas = tk.Canvas(self.commits_frame)
        scrollbar = ttk.Scrollbar(self.commits_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        if self.github_token:
            self.initialize_github()
    
    def show_settings_dialog(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x150")
        
        ttk.Label(settings_window, text="GitHub API Token:").pack(pady=5)
        token_entry = ttk.Entry(settings_window, width=50)
        token_entry.insert(0, self.github_token)
        token_entry.pack(pady=5)
        
        def save_settings():
            token = token_entry.get().strip()
            if token:
                try:
                    # Test token validity
                    g = Github(token)
                    g.get_user().login
                    self.github_token = token
                    self.initialize_github()
                    settings_window.destroy()
                    messagebox.showinfo("Success", "GitHub token validated successfully!")
                except GithubException:
                    messagebox.showerror("Error", "Invalid GitHub token!")
            else:
                messagebox.showerror("Error", "Please enter a GitHub token!")
        
        ttk.Button(settings_window, text="Save", command=save_settings).pack(pady=10)
        ttk.Label(settings_window, text="Note: Token needs repo access permissions").pack(pady=5)
    
    def initialize_github(self):
        try:
            self.github = Github(self.github_token)
            repos = [repo.full_name for repo in self.github.get_user().get_repos()]
            self.repo_combo["values"] = repos
            if repos:
                self.repo_combo.set(repos[0])
                self.on_repo_selected(None)
        except GithubException as e:
            messagebox.showerror("Error", f"Failed to initialize GitHub: {str(e)}")
    
    def on_repo_selected(self, event):
        try:
            repo_name = self.repo_combo.get()
            self.selected_repo = self.github.get_repo(repo_name)
            branches = [branch.name for branch in self.selected_repo.get_branches()]
            
            self.source_branch_combo["values"] = branches
            self.target_branch_combo["values"] = branches
            
            if branches:
                self.source_branch_combo.set(branches[0])
                self.target_branch_combo.set(self.selected_repo.default_branch)
        except GithubException as e:
            messagebox.showerror("Error", f"Failed to load repository: {str(e)}")
    
    def compare_branches(self):
        if not self.selected_repo:
            messagebox.showerror("Error", "Please select a repository first!")
            return
        
        source = self.source_branch_combo.get()
        target = self.target_branch_combo.get()
        
        if not source or not target:
            messagebox.showerror("Error", "Please select both source and target branches!")
            return
        
        try:
            # Clear previous commits
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            
            comparison = self.selected_repo.compare(target, source)
            
            if not comparison.commits:
                ttk.Label(self.scrollable_frame, text="No commits to compare").pack(pady=10)
                return
            
            for commit in comparison.commits:
                commit_frame = ttk.Frame(self.scrollable_frame)
                commit_frame.pack(fill=tk.X, pady=5, padx=5)
                
                # Commit info
                info_text = f"{commit.commit.message}\n{len(commit.files)} changed files with {commit.stats.additions} additions and {commit.stats.deletions} deletions"
                ttk.Label(commit_frame, text=info_text, wraplength=600).pack(side=tk.LEFT, padx=5)
                
                # View button
                ttk.Button(
                    commit_frame, 
                    text="View Diff",
                    command=lambda url=commit.html_url: webbrowser.open(url)
                ).pack(side=tk.RIGHT, padx=2)
                
                # Merge button
                ttk.Button(
                    commit_frame,
                    text="Merge",
                    command=lambda c=commit: self.merge_commit(c)
                ).pack(side=tk.RIGHT, padx=2)
                
                # Separator
                ttk.Separator(self.scrollable_frame, orient="horizontal").pack(fill=tk.X, pady=5)
                
        except GithubException as e:
            messagebox.showerror("Error", f"Failed to compare branches: {str(e)}")
    
    def merge_commit(self, commit):
        try:
            # Create a new branch for the cherry-pick
            base_branch = self.target_branch_combo.get()
            new_branch = f"cherry-pick-{commit.sha[:7]}"
            
            # Create new branch from base
            base_ref = self.selected_repo.get_git_ref(f"heads/{base_branch}")
            self.selected_repo.create_git_ref(ref=f"refs/heads/{new_branch}", sha=base_ref.object.sha)
            
            # Cherry-pick the commit
            self.selected_repo.merge(new_branch, commit.sha, f"Cherry-pick: {commit.commit.message}")
            
            # Create pull request
            pr = self.selected_repo.create_pull(
                title=f"Cherry-pick: {commit.commit.message}",
                body=f"Cherry-picked commit {commit.sha} from {self.source_branch_combo.get()}",
                head=new_branch,
                base=base_branch
            )
            
            messagebox.showinfo(
                "Success", 
                f"Created PR #{pr.number} for the cherry-pick!\nView it here: {pr.html_url}"
            )
            
        except GithubException as e:
            messagebox.showerror("Error", f"Failed to merge commit: {str(e)}")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = GithubCompareApp()
    app.run()
