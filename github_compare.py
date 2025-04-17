import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import tempfile
import webbrowser
from github import Github, GithubException
import subprocess

class GitHubCompare:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Branch Comparison Tool")
        
        # Initialize GitHub API token from settings if exists
        self.token = self.load_token()
        self.g = None if not self.token else Github(self.token)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(pady=10, expand=True)
        
        # Create tabs
        self.local_tab = ttk.Frame(self.notebook)
        self.origin_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.local_tab, text='Local Compare')
        self.notebook.add(self.origin_tab, text='Origin Compare')
        
        # Settings button
        self.settings_button = ttk.Button(self.root, text="⚙️ Settings", command=self.show_settings)
        self.settings_button.pack(pady=5)
        
        # Setup local compare tab
        self.setup_local_tab()
        
        # Setup origin compare tab
        self.setup_origin_tab()
        
        # Initialize workspace
        self.workspace = tempfile.mkdtemp()
        
    def load_token(self):
        try:
            with open('github_token.json', 'r') as f:
                data = json.load(f)
                return data.get('token', '')
        except:
            return ''
            
    def save_token(self, token):
        with open('github_token.json', 'w') as f:
            json.dump({'token': token}, f)
            
    def show_settings(self):
        settings = tk.Toplevel(self.root)
        settings.title("Settings")
        settings.geometry("400x200")
        
        ttk.Label(settings, text="GitHub API Token:").pack(pady=10)
        token_entry = ttk.Entry(settings, width=40)
        token_entry.insert(0, self.token)
        token_entry.pack(pady=5)
        
        def save_settings():
            new_token = token_entry.get().strip()
            if new_token != self.token:
                self.token = new_token
                self.save_token(new_token)
                self.g = Github(new_token)
                messagebox.showinfo("Success", "Settings saved successfully!")
                # Refresh repository lists
                self.refresh_repo_lists()
            settings.destroy()
            
        ttk.Button(settings, text="Save", command=save_settings).pack(pady=20)
        
    def refresh_repo_lists(self):
        """Refresh all repository dropdown lists"""
        if not self.g:
            messagebox.showerror("Error", "Please set your GitHub token in settings first!")
            return
            
        try:
            # Get user's repositories
            repos = list(self.g.get_user().get_repos())
            repo_names = [repo.full_name for repo in repos]
            
            # Update local tab dropdowns
            self.local_repo_var.set('')
            self.local_repo_dropdown['values'] = repo_names
            
            # Update origin tab dropdowns
            self.origin_repo_var.set('')
            self.origin_repo_dropdown['values'] = repo_names
            
        except GithubException as e:
            messagebox.showerror("Error", f"Failed to fetch repositories: {str(e)}")
            
    def setup_local_tab(self):
        # Repository selection
        ttk.Label(self.local_tab, text="Repository:").pack(pady=5)
        self.local_repo_var = tk.StringVar()
        self.local_repo_dropdown = ttk.Combobox(self.local_tab, textvariable=self.local_repo_var)
        self.local_repo_dropdown.pack(pady=5)
        
        # Branch selections
        ttk.Label(self.local_tab, text="Base Branch:").pack(pady=5)
        self.local_base_var = tk.StringVar()
        self.local_base_dropdown = ttk.Combobox(self.local_tab, textvariable=self.local_base_var)
        self.local_base_dropdown.pack(pady=5)
        
        ttk.Label(self.local_tab, text="Compare Branch:").pack(pady=5)
        self.local_compare_var = tk.StringVar()
        self.local_compare_dropdown = ttk.Combobox(self.local_tab, textvariable=self.local_compare_var)
        self.local_compare_dropdown.pack(pady=5)
        
        # Compare button
        ttk.Button(self.local_tab, text="Compare Branches", 
                  command=lambda: self.compare_branches(False)).pack(pady=20)
        
        # Results area
        self.local_results = tk.Text(self.local_tab, height=10, width=50)
        self.local_results.pack(pady=10, padx=10, expand=True, fill='both')
        
        # Bind repository selection to branch update
        self.local_repo_dropdown.bind('<<ComboboxSelected>>', 
                                    lambda e: self.update_branches(self.local_repo_var.get(),
                                                                 self.local_base_dropdown,
                                                                 self.local_compare_dropdown))
                                                                 
    def setup_origin_tab(self):
        # Repository selection
        ttk.Label(self.origin_tab, text="Your Repository:").pack(pady=5)
        self.origin_repo_var = tk.StringVar()
        self.origin_repo_dropdown = ttk.Combobox(self.origin_tab, textvariable=self.origin_repo_var)
        self.origin_repo_dropdown.pack(pady=5)
        
        # Branch selections
        ttk.Label(self.origin_tab, text="Your Branch:").pack(pady=5)
        self.origin_base_var = tk.StringVar()
        self.origin_base_dropdown = ttk.Combobox(self.origin_tab, textvariable=self.origin_base_var)
        self.origin_base_dropdown.pack(pady=5)
        
        # Compare button
        ttk.Button(self.origin_tab, text="Compare with Origin", 
                  command=lambda: self.compare_branches(True)).pack(pady=20)
        
        # Results area
        self.origin_results = tk.Text(self.origin_tab, height=10, width=50)
        self.origin_results.pack(pady=10, padx=10, expand=True, fill='both')
        
        # Bind repository selection to branch update
        self.origin_repo_dropdown.bind('<<ComboboxSelected>>', 
                                     lambda e: self.update_branches(self.origin_repo_var.get(),
                                                                  self.origin_base_dropdown,
                                                                  None,
                                                                  True))
                                                                  
    def update_branches(self, repo_name, base_dropdown, compare_dropdown=None, is_origin=False):
        if not self.g:
            messagebox.showerror("Error", "Please set your GitHub token in settings first!")
            return
            
        try:
            repo = self.g.get_repo(repo_name)
            branches = [branch.name for branch in repo.get_branches()]
            
            base_dropdown['values'] = branches
            if compare_dropdown:
                compare_dropdown['values'] = branches
                
            if is_origin:
                # Get parent repository branches if it exists
                try:
                    parent = repo.parent
                    if parent:
                        parent_branches = [branch.name for branch in parent.get_branches()]
                        self.origin_parent_branches = parent_branches
                except:
                    self.origin_parent_branches = []
                    
        except GithubException as e:
            messagebox.showerror("Error", f"Failed to fetch branches: {str(e)}")
            
    def compare_branches(self, is_origin=False):
        if not self.g:
            messagebox.showerror("Error", "Please set your GitHub token in settings first!")
            return
            
        try:
            if is_origin:
                repo_name = self.origin_repo_var.get()
                base_branch = self.origin_base_var.get()
                repo = self.g.get_repo(repo_name)
                
                # Get parent repository
                parent = repo.parent
                if not parent:
                    messagebox.showerror("Error", "This repository has no parent/origin repository!")
                    return
                    
                # Compare with parent's default branch
                compare_branch = parent.default_branch
                comparison = repo.compare(base_branch, f"{parent.owner.login}:{compare_branch}")
                
                # Clear previous results
                self.origin_results.delete(1.0, tk.END)
                
                # Show comparison stats
                stats = f"Comparing with origin repository {parent.full_name}\n"
                stats += f"Commits behind: {len(comparison.behind_commits)}\n"
                stats += f"Commits ahead: {len(comparison.ahead_commits)}\n\n"
                self.origin_results.insert(tk.END, stats)
                
                # Show behind commits with buttons
                if comparison.behind_commits:
                    self.origin_results.insert(tk.END, "Commits you can merge from origin:\n\n")
                    for commit in comparison.behind_commits:
                        # Create frame for commit info and buttons
                        commit_frame = ttk.Frame(self.origin_results)
                        
                        # Commit message and stats
                        info_text = f"{commit.commit.message}\n"
                        info_text += f"Changed files: {len(list(commit.files))} with "
                        info_text += f"{commit.stats.additions} additions and {commit.stats.deletions} deletions"
                        
                        ttk.Label(commit_frame, text=info_text, wraplength=400).pack(side=tk.LEFT, padx=5)
                        
                        # View button
                        view_btn = ttk.Button(commit_frame, text="View Diff",
                                            command=lambda c=commit: webbrowser.open(c.html_url))
                        view_btn.pack(side=tk.LEFT, padx=5)
                        
                        # Merge button
                        merge_btn = ttk.Button(commit_frame, text="Merge",
                                             command=lambda c=commit: self.merge_commit(repo_name, c.sha))
                        merge_btn.pack(side=tk.LEFT, padx=5)
                        
                        # Add frame to text widget
                        self.origin_results.window_create(tk.END, window=commit_frame)
                        self.origin_results.insert(tk.END, "\n\n")
                
            else:
                repo_name = self.local_repo_var.get()
                base_branch = self.local_base_var.get()
                compare_branch = self.local_compare_var.get()
                
                if not all([repo_name, base_branch, compare_branch]):
                    messagebox.showerror("Error", "Please select repository and branches!")
                    return
                    
                repo = self.g.get_repo(repo_name)
                comparison = repo.compare(base_branch, compare_branch)
                
                # Clear previous results
                self.local_results.delete(1.0, tk.END)
                
                # Show comparison stats
                stats = f"Comparing {base_branch}...{compare_branch}\n"
                stats += f"Total commits: {len(comparison.commits)}\n"
                stats += f"Changed files: {len(comparison.files)}\n"
                stats += f"Additions: {comparison.total_additions}\n"
                stats += f"Deletions: {comparison.total_deletions}\n\n"
                self.local_results.insert(tk.END, stats)
                
                # Show commits with buttons
                if comparison.commits:
                    self.local_results.insert(tk.END, "Commits:\n\n")
                    for commit in comparison.commits:
                        # Create frame for commit info and buttons
                        commit_frame = ttk.Frame(self.local_results)
                        
                        # Commit message and stats
                        info_text = f"{commit.commit.message}\n"
                        info_text += f"Changed files: {len(list(commit.files))} with "
                        info_text += f"{commit.stats.additions} additions and {commit.stats.deletions} deletions"
                        
                        ttk.Label(commit_frame, text=info_text, wraplength=400).pack(side=tk.LEFT, padx=5)
                        
                        # View button
                        view_btn = ttk.Button(commit_frame, text="View Diff",
                                            command=lambda c=commit: webbrowser.open(c.html_url))
                        view_btn.pack(side=tk.LEFT, padx=5)
                        
                        self.local_results.window_create(tk.END, window=commit_frame)
                        self.local_results.insert(tk.END, "\n\n")
                        
        except GithubException as e:
            messagebox.showerror("Error", f"Comparison failed: {str(e)}")
            
    def merge_commit(self, repo_name, commit_sha):
        """Merge a specific commit by cloning the repo and cherry-picking"""
        try:
            repo = self.g.get_repo(repo_name)
            
            # Create a new directory for this operation
            temp_dir = tempfile.mkdtemp()
            
            # Clone the repository
            clone_url = f"https://{self.token}@github.com/{repo_name}.git"
            subprocess.run(['git', 'clone', clone_url, temp_dir], check=True)
            
            # Change to repo directory
            os.chdir(temp_dir)
            
            # Create a new branch for the cherry-pick
            branch_name = f"merge-{commit_sha[:7]}"
            subprocess.run(['git', 'checkout', '-b', branch_name], check=True)
            
            # Cherry-pick the commit
            subprocess.run(['git', 'cherry-pick', commit_sha], check=True)
            
            # Push the changes
            subprocess.run(['git', 'push', 'origin', branch_name], check=True)
            
            # Create pull request
            pr = repo.create_pull(
                title=f"Merge commit {commit_sha[:7]}",
                body=f"Cherry-picked commit {commit_sha} from parent repository",
                head=branch_name,
                base=repo.default_branch
            )
            
            messagebox.showinfo("Success", f"Created PR #{pr.number} for the merge!")
            webbrowser.open(pr.html_url)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to merge commit: {str(e)}")
            
    def run(self):
        # Initial repository list load
        if self.g:
            self.refresh_repo_lists()
        self.root.mainloop()

if __name__ == "__main__":
    app = GitHubCompare()
    app.run()
