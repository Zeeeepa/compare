import os
import re
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import tempfile
import shutil
from datetime import datetime
import urllib.parse

class RepoComparisonTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Repository Comparison Tool")
        self.root.geometry("900x700")
        self.root.minsize(900, 700)
        
        # Set style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Variables
        self.repo1_path = tk.StringVar()
        self.repo2_path = tk.StringVar()
        self.repo1_search = tk.StringVar()
        self.repo2_search = tk.StringVar()
        self.max_commits_behind = tk.StringVar(value="100")
        self.comparison_direction = tk.StringVar(value="both")
        self.status_text = tk.StringVar(value="Ready")
        self.repo1_tags = []
        self.repo2_tags = []
        self.repo1_selected_tag = tk.StringVar()
        self.repo2_selected_tag = tk.StringVar()
        
        # Create temp directory for cloning repos
        self.temp_dir = tempfile.mkdtemp()
        
        # Create UI
        self.create_ui()
        
    def create_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Repository 1 frame
        repo1_frame = ttk.LabelFrame(main_frame, text="Repository 1", padding="10")
        repo1_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(repo1_frame, text="Repository Path or URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        repo1_entry = ttk.Entry(repo1_frame, textvariable=self.repo1_path, width=50)
        repo1_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        ttk.Button(repo1_frame, text="Browse", command=lambda: self.browse_repo(self.repo1_path)).grid(row=0, column=2, padx=5, pady=5)
        
        # Repository 2 frame
        repo2_frame = ttk.LabelFrame(main_frame, text="Repository 2", padding="10")
        repo2_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(repo2_frame, text="Repository Path or URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        repo2_entry = ttk.Entry(repo2_frame, textvariable=self.repo2_path, width=50)
        repo2_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        ttk.Button(repo2_frame, text="Browse", command=lambda: self.browse_repo(self.repo2_path)).grid(row=0, column=2, padx=5, pady=5)
        
        # Fetch tags button
        fetch_frame = ttk.Frame(main_frame)
        fetch_frame.pack(fill=tk.X, pady=5)
        ttk.Button(fetch_frame, text="Fetch Tags", command=self.fetch_tags).pack(pady=10)
        
        # Tags selection frame
        tags_frame = ttk.Frame(main_frame)
        tags_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        tags_frame.columnconfigure(0, weight=1)
        tags_frame.columnconfigure(1, weight=1)
        
        # Repository 1 tags
        repo1_tags_frame = ttk.LabelFrame(tags_frame, text="Repository 1 Tags/Branches", padding="10")
        repo1_tags_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=5)
        
        ttk.Label(repo1_tags_frame, text="Search:").pack(anchor=tk.W, pady=5)
        ttk.Entry(repo1_tags_frame, textvariable=self.repo1_search).pack(fill=tk.X, pady=5)
        self.repo1_search.trace_add("write", lambda *args: self.filter_tags(1))
        
        self.repo1_tags_listbox = tk.Listbox(repo1_tags_frame, height=10)
        self.repo1_tags_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        repo1_scrollbar = ttk.Scrollbar(self.repo1_tags_listbox, orient="vertical", command=self.repo1_tags_listbox.yview)
        self.repo1_tags_listbox.configure(yscrollcommand=repo1_scrollbar.set)
        repo1_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Repository 2 tags
        repo2_tags_frame = ttk.LabelFrame(tags_frame, text="Repository 2 Tags/Branches", padding="10")
        repo2_tags_frame.grid(row=0, column=1, sticky=tk.NSEW, padx=5)
        
        ttk.Label(repo2_tags_frame, text="Search:").pack(anchor=tk.W, pady=5)
        ttk.Entry(repo2_tags_frame, textvariable=self.repo2_search).pack(fill=tk.X, pady=5)
        self.repo2_search.trace_add("write", lambda *args: self.filter_tags(2))
        
        self.repo2_tags_listbox = tk.Listbox(repo2_tags_frame, height=10)
        self.repo2_tags_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        repo2_scrollbar = ttk.Scrollbar(self.repo2_tags_listbox, orient="vertical", command=self.repo2_tags_listbox.yview)
        self.repo2_tags_listbox.configure(yscrollcommand=repo2_scrollbar.set)
        repo2_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Filter frame
        filter_frame = ttk.LabelFrame(main_frame, text="Filtering Options", padding="10")
        filter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(filter_frame, text="Max Commits Behind:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(filter_frame, textvariable=self.max_commits_behind, width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Button(filter_frame, text="Apply Filter", command=self.apply_filter).grid(row=0, column=2, padx=5, pady=5)
        
        # Comparison direction
        direction_frame = ttk.LabelFrame(main_frame, text="Comparison Direction", padding="10")
        direction_frame.pack(fill=tk.X, pady=5)
        
        ttk.Radiobutton(direction_frame, text="Repo1 \u2192 Repo2 (files in Repo1 not in Repo2)", 
                        variable=self.comparison_direction, value="1to2").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(direction_frame, text="Repo2 \u2192 Repo1 (files in Repo2 not in Repo1)", 
                        variable=self.comparison_direction, value="2to1").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(direction_frame, text="Both directions (all differences)", 
                        variable=self.comparison_direction, value="both").pack(anchor=tk.W, pady=2)
        
        # Generate button
        generate_frame = ttk.Frame(main_frame)
        generate_frame.pack(fill=tk.X, pady=10)
        ttk.Button(generate_frame, text="Generate Difference", command=self.generate_difference).pack(pady=5)
        
        # Status bar
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Label(status_frame, textvariable=self.status_text).pack(side=tk.LEFT, padx=10)
        
        # Set up tag selection handlers
        self.repo1_tags_listbox.bind('<<ListboxSelect>>', lambda e: self.on_tag_select(1))
        self.repo2_tags_listbox.bind('<<ListboxSelect>>', lambda e: self.on_tag_select(2))
    
    def browse_repo(self, path_var):
        folder_path = filedialog.askdirectory()
        if folder_path:
            path_var.set(folder_path)
    
    def is_url(self, path):
        return path.startswith(('http://', 'https://'))
    
    def get_repo_name(self, repo_path):
        if self.is_url(repo_path):
            # Extract repo name from URL
            parsed_url = urllib.parse.urlparse(repo_path)
            path_parts = parsed_url.path.strip('/').split('/')
            if len(path_parts) >= 2:
                return path_parts[-1].replace('.git', '')
        else:
            # Extract repo name from local path
            return os.path.basename(repo_path)
        return "repo"
    
    def clone_repo(self, repo_path, target_dir):
        if self.is_url(repo_path):
            self.update_status(f"Cloning repository from {repo_path}...")
            try:
                # Use --mirror to get all refs
                subprocess.run(['git', 'clone', '--mirror', repo_path, target_dir], 
                              check=True, capture_output=True, text=True)
                return True
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Error", f"Failed to clone repository: {e.stderr}")
                return False
        else:
            # Local repository, just use it directly
            if not os.path.exists(os.path.join(repo_path, '.git')):
                messagebox.showerror("Error", f"The path '{repo_path}' is not a valid Git repository.")
                return False
            return True
    
    def get_repo_dir(self, repo_path):
        if self.is_url(repo_path):
            repo_name = self.get_repo_name(repo_path)
            repo_dir = os.path.join(self.temp_dir, repo_name)
            if not os.path.exists(repo_dir):
                if not self.clone_repo(repo_path, repo_dir):
                    return None
            return repo_dir
        else:
            # Validate local repository
            if not os.path.exists(repo_path):
                messagebox.showerror("Error", f"The path '{repo_path}' does not exist.")
                return None
            if not os.path.exists(os.path.join(repo_path, '.git')):
                messagebox.showerror("Error", f"The path '{repo_path}' is not a valid Git repository.")
                return None
            return repo_path
    
    def fetch_tags(self):
        threading.Thread(target=self._fetch_tags_thread).start()
    
    def _fetch_tags_thread(self):
        self.update_status("Fetching tags and branches...")
        
        # Repo 1
        repo1_path = self.repo1_path.get().strip()
        if not repo1_path:
            messagebox.showerror("Error", "Please enter Repository 1 path or URL")
            self.update_status("Ready")
            return
        
        repo1_dir = self.get_repo_dir(repo1_path)
        if not repo1_dir:
            self.update_status("Failed to access Repository 1")
            return
        
        # Repo 2
        repo2_path = self.repo2_path.get().strip()
        if not repo2_path:
            messagebox.showerror("Error", "Please enter Repository 2 path or URL")
            self.update_status("Ready")
            return
        
        repo2_dir = self.get_repo_dir(repo2_path)
        if not repo2_dir:
            self.update_status("Failed to access Repository 2")
            return
        
        # Get tags and branches for repo 1
        self.update_status("Fetching tags and branches for Repository 1...")
        self.repo1_tags = self.get_tags_and_branches(repo1_dir)
        
        # Get tags and branches for repo 2
        self.update_status("Fetching tags and branches for Repository 2...")
        self.repo2_tags = self.get_tags_and_branches(repo2_dir)
        
        # Update UI
        self.root.after(0, self.update_tags_ui)
        self.update_status("Tags and branches fetched successfully")
    
    def get_tags_and_branches(self, repo_dir):
        tags_and_branches = []
        
        try:
            # Get tags
            tags_output = subprocess.run(['git', '-C', repo_dir, 'tag'],
                                      check=True, capture_output=True, text=True).stdout.strip()
            if tags_output:
                for tag in tags_output.split('\n'):
                    if tag:
                        commit_count = self.get_commit_difference(repo_dir, tag, 'HEAD')
                        tags_and_branches.append({
                            'name': tag,
                            'type': 'tag',
                            'ahead': commit_count['ahead'],
                            'behind': commit_count['behind']
                        })
            
            # Get branches
            branches_output = subprocess.run(['git', '-C', repo_dir, 'branch', '-a'],
                                         check=True, capture_output=True, text=True).stdout.strip()
            if branches_output:
                for branch in branches_output.split('\n'):
                    branch = branch.strip()
                    if branch.startswith('*'):
                        branch = branch[1:].strip()
                    if branch and not branch.startswith('remotes/'):
                        commit_count = self.get_commit_difference(repo_dir, branch, 'HEAD')
                        tags_and_branches.append({
                            'name': branch,
                            'type': 'branch',
                            'ahead': commit_count['ahead'],
                            'behind': commit_count['behind']
                        })
                    elif branch and branch.startswith('remotes/origin/'):
                        branch_name = branch.replace('remotes/origin/', '')
                        if branch_name != 'HEAD':
                            commit_count = self.get_commit_difference(repo_dir, branch, 'HEAD')
                            tags_and_branches.append({
                                'name': branch_name,
                                'type': 'remote_branch',
                                'ahead': commit_count['ahead'],
                                'behind': commit_count['behind']
                            })
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to get tags and branches: {e.stderr}")
        
        return tags_and_branches
    
    def get_commit_difference(self, repo_dir, ref1, ref2):
        try:
            # Make sure both refs exist
            subprocess.run(['git', '-C', repo_dir, 'rev-parse', ref1],
                          check=True, capture_output=True, text=True)
            subprocess.run(['git', '-C', repo_dir, 'rev-parse', ref2],
                          check=True, capture_output=True, text=True)
            
            # Get ahead count
            ahead_output = subprocess.run(['git', '-C', repo_dir, 'rev-list', '--count', f'{ref2}..{ref1}'],
                                       check=True, capture_output=True, text=True).stdout.strip()
            
            # Get behind count
            behind_output = subprocess.run(['git', '-C', repo_dir, 'rev-list', '--count', f'{ref1}..{ref2}'],
                                        check=True, capture_output=True, text=True).stdout.strip()
            
            return {
                'ahead': int(ahead_output) if ahead_output.isdigit() else 0,
                'behind': int(behind_output) if behind_output.isdigit() else 0
            }
        except subprocess.CalledProcessError:
            return {'ahead': 0, 'behind': 0}
    
    def update_tags_ui(self):
        # Clear listboxes
        self.repo1_tags_listbox.delete(0, tk.END)
        self.repo2_tags_listbox.delete(0, tk.END)
        
        # Apply filter
        max_behind = int(self.max_commits_behind.get()) if self.max_commits_behind.get().isdigit() else 0
        
        # Filter and populate repo1 tags
        filtered_tags1 = self.filter_tags_by_search(self.repo1_tags, self.repo1_search.get())
        filtered_tags1 = [tag for tag in filtered_tags1 if tag['behind'] <= max_behind]
        for tag in filtered_tags1:
            display_name = f"{tag['name']} (+{tag['ahead']}/-{tag['behind']})"
            self.repo1_tags_listbox.insert(tk.END, display_name)
        
        # Filter and populate repo2 tags
        filtered_tags2 = self.filter_tags_by_search(self.repo2_tags, self.repo2_search.get())
        filtered_tags2 = [tag for tag in filtered_tags2 if tag['behind'] <= max_behind]
        for tag in filtered_tags2:
            display_name = f"{tag['name']} (+{tag['ahead']}/-{tag['behind']})"
            self.repo2_tags_listbox.insert(tk.END, display_name)
    
    def filter_tags_by_search(self, tags, search_text):
        if not search_text:
            return tags
        search_text = search_text.lower()
        return [tag for tag in tags if search_text in tag['name'].lower()]
    
    def filter_tags(self, repo_num):
        self.update_tags_ui()
    
    def apply_filter(self):
        self.update_tags_ui()
    
    def on_tag_select(self, repo_num):
        if repo_num == 1:
            selected_indices = self.repo1_tags_listbox.curselection()
            if selected_indices:
                selected_index = selected_indices[0]
                selected_tag = self.repo1_tags_listbox.get(selected_index)
                # Extract tag name from display string
                tag_name = selected_tag.split(" (+")[0]
                self.repo1_selected_tag.set(tag_name)
        else:
            selected_indices = self.repo2_tags_listbox.curselection()
            if selected_indices:
                selected_index = selected_indices[0]
                selected_tag = self.repo2_tags_listbox.get(selected_index)
                # Extract tag name from display string
                tag_name = selected_tag.split(" (+")[0]
                self.repo2_selected_tag.set(tag_name)
    
    def generate_difference(self):
        threading.Thread(target=self._generate_difference_thread).start()
    
    def _generate_difference_thread(self):
        self.update_status("Generating difference...")
        
        # Check if tags are selected
        if not self.repo1_selected_tag.get():
            messagebox.showerror("Error", "Please select a tag/branch for Repository 1")
            self.update_status("Ready")
            return
        
        if not self.repo2_selected_tag.get():
            messagebox.showerror("Error", "Please select a tag/branch for Repository 2")
            self.update_status("Ready")
            return
        
        # Get repo directories
        repo1_dir = self.get_repo_dir(self.repo1_path.get().strip())
        if not repo1_dir:
            self.update_status("Failed to access Repository 1")
            return
        
        repo2_dir = self.get_repo_dir(self.repo2_path.get().strip())
        if not repo2_dir:
            self.update_status("Failed to access Repository 2")
            return
        
        # Create output directory on desktop
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(desktop_path, f"repo_diff_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Create subdirectories based on comparison direction
        if self.comparison_direction.get() in ["1to2", "both"]:
            os.makedirs(os.path.join(output_dir, "repo1_unique"), exist_ok=True)
        
        if self.comparison_direction.get() in ["2to1", "both"]:
            os.makedirs(os.path.join(output_dir, "repo2_unique"), exist_ok=True)
        
        # Create temporary working directories
        temp_repo1 = os.path.join(self.temp_dir, "temp_repo1")
        temp_repo2 = os.path.join(self.temp_dir, "temp_repo2")
        
        # Clean up any existing temp directories
        if os.path.exists(temp_repo1):
            shutil.rmtree(temp_repo1, ignore_errors=True)
        if os.path.exists(temp_repo2):
            shutil.rmtree(temp_repo2, ignore_errors=True)
            
        os.makedirs(temp_repo1, exist_ok=True)
        os.makedirs(temp_repo2, exist_ok=True)
        
        # Clone repositories to temporary directories with specific tags/branches
        self.update_status("Preparing repositories...")
        
        try:
            # For URL repositories, we need to clone them
            if self.is_url(self.repo1_path.get().strip()):
                # Clone repo1 with selected tag/branch
                subprocess.run(['git', 'clone', self.repo1_path.get().strip(), temp_repo1], 
                              check=True, capture_output=True, text=True)
                subprocess.run(['git', '-C', temp_repo1, 'checkout', self.repo1_selected_tag.get()], 
                              check=True, capture_output=True, text=True)
            else:
                # For local repositories, create a copy
                self.copy_git_repo(repo1_dir, temp_repo1)
                subprocess.run(['git', '-C', temp_repo1, 'checkout', self.repo1_selected_tag.get()], 
                              check=True, capture_output=True, text=True)
            
            # Same for repo2
            if self.is_url(self.repo2_path.get().strip()):
                # Clone repo2 with selected tag/branch
                subprocess.run(['git', 'clone', self.repo2_path.get().strip(), temp_repo2], 
                              check=True, capture_output=True, text=True)
                subprocess.run(['git', '-C', temp_repo2, 'checkout', self.repo2_selected_tag.get()], 
                              check=True, capture_output=True, text=True)
            else:
                # For local repositories, create a copy
                self.copy_git_repo(repo2_dir, temp_repo2)
                subprocess.run(['git', '-C', temp_repo2, 'checkout', self.repo2_selected_tag.get()], 
                              check=True, capture_output=True, text=True)
                
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to prepare repositories: {e.stderr}")
            self.update_status("Failed to generate difference")
            return
        
        # Compare repositories
        self.update_status("Comparing repositories...")
        
        # Files in repo1 but not in repo2
        if self.comparison_direction.get() in ["1to2", "both"]:
            self.update_status("Finding files in Repository 1 not in Repository 2...")
            self.find_unique_files(temp_repo1, temp_repo2, os.path.join(output_dir, "repo1_unique"))
        
        # Files in repo2 but not in repo1
        if self.comparison_direction.get() in ["2to1", "both"]:
            self.update_status("Finding files in Repository 2 not in Repository 1...")
            self.find_unique_files(temp_repo2, temp_repo1, os.path.join(output_dir, "repo2_unique"))
        
        # Clean up temporary directories
        self.update_status("Cleaning up...")
        shutil.rmtree(temp_repo1, ignore_errors=True)
        shutil.rmtree(temp_repo2, ignore_errors=True)
        
        # Open output directory
        self.update_status("Difference generated successfully")
        os.startfile(output_dir)
    
    def copy_git_repo(self, source_repo, target_dir):
        """Create a copy of a git repository for comparison"""
        # Initialize a new git repository in the target directory
        subprocess.run(['git', 'init', target_dir], 
                      check=True, capture_output=True, text=True)
        
        # Add the source repository as a remote
        subprocess.run(['git', '-C', target_dir, 'remote', 'add', 'origin', source_repo], 
                      check=True, capture_output=True, text=True)
        
        # Fetch all branches and tags
        subprocess.run(['git', '-C', target_dir, 'fetch', '--all'], 
                      check=True, capture_output=True, text=True)
        
        # Fetch all tags
        subprocess.run(['git', '-C', target_dir, 'fetch', '--tags'], 
                      check=True, capture_output=True, text=True)
    
    def find_unique_files(self, source_repo, target_repo, output_dir):
        # Get list of files in source repo
        source_files = []
        for root, dirs, files in os.walk(source_repo):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, source_repo)
                source_files.append(rel_path)
        
        # Get list of files in target repo
        target_files = []
        for root, dirs, files in os.walk(target_repo):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, target_repo)
                target_files.append(rel_path)
        
        # Find files in source but not in target
        unique_files = [f for f in source_files if f not in target_files]
        
        # Copy unique files to output directory
        for file in unique_files:
            source_file = os.path.join(source_repo, file)
            target_file = os.path.join(output_dir, file)
            
            # Create directory structure
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            
            # Copy file
            shutil.copy2(source_file, target_file)
    
    def update_status(self, message):
        self.status_text.set(message)
        self.root.update_idletasks()
    
    def cleanup(self):
        # Clean up temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

def main():
    root = tk.Tk()
    app = RepoComparisonTool(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.cleanup(), root.destroy()))
    root.mainloop()

if __name__ == "__main__":
    main()
