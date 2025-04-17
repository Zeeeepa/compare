import os
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
from github import Github
import tempfile
import webbrowser

class GitHubComparisonTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Repository Comparison Tool")
        self.root.geometry("800x600")
        
        # Initialize GitHub client
        self.github_token = os.getenv("GITHUB_TOKEN")
        if not self.github_token:
            self.show_settings()
        else:
            self.github = Github(self.github_token)
            
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Create tabs
        self.local_tab = ttk.Frame(self.notebook)
        self.origin_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.local_tab, text='Local Compare')
        self.notebook.add(self.origin_tab, text='Origin Compare')
        
        self.setup_local_tab()
        self.setup_origin_tab()
        
        # Create workspace directory
        self.workspace = tempfile.mkdtemp()
        
    def setup_local_tab(self):
        # Repository selection
        repo_frame = ttk.Frame(self.local_tab)
        repo_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side='left')
        self.repo_var = tk.StringVar()
        self.repo_combo = ttk.Combobox(repo_frame, textvariable=self.repo_var)
        self.repo_combo.pack(side='left', fill='x', expand=True, padx=5)
        self.repo_combo.bind('<<ComboboxSelected>>', self.update_branches)
        
        # Branch selection
        branches_frame = ttk.Frame(self.local_tab)
        branches_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(branches_frame, text="Base Branch:").pack(side='left')
        self.base_branch_var = tk.StringVar()
        self.base_branch_combo = ttk.Combobox(branches_frame, textvariable=self.base_branch_var)
        self.base_branch_combo.pack(side='left', fill='x', expand=True, padx=5)
        
        ttk.Label(branches_frame, text="Compare Branch:").pack(side='left')
        self.compare_branch_var = tk.StringVar()
        self.compare_branch_combo = ttk.Combobox(branches_frame, textvariable=self.compare_branch_var)
        self.compare_branch_combo.pack(side='left', fill='x', expand=True, padx=5)
        
        # Compare button
        ttk.Button(self.local_tab, text="Compare Branches", command=self.compare_local_branches).pack(pady=10)
        
        # Results area
        self.local_results = tk.Text(self.local_tab, height=20)
        self.local_results.pack(fill='both', expand=True, padx=5, pady=5)
        
    def setup_origin_tab(self):
        # Repository selection
        repo_frame = ttk.Frame(self.origin_tab)
        repo_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side='left')
        self.origin_repo_var = tk.StringVar()
        self.origin_repo_combo = ttk.Combobox(repo_frame, textvariable=self.origin_repo_var)
        self.origin_repo_combo.pack(side='left', fill='x', expand=True, padx=5)
        self.origin_repo_combo.bind('<<ComboboxSelected>>', self.update_origin_branches)
        
        # Branch selection
        branches_frame = ttk.Frame(self.origin_tab)
        branches_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(branches_frame, text="Base Branch:").pack(side='left')
        self.origin_base_branch_var = tk.StringVar()
        self.origin_base_branch_combo = ttk.Combobox(branches_frame, textvariable=self.origin_base_branch_var)
        self.origin_base_branch_combo.pack(side='left', fill='x', expand=True, padx=5)
        
        ttk.Label(branches_frame, text="Compare Branch:").pack(side='left')
        self.origin_compare_branch_var = tk.StringVar()
        self.origin_compare_branch_combo = ttk.Combobox(branches_frame, textvariable=self.origin_compare_branch_var)
        self.origin_compare_branch_combo.pack(side='left', fill='x', expand=True, padx=5)
        
        # Compare button
        ttk.Button(self.origin_tab, text="Compare with Origin", command=self.compare_with_origin).pack(pady=10)
        
        # Results area
        self.origin_results = tk.Text(self.origin_tab, height=20)
        self.origin_results.pack(fill='both', expand=True, padx=5, pady=5)
        
    def show_settings(self):
        settings = tk.Toplevel(self.root)
        settings.title("Settings")
        settings.geometry("400x150")
        
        ttk.Label(settings, text="GitHub Token:").pack(pady=5)
        token_entry = ttk.Entry(settings, width=50)
        token_entry.pack(pady=5)
        
        def save_token():
            token = token_entry.get()
            if token:
                os.environ["GITHUB_TOKEN"] = token
                self.github_token = token
                self.github = Github(token)
                self.update_repos()
                settings.destroy()
                messagebox.showinfo("Success", "GitHub token saved successfully!")
            else:
                messagebox.showerror("Error", "Please enter a valid GitHub token")
                
        ttk.Button(settings, text="Save", command=save_token).pack(pady=10)
        
    def update_repos(self):
        try:
            repos = [repo.full_name for repo in self.github.get_user().get_repos()]
            self.repo_combo['values'] = repos
            self.origin_repo_combo['values'] = repos
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch repositories: {str(e)}")
            
    def update_branches(self, event=None):
        try:
            repo = self.github.get_repo(self.repo_var.get())
            branches = [branch.name for branch in repo.get_branches()]
            self.base_branch_combo['values'] = branches
            self.compare_branch_combo['values'] = branches
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch branches: {str(e)}")
            
    def update_origin_branches(self, event=None):
        try:
            repo = self.github.get_repo(self.origin_repo_var.get())
            branches = [branch.name for branch in repo.get_branches()]
            self.origin_base_branch_combo['values'] = branches
            self.origin_compare_branch_combo['values'] = branches
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch branches: {str(e)}")
            
    def clone_repo(self, repo_name, branch_name):
        repo_path = os.path.join(self.workspace, repo_name.split('/')[-1])
        if not os.path.exists(repo_path):
            subprocess.run(['git', 'clone', f'https://{self.github_token}@github.com/{repo_name}.git', repo_path], check=True)
        os.chdir(repo_path)
        subprocess.run(['git', 'fetch', 'origin'], check=True)
        subprocess.run(['git', 'checkout', branch_name], check=True)
        subprocess.run(['git', 'pull', 'origin', branch_name], check=True)
        return repo_path
        
    def compare_local_branches(self):
        try:
            repo_name = self.repo_var.get()
            base_branch = self.base_branch_var.get()
            compare_branch = self.compare_branch_var.get()
            
            if not all([repo_name, base_branch, compare_branch]):
                messagebox.showerror("Error", "Please select repository and branches")
                return
                
            # Clone repository and get commits
            repo_path = self.clone_repo(repo_name, base_branch)
            
            # Get commit differences
            result = subprocess.run(
                ['git', 'log', '--pretty=format:%H|%s|%an|%ad', f'{base_branch}..{compare_branch}'],
                capture_output=True, text=True
            )
            
            self.local_results.delete(1.0, tk.END)
            commits = result.stdout.strip().split('\n')
            
            for commit in commits:
                if not commit:
                    continue
                    
                sha, message, author, date = commit.split('|')
                
                # Get commit stats
                stats = subprocess.run(
                    ['git', 'show', '--stat', sha],
                    capture_output=True, text=True
                )
                
                commit_frame = ttk.Frame(self.local_results)
                self.local_results.window_create(tk.END, window=commit_frame)
                
                # Commit info
                info_text = f"{message}\nAuthor: {author}\nDate: {date}\n{stats.stdout.split('--')[-1].strip()}\n"
                ttk.Label(commit_frame, text=info_text).pack(side='left')
                
                # View button
                view_btn = ttk.Button(
                    commit_frame, text="View Diff",
                    command=lambda s=sha: webbrowser.open(f"https://github.com/{repo_name}/commit/{s}")
                )
                view_btn.pack(side='left', padx=5)
                
                # Apply button
                apply_btn = ttk.Button(
                    commit_frame, text="Apply",
                    command=lambda s=sha: self.apply_commit(s, repo_path)
                )
                apply_btn.pack(side='left')
                
                self.local_results.insert(tk.END, '\n' + '-'*80 + '\n')
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to compare branches: {str(e)}")
            
    def compare_with_origin(self):
        try:
            repo_name = self.origin_repo_var.get()
            base_branch = self.origin_base_branch_var.get()
            compare_branch = self.origin_compare_branch_var.get()
            
            if not all([repo_name, base_branch, compare_branch]):
                messagebox.showerror("Error", "Please select repository and branches")
                return
                
            repo = self.github.get_repo(repo_name)
            comparison = repo.compare(base_branch, compare_branch)
            
            self.origin_results.delete(1.0, tk.END)
            self.origin_results.insert(tk.END, f"Commits behind: {comparison.behind_by}\n")
            self.origin_results.insert(tk.END, f"Commits ahead: {comparison.ahead_by}\n\n")
            
            for commit in comparison.commits:
                commit_frame = ttk.Frame(self.origin_results)
                self.origin_results.window_create(tk.END, window=commit_frame)
                
                # Get commit stats
                stats = commit.stats
                info_text = f"{commit.commit.message}\n{len(commit.files)} changed files with {stats.additions} additions and {stats.deletions} deletions"
                ttk.Label(commit_frame, text=info_text).pack(side='left')
                
                # View button
                view_btn = ttk.Button(
                    commit_frame, text="View Diff",
                    command=lambda c=commit: webbrowser.open(c.html_url)
                )
                view_btn.pack(side='left', padx=5)
                
                # Apply button
                apply_btn = ttk.Button(
                    commit_frame, text="Apply",
                    command=lambda s=commit.sha: self.apply_commit(s, self.clone_repo(repo_name, base_branch))
                )
                apply_btn.pack(side='left')
                
                self.origin_results.insert(tk.END, '\n' + '-'*80 + '\n')
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to compare with origin: {str(e)}")
            
    def apply_commit(self, commit_sha, repo_path):
        try:
            os.chdir(repo_path)
            subprocess.run(['git', 'cherry-pick', commit_sha], check=True)
            messagebox.showinfo("Success", "Commit applied successfully!")
            
            # Push changes
            if messagebox.askyesno("Push Changes", "Would you like to push the changes to remote?"):
                subprocess.run(['git', 'push'], check=True)
                messagebox.showinfo("Success", "Changes pushed successfully!")
                
        except subprocess.CalledProcessError as e:
            subprocess.run(['git', 'cherry-pick', '--abort'], check=True)
            messagebox.showerror("Error", f"Failed to apply commit: {str(e)}")
            
    def run(self):
        if self.github_token:
            self.update_repos()
        self.root.mainloop()

if __name__ == "__main__":
    app = GitHubComparisonTool()
    app.run()
