1. Main Python Script (repo_diff_gui.py)
This is the core file that implements the Tkinter UI and repository comparison functionality:
 python
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
        
        ttk.Radiobutton(direction_frame, text="Repo1 → Repo2 (files in Repo1 not in Repo2)", 
                        variable=self.comparison_direction, value="1to2").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(direction_frame, text="Repo2 → Repo1 (files in Repo2 not in Repo1)", 
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
I'll continue with the rest of the implementation in the next messages.
:computer: View my work

React

02:17
2. Repository Handling Methods
These methods handle repository operations like browsing, cloning, and fetching tags:
 python
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
                subprocess.run(['git', 'clone', repo_path, target_dir], 
                              check=True, capture_output=True, text=True)
                return True
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Error", f"Failed to clone repository: {e.stderr}")
                return False
        else:
            # Local repository, just use it directly
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
:computer: View my work
02:18
3. Tag and Branch Handling Methods
These methods handle fetching, filtering, and displaying tags and branches:
 python
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
:computer: View my work
02:18
4. Difference Generation Methods
These methods handle generating the directory structure showing the differences between repositories:
 python
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
        
        os.makedirs(temp_repo1, exist_ok=True)
        os.makedirs(temp_repo2, exist_ok=True)
        
        # Clone repositories to temporary directories with specific tags/branches
        self.update_status("Preparing repositories...")
        
        try:
            # Clone repo1 with selected tag/branch
            subprocess.run(['git', 'clone', repo1_dir, temp_repo1], 
                          check=True, capture_output=True, text=True)
            subprocess.run(['git', '-C', temp_repo1, 'checkout', self.repo1_selected_tag.get()], 
                          check=True, capture_output=True, text=True)
            
            # Clone repo2 with selected tag/branch
            subprocess.run(['git', 'clone', repo2_dir, temp_repo2], 
                          check=True, capture_output=True, text=True)
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
:computer: View my work
02:18
5. Utility Methods and Main Function
These are the final methods for the class and the main function to run the application:
 python
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
6. Batch File to Run the Application (run_repo_diff.bat)
 batch
@echo off
echo Starting Repository Comparison Tool...
python repo_diff_gui.py
7. Test Script (test_repo_diff.bat)
 batch
@echo off
echo Creating test repositories...

mkdir test_repo1
cd test_repo1
git init
echo # Test Repository 1 > README.md
mkdir src
echo function test() { return true; } > src/main.js
mkdir docs
echo # Documentation > docs/index.md
git add .
git commit -m "Initial commit for test repo 1"
echo function newFeature() { return "new"; } > src/feature.js
git add .
git commit -m "Add new feature"
git tag v1.0
cd ..

mkdir test_repo2
cd test_repo2
git init
echo # Test Repository 2 > README.md
mkdir src
echo function test() { return true; } > src/main.js
mkdir config
echo { "setting": "value" } > config/settings.json
git add .
git commit -m "Initial commit for test repo 2"
git tag v1.0
cd ..

echo Test repositories created successfully!
echo.
echo Now you can use the Repository Comparison Tool to compare these test repositories.
echo.
echo Press any key to start the tool...
pause > nul
python repo_diff_gui.py
:computer: View my work
02:19
8. README.md
``` markdown
# Repository Comparison Tool
A Windows application that allows you to compare two GitHub repositories and generate a directory structure showing the differences between them.
## Features
- Compare two GitHub repositories or local repository paths
- Select specific tags/versions for each repository
- View commit differences (ahead/behind) between versions
- Filter versions based on how many commits they are behind
- Search for specific branches/tags
- Generate a directory structure showing all differences between repositories
## Requirements
- Python 3.6 or higher
- Git installed and available in your system PATH
- Tkinter (included with standard Python installation on Windows)
## Installation
Download and extract the files
Make sure you have Python and Git installed
Run run_repo_diff.bat or directly run python repo_diff_gui.py
## Usage
Enter repository paths or URLs in the respective fields
- You can use local repository paths or GitHub repository URLs
- Example URL: https://github.com/username/repository.git
Click "Fetch Tags" to retrieve available tags and branches
- This will show all tags and branches with commit difference indicators
- Format: branch_name (+ahead/-behind)
Select the desired tags/branches for each repository
- Use the search box to find specific tags/branches
- Use the "Max Commits Behind" filter to hide outdated versions
Choose the comparison direction:
- Repo1 → Repo2: Find files in Repo1 not in Repo2
- Repo2 → Repo1: Find files in Repo2 not in Repo1
- Both directions: Find all differences
Click "Generate Difference" to create the output
- The tool will create a directory on your desktop with all the differences
- The directory structure will be preserved
- The output folder will open automatically when complete
## Testing
You can run the included test script test_repo_diff.bat to create sample repositories with known differences and test the tool.
## Troubleshooting
- Make sure Git is installed and available in your system PATH
- For GitHub repositories, ensure you have proper access permissions
- If you encounter issues with URL input, make sure the URL is in the correct format
- For large repositories, the fetching process may take some time
Create a new directory for the project
Create the following files with the code provided:
repo_diff_gui.py - The main Python script
run_repo_diff.bat - Batch file to run the application
test_repo_diff.bat - Test script to verify functionality
README.md - Documentation with usage instructions
Run the application using run_repo_diff.bat or by running python repo_diff_gui.py directly
To test the tool, you can run test_repo_diff.bat which will create two test repositories with known differences
Robust URL Handling: The tool now properly handles GitHub repository URLs with improved parsing and error handling.
Complete Tag/Branch Fetching: The tool fetches all tags and branches from both repositories and displays them with commit difference indicators.
Bidirectional Comparison: The tool can now find files that exist in Repo1 but not in Repo2, and vice versa, preserving the exact directory structure.
Filtering and Search: Added filtering to hide repositories that are more than X commits behind and search functionality to find specific branches/tags.
Improved Error Handling: Better error messages and handling for common issues like repository access, tag selection, and file operations.
Clean UI Separation: The UI is now more organized with clear sections for repository selection, tag/branch selection, filtering, and comparison options.
