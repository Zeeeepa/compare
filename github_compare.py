import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from github import Github, GithubException
import webbrowser
import git
import tempfile
import shutil

class GitHubCompare:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Repository Comparison")
        self.root.geometry("800x600")
        
        # Initialize GitHub API
        self.gh = None
        self.load_token()
        
        # Create main container
        self.container = ttk.Frame(self.root)
        self.container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.container)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.local_tab = ttk.Frame(self.notebook)
        self.origin_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.local_tab, text="Local Compare")
        self.notebook.add(self.origin_tab, text="Origin Compare")
        
        # Setup UI elements
        self.setup_local_tab()
        self.setup_origin_tab()
        self.setup_settings_button()

    def setup_settings_button(self):
        settings_btn = ttk.Button(self.container, text="⚙️ Settings", command=self.show_settings)
        settings_btn.pack(side=tk.TOP, pady=5)

    def setup_local_tab(self):
        # Repository selection
        repo_frame = ttk.Frame(self.local_tab)
        repo_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side=tk.LEFT)
        self.local_repo_var = tk.StringVar()
        self.local_repo_dropdown = ttk.Combobox(repo_frame, textvariable=self.local_repo_var)
        self.local_repo_dropdown.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Branch selection
        branches_frame = ttk.Frame(self.local_tab)
        branches_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(branches_frame, text="Base Branch:").pack(side=tk.LEFT)
        self.base_branch_var = tk.StringVar()
        self.base_branch_dropdown = ttk.Combobox(branches_frame, textvariable=self.base_branch_var)
        self.base_branch_dropdown.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(branches_frame, text="Compare Branch:").pack(side=tk.LEFT)
        self.compare_branch_var = tk.StringVar()
        self.compare_branch_dropdown = ttk.Combobox(branches_frame, textvariable=self.compare_branch_var)
        self.compare_branch_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Compare button
        ttk.Button(self.local_tab, text="Compare Branches", 
                  command=lambda: self.compare_branches(False)).pack(pady=10)
        
        # Results
        self.local_results = tk.Text(self.local_tab, height=20, wrap=tk.WORD)
        self.local_results.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def setup_origin_tab(self):
        # Repository selection
        repo_frame = ttk.Frame(self.origin_tab)
        repo_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side=tk.LEFT)
        self.origin_repo_var = tk.StringVar()
        self.origin_repo_dropdown = ttk.Combobox(repo_frame, textvariable=self.origin_repo_var)
        self.origin_repo_dropdown.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Compare button
        ttk.Button(self.origin_tab, text="Compare with Origin", 
                  command=lambda: self.compare_branches(True)).pack(pady=10)
        
        # Results
        self.origin_results = tk.Text(self.origin_tab, height=20, wrap=tk.WORD)
        self.origin_results.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def load_token(self):
        try:
            if os.path.exists('github_token.json'):
                with open('github_token.json', 'r') as f:
                    data = json.load(f)
                    token = data.get('token')
                    if token:
                        self.gh = Github(token)
                        self.update_repo_lists()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load GitHub token: {str(e)}")

    def save_token(self, token):
        try:
            with open('github_token.json', 'w') as f:
                json.dump({'token': token}, f)
            self.gh = Github(token)
            self.update_repo_lists()
            messagebox.showinfo("Success", "GitHub token saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save GitHub token: {str(e)}")

    def show_settings(self):
        settings = tk.Toplevel(self.root)
        settings.title("Settings")
        settings.geometry("400x150")
        
        ttk.Label(settings, text="GitHub Token:").pack(pady=5)
        token_entry = ttk.Entry(settings, width=50)
        token_entry.pack(pady=5)
        
        if os.path.exists('github_token.json'):
            try:
                with open('github_token.json', 'r') as f:
                    data = json.load(f)
                    token_entry.insert(0, data.get('token', ''))
            except:
                pass
        
        ttk.Button(settings, text="Save", 
                  command=lambda: self.save_token(token_entry.get())).pack(pady=10)

    def update_repo_lists(self):
        if not self.gh:
            return
            
        try:
            repos = [repo.full_name for repo in self.gh.get_user().get_repos()]
            self.local_repo_dropdown['values'] = repos
            self.origin_repo_dropdown['values'] = repos
            
            if repos:
                self.local_repo_var.set(repos[0])
                self.origin_repo_var.set(repos[0])
                self.update_branch_lists()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch repositories: {str(e)}")

    def update_branch_lists(self):
        if not self.gh or not self.local_repo_var.get():
            return
            
        try:
            repo = self.gh.get_repo(self.local_repo_var.get())
            branches = [branch.name for branch in repo.get_branches()]
            
            self.base_branch_dropdown['values'] = branches
            self.compare_branch_dropdown['values'] = branches
            
            if branches:
                self.base_branch_var.set(branches[0])
                self.compare_branch_var.set(branches[0])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch branches: {str(e)}")

    def compare_branches(self, compare_with_origin=False):
        if not self.gh:
            messagebox.showerror("Error", "Please set your GitHub token in Settings first!")
            return
            
        try:
            if compare_with_origin:
                repo_name = self.origin_repo_var.get()
                repo = self.gh.get_repo(repo_name)
                
                # Get parent/origin repository
                if repo.parent:
                    origin_repo = repo.parent
                    comparison = repo.compare(f"{origin_repo.owner.login}:main", "main")
                    
                    # Clear previous results
                    self.origin_results.delete(1.0, tk.END)
                    
                    # Show repository info
                    self.origin_results.insert(tk.END, f"Comparing with origin repository: {origin_repo.full_name}\n\n")
                    
                    # Show commit stats
                    stats = f"Stats:\n"
                    stats += f"Commits ahead: {len(list(comparison.ahead_commits))}\n"
                    stats += f"Commits behind: {len(list(comparison.behind_commits))}\n\n"
                    self.origin_results.insert(tk.END, stats)
                    
                    # Show behind commits
                    self.origin_results.insert(tk.END, "Behind Commits:\n")
                    for i, commit in enumerate(comparison.behind_commits, 1):
                        commit_info = f"\n{i}. {commit.commit.message}\n"
                        
                        # Get commit stats
                        try:
                            files_changed = len(list(commit.files))
                            additions = commit.stats.additions
                            deletions = commit.stats.deletions
                            commit_info += f"   {files_changed} changed files with {additions} additions and {deletions} deletions\n"
                        except:
                            commit_info += "   Stats not available\n"
                        
                        # Add buttons frame
                        buttons_frame = ttk.Frame(self.origin_tab)
                        self.origin_results.window_create(tk.END, window=buttons_frame)
                        
                        # View Diff button
                        ttk.Button(buttons_frame, text="View Diff", 
                                 command=lambda c=commit: webbrowser.open(c.html_url)).pack(side=tk.LEFT, padx=5)
                        
                        # Merge button
                        ttk.Button(buttons_frame, text="Merge", 
                                 command=lambda c=commit: self.merge_commit(c, repo_name)).pack(side=tk.LEFT, padx=5)
                        
                        self.origin_results.insert(tk.END, "\n" + "-"*50 + "\n")
                else:
                    messagebox.showinfo("Info", "This repository has no parent/origin repository.")
            else:
                # Local branch comparison
                repo_name = self.local_repo_var.get()
                repo = self.gh.get_repo(repo_name)
                base = self.base_branch_var.get()
                compare = self.compare_branch_var.get()
                
                comparison = repo.compare(base, compare)
                
                # Clear previous results
                self.local_results.delete(1.0, tk.END)
                
                # Show commit stats
                stats = f"Comparing {base} with {compare}:\n\n"
                stats += f"Total commits: {len(list(comparison.commits))}\n"
                stats += f"Changed files: {comparison.total_commits}\n"
                stats += f"Additions: {comparison.ahead_by}\n"
                stats += f"Deletions: {comparison.behind_by}\n\n"
                self.local_results.insert(tk.END, stats)
                
                # Show commits
                self.local_results.insert(tk.END, "Commits:\n")
                for i, commit in enumerate(comparison.commits, 1):
                    commit_info = f"\n{i}. {commit.commit.message}\n"
                    self.local_results.insert(tk.END, commit_info)
                    
                    # Add buttons frame
                    buttons_frame = ttk.Frame(self.local_tab)
                    self.local_results.window_create(tk.END, window=buttons_frame)
                    
                    # View Diff button
                    ttk.Button(buttons_frame, text="View Diff", 
                             command=lambda c=commit: webbrowser.open(c.html_url)).pack(side=tk.LEFT, padx=5)
                    
                    self.local_results.insert(tk.END, "\n" + "-"*50 + "\n")
                
        except Exception as e:
            messagebox.showerror("Error", f"Comparison failed: {str(e)}")

    def merge_commit(self, commit, repo_name):
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp()
            
            try:
                # Clone repository
                repo = git.Repo.clone_from(f"https://github.com/{repo_name}.git", temp_dir)
                
                # Create and checkout new branch
                new_branch = f"merge-{commit.sha[:7]}"
                current = repo.create_head(new_branch)
                current.checkout()
                
                # Cherry pick the commit
                repo.git.cherry_pick(commit.sha)
                
                # Push changes
                repo.git.push('origin', new_branch)
                
                # Create pull request
                gh_repo = self.gh.get_repo(repo_name)
                pr = gh_repo.create_pull(
                    title=f"Merge commit {commit.sha[:7]}",
                    body=f"Cherry-picked commit from origin:\n\n{commit.commit.message}",
                    head=new_branch,
                    base="main"
                )
                
                messagebox.showinfo("Success", f"Created PR #{pr.number} for the merge!")
                webbrowser.open(pr.html_url)
                
            finally:
                # Cleanup
                shutil.rmtree(temp_dir)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to merge commit: {str(e)}")

    def run(self):
        # Bind repository selection to branch update
        self.local_repo_dropdown.bind('<<ComboboxSelected>>', lambda e: self.update_branch_lists())
        
        # Start the application
        self.root.mainloop()

if __name__ == "__main__":
    app = GitHubCompare()
    app.run()
