import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import subprocess
from github import Github, GithubException
from urllib.parse import urlparse

class GitHubCompare:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Branch Comparison Tool")
        self.root.geometry("800x600")
        
        # Initialize GitHub API
        self.gh = None
        self.load_token()
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Create tabs
        self.local_tab = ttk.Frame(self.notebook)
        self.origin_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.local_tab, text='Local Branch Compare')
        self.notebook.add(self.origin_tab, text='Origin Compare')
        
        # Setup UI for both tabs
        self.setup_local_tab()
        self.setup_origin_tab()
        
        # Add settings button
        self.settings_button = ttk.Button(
            self.root,
            text="⚙️ Settings",
            command=self.show_settings
        )
        self.settings_button.pack(pady=5)

    def load_token(self):
        try:
            if os.path.exists('github_token.json'):
                with open('github_token.json', 'r') as f:
                    data = json.load(f)
                    token = data.get('token')
                    if token:
                        self.gh = Github(token)
                        return
        except Exception:
            pass
        self.gh = None

    def save_token(self, token):
        try:
            with open('github_token.json', 'w') as f:
                json.dump({'token': token}, f)
            self.gh = Github(token)
            messagebox.showinfo("Success", "GitHub token saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save token: {str(e)}")

    def show_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x200")
        
        ttk.Label(settings_window, text="GitHub Token:").pack(pady=10)
        token_entry = ttk.Entry(settings_window, width=50)
        token_entry.pack(pady=5)
        
        if os.path.exists('github_token.json'):
            try:
                with open('github_token.json', 'r') as f:
                    data = json.load(f)
                    token_entry.insert(0, data.get('token', ''))
            except Exception:
                pass
        
        ttk.Button(
            settings_window,
            text="Save Token",
            command=lambda: self.save_token(token_entry.get())
        ).pack(pady=10)

    def setup_local_tab(self):
        # Repository selection
        repo_frame = ttk.LabelFrame(self.local_tab, text="Repository Selection")
        repo_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side='left', padx=5)
        self.local_repo_var = tk.StringVar()
        self.local_repo_dropdown = ttk.Combobox(
            repo_frame,
            textvariable=self.local_repo_var,
            state='readonly'
        )
        self.local_repo_dropdown.pack(side='left', padx=5, fill='x', expand=True)
        
        # Branch selection
        branch_frame = ttk.LabelFrame(self.local_tab, text="Branch Selection")
        branch_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(branch_frame, text="Base Branch:").pack(side='left', padx=5)
        self.local_base_var = tk.StringVar()
        self.local_base_dropdown = ttk.Combobox(
            branch_frame,
            textvariable=self.local_base_var,
            state='readonly'
        )
        self.local_base_dropdown.pack(side='left', padx=5, fill='x', expand=True)
        
        ttk.Label(branch_frame, text="Compare Branch:").pack(side='left', padx=5)
        self.local_compare_var = tk.StringVar()
        self.local_compare_dropdown = ttk.Combobox(
            branch_frame,
            textvariable=self.local_compare_var,
            state='readonly'
        )
        self.local_compare_dropdown.pack(side='left', padx=5, fill='x', expand=True)
        
        # Compare button
        ttk.Button(
            self.local_tab,
            text="Compare Branches",
            command=lambda: self.compare_branches(False)
        ).pack(pady=10)
        
        # Results
        self.local_results = tk.Text(self.local_tab, height=20)
        self.local_results.pack(fill='both', expand=True, padx=10, pady=5)

    def setup_origin_tab(self):
        # Repository selection
        repo_frame = ttk.LabelFrame(self.origin_tab, text="Repository Selection")
        repo_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(repo_frame, text="Repository:").pack(side='left', padx=5)
        self.origin_repo_var = tk.StringVar()
        self.origin_repo_dropdown = ttk.Combobox(
            repo_frame,
            textvariable=self.origin_repo_var,
            state='readonly'
        )
        self.origin_repo_dropdown.pack(side='left', padx=5, fill='x', expand=True)
        
        # Compare button
        ttk.Button(
            self.origin_tab,
            text="Compare with Origin",
            command=lambda: self.compare_branches(True)
        ).pack(pady=10)
        
        # Results
        self.origin_results = tk.Text(self.origin_tab, height=20)
        self.origin_results.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Bind events
        self.origin_repo_dropdown.bind('<<ComboboxSelected>>', self.on_repo_selected)
        self.local_repo_dropdown.bind('<<ComboboxSelected>>', self.on_repo_selected)

    def refresh_repos(self):
        if not self.gh:
            messagebox.showerror("Error", "Please set your GitHub token in settings first!")
            return
        
        try:
            repos = [repo.full_name for repo in self.gh.get_user().get_repos()]
            self.local_repo_dropdown['values'] = repos
            self.origin_repo_dropdown['values'] = repos
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch repositories: {str(e)}")

    def on_repo_selected(self, event=None):
        if not self.gh:
            return
            
        try:
            # Update branches for local tab
            if event.widget == self.local_repo_dropdown:
                repo = self.gh.get_repo(self.local_repo_var.get())
                branches = [branch.name for branch in repo.get_branches()]
                self.local_base_dropdown['values'] = branches
                self.local_compare_dropdown['values'] = branches
                
                # Set defaults
                default_branch = repo.default_branch
                self.local_base_var.set(default_branch)
                if len(branches) > 1:
                    self.local_compare_var.set([b for b in branches if b != default_branch][0])
                else:
                    self.local_compare_var.set(default_branch)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch branches: {str(e)}")

    def compare_branches(self, compare_origin=False):
        if not self.gh:
            messagebox.showerror("Error", "Please set your GitHub token in settings first!")
            return
            
        try:
            if compare_origin:
                repo_name = self.origin_repo_var.get()
                if not repo_name:
                    messagebox.showerror("Error", "Please select a repository first!")
                    return
                    
                repo = self.gh.get_repo(repo_name)
                parent = repo.parent
                
                if not parent:
                    messagebox.showerror("Error", "Selected repository has no parent/origin repository!")
                    return
                
                # Compare with parent's default branch
                comparison = repo.compare(parent.default_branch, repo.default_branch)
                
                # Clear previous results
                self.origin_results.delete(1.0, tk.END)
                
                # Show comparison stats
                stats = f"Comparing with origin repository: {parent.full_name}\n"
                stats += f"Base branch: {parent.default_branch}\n"
                stats += f"Compare branch: {repo.default_branch}\n\n"
                stats += f"Commits ahead: {comparison.ahead_by}\n"
                stats += f"Commits behind: {comparison.behind_by}\n\n"
                stats += "Behind Commits:\n"
                
                self.origin_results.insert(tk.END, stats)
                
                # Show behind commits with buttons
                for i, commit in enumerate(comparison.commits, 1):
                    commit_info = f"\n{i}. {commit.commit.message}\n"
                    commit_info += f"Files changed: {len(commit.files)} with {commit.stats.additions} additions and {commit.stats.deletions} deletions\n"
                    
                    self.origin_results.insert(tk.END, commit_info)
                    
                    # Add buttons
                    button_frame = ttk.Frame(self.origin_results)
                    
                    view_button = ttk.Button(
                        button_frame,
                        text="View Diff",
                        command=lambda c=commit: self.view_commit_diff(c.html_url)
                    )
                    view_button.pack(side='left', padx=5)
                    
                    merge_button = ttk.Button(
                        button_frame,
                        text="Merge",
                        command=lambda c=commit: self.merge_commit(repo, c.sha)
                    )
                    merge_button.pack(side='left', padx=5)
                    
                    self.origin_results.window_create(tk.END, window=button_frame)
                    self.origin_results.insert(tk.END, "\n")
            else:
                # Local branch comparison
                repo_name = self.local_repo_var.get()
                base_branch = self.local_base_var.get()
                compare_branch = self.local_compare_var.get()
                
                if not all([repo_name, base_branch, compare_branch]):
                    messagebox.showerror("Error", "Please select repository and branches first!")
                    return
                
                repo = self.gh.get_repo(repo_name)
                comparison = repo.compare(base_branch, compare_branch)
                
                # Clear previous results
                self.local_results.delete(1.0, tk.END)
                
                # Show comparison stats
                stats = f"Comparing branches in {repo_name}\n"
                stats += f"Base branch: {base_branch}\n"
                stats += f"Compare branch: {compare_branch}\n\n"
                stats += f"Commits ahead: {comparison.ahead_by}\n"
                stats += f"Commits behind: {comparison.behind_by}\n\n"
                stats += "Commits:\n"
                
                self.local_results.insert(tk.END, stats)
                
                # Show commits with buttons
                for i, commit in enumerate(comparison.commits, 1):
                    commit_info = f"\n{i}. {commit.commit.message}\n"
                    commit_info += f"Files changed: {len(commit.files)} with {commit.stats.additions} additions and {commit.stats.deletions} deletions\n"
                    
                    self.local_results.insert(tk.END, commit_info)
                    
                    # Add buttons
                    button_frame = ttk.Frame(self.local_results)
                    
                    view_button = ttk.Button(
                        button_frame,
                        text="View Diff",
                        command=lambda c=commit: self.view_commit_diff(c.html_url)
                    )
                    view_button.pack(side='left', padx=5)
                    
                    self.local_results.window_create(tk.END, window=button_frame)
                    self.local_results.insert(tk.END, "\n")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to compare branches: {str(e)}")

    def view_commit_diff(self, url):
        import webbrowser
        webbrowser.open(url)

    def merge_commit(self, repo, commit_sha):
        try:
            # Create a temporary directory for git operations
            temp_dir = "temp_repo"
            os.makedirs(temp_dir, exist_ok=True)
            
            # Clone the repository
            clone_url = repo.clone_url
            if self.gh:
                parsed = urlparse(clone_url)
                clone_url = f"https://{self.gh._Github__requester._Requester__authorizationHeader.split(' ')[1]}@{parsed.netloc}{parsed.path}"
            
            subprocess.run(['git', 'clone', clone_url, temp_dir], check=True)
            
            # Setup git config
            subprocess.run(['git', 'config', 'user.name', "GitHub Compare Tool"], cwd=temp_dir, check=True)
            subprocess.run(['git', 'config', 'user.email', "noreply@github.com"], cwd=temp_dir, check=True)
            
            # Cherry-pick the commit
            subprocess.run(['git', 'cherry-pick', commit_sha], cwd=temp_dir, check=True)
            
            # Push changes
            subprocess.run(['git', 'push'], cwd=temp_dir, check=True)
            
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir)
            
            messagebox.showinfo("Success", "Commit merged successfully!")
            
            # Refresh the comparison
            self.compare_branches(True)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to merge commit: {str(e)}")
            # Cleanup on error
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)

    def run(self):
        # Initial repos refresh
        self.refresh_repos()
        # Start the main loop
        self.root.mainloop()

if __name__ == "__main__":
    app = GitHubCompare()
    app.run()
