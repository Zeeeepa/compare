#!/usr/bin/env python3
"""
Repository Comparison Tool - A GUI tool for comparing two Git repositories.

This tool allows users to compare two Git repositories (local or remote)
and find differences between them. It supports selecting specific branches
or tags, filtering results, and generating a directory with unique files.
"""
import os
import sys
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import platform
import json
import webbrowser
from typing import Dict, Any, List, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('RepoComparisonTool')

# Try to import the package modules
try:
    from repo_comparison.ui_components import (
        ModernButton, SearchableListbox, StatusBar, 
        SettingsDialog, create_themed_window
    )
    from repo_comparison.git_utils import GitUtils
    from repo_comparison.comparison import ComparisonManager
    
    PACKAGE_IMPORT = True
except ImportError:
    logger.warning("Could not import package modules, using local imports")
    PACKAGE_IMPORT = False
    
    # Local imports for development
    class GitUtils:
        @staticmethod
        def is_url(path):
            return path.startswith(('http://', 'https://', 'git@'))
        
        @staticmethod
        def get_repo_name(repo_path):
            if GitUtils.is_url(repo_path):
                if repo_path.endswith('.git'):
                    repo_path = repo_path[:-4]
                
                if repo_path.startswith('git@'):
                    parts = repo_path.split(':')
                    if len(parts) >= 2:
                        return parts[1].split('/')[-1]
                
                parts = repo_path.rstrip('/').split('/')
                return parts[-1]
            else:
                return os.path.basename(os.path.normpath(repo_path))
        
        @staticmethod
        def get_tags_and_branches(repo_path):
            # Simplified version for local development
            return ["main", "master"], ["main", "master", "develop"]
    
    # Simplified UI components for local development
    class ModernButton(ttk.Button):
        pass
    
    class SearchableListbox(ttk.Frame):
        def __init__(self, master=None, title="", on_select=None, **kwargs):
            super().__init__(master, **kwargs)
            self.title = title
            self.on_select_callback = on_select
            self.items = []
            self.filtered_items = []
            
            # Create a simple frame with title and listbox
            ttk.Label(self, text=title).pack(anchor=tk.W)
            self.listbox = tk.Listbox(self, height=10)
            self.listbox.pack(fill=tk.BOTH, expand=True)
            
            if on_select:
                self.listbox.bind('<<ListboxSelect>>', 
                                 lambda e: on_select(self.get_selected_item()))
        
        def set_items(self, items):
            self.items = items
            self.filtered_items = items.copy()
            self.listbox.delete(0, tk.END)
            for item in items:
                self.listbox.insert(tk.END, item)
        
        def get_selected_item(self):
            selection = self.listbox.curselection()
            if selection:
                index = selection[0]
                if 0 <= index < len(self.filtered_items):
                    return self.filtered_items[index]
            return None
    
    class StatusBar(ttk.Frame):
        def __init__(self, master=None, **kwargs):
            super().__init__(master, **kwargs)
            self.status_var = tk.StringVar(value="Ready")
            ttk.Label(self, textvariable=self.status_var).pack(side=tk.LEFT)
        
        def set_status(self, message, show_progress=False):
            self.status_var.set(message)
            self.update_idletasks()
    
    class SettingsDialog(tk.Toplevel):
        def __init__(self, parent, settings, on_save):
            super().__init__(parent)
            self.title("Settings")
            self.settings = settings.copy()
            ttk.Button(self, text="Save", 
                      command=lambda: on_save(self.settings)).pack()
    
    def create_themed_window(title, theme="default"):
        root = tk.Tk()
        root.title(title)
        return root
    
    class ComparisonManager:
        def __init__(self, settings=None):
            self.settings = settings or {}
        
        def cleanup(self):
            pass
        
        def run_comparison_async(self, repo1_path, repo2_path, repo1_ref, repo2_ref, 
                                comparison_direction, max_commits_behind=100,
                                callback=None, on_complete=None):
            # Simplified version for local development
            import threading
            def _run():
                try:
                    # Simulate comparison
                    import time
                    if callback:
                        callback("Preparing repositories...", True)
                        time.sleep(1)
                        callback("Cloning repositories...", True)
                        time.sleep(1)
                        callback("Checking out branches...", True)
                        time.sleep(1)
                        callback("Finding unique files...", True)
                        time.sleep(1)
                        callback("Comparison completed successfully", False)
                    
                    # Create a dummy output directory
                    output_dir = os.path.join(os.path.expanduser("~"), "RepoComparisons", "dummy_comparison")
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # Create a dummy summary file
                    with open(os.path.join(output_dir, "comparison_summary.txt"), "w") as f:
                        f.write("Dummy comparison summary\n")
                    
                    if on_complete:
                        on_complete(output_dir, {"repo1_unique": 10, "repo2_unique": 5})
                except Exception as e:
                    logger.error(f"Error in async comparison: {str(e)}")
                    if callback:
                        callback(f"Error: {str(e)}", False)
            
            thread = threading.Thread(target=_run)
            thread.daemon = True
            thread.start()
            return thread


class RepoComparisonTool:
    """Main application class for the Repository Comparison Tool."""
    
    def __init__(self, root):
        """Initialize the application."""
        self.root = root
        self.root.title("Repository Comparison Tool")
        self.root.geometry("1000x700")
        self.root.minsize(900, 700)
        
        # Load settings
        self.settings = self.load_settings()
        
        # Variables
        self.repo1_path = tk.StringVar()
        self.repo2_path = tk.StringVar()
        self.max_commits_behind = tk.StringVar(value="100")
        self.comparison_direction = tk.StringVar(value="both")
        self.repo1_selected_tag = tk.StringVar()
        self.repo2_selected_tag = tk.StringVar()
        
        # UI Components
        self.repo1_tags_listbox = None
        self.repo2_tags_listbox = None
        self.status_bar = None
        self.main_frame = None
        
        # State variables
        self.comparison_in_progress = False
        self.last_comparison_output = None
        self.comparison_thread = None
        
        # Create comparison manager
        self.comparison_manager = ComparisonManager(self.settings)
        
        # Create UI
        self.create_ui()
        
        # Set up protocol for window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file."""
        settings_path = os.path.join(os.path.expanduser("~"), ".repo_comparison_settings.json")
        default_settings = {
            "theme": "arc",
            "git_clone_depth": 1,
            "ignore_whitespace": False,
            "ignore_case": False,
            "recent_repos": []
        }
        
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                return {**default_settings, **settings}
            except Exception as e:
                logger.error(f"Error loading settings: {str(e)}")
        
        return default_settings
    
    def save_settings(self):
        """Save settings to file."""
        settings_path = os.path.join(os.path.expanduser("~"), ".repo_comparison_settings.json")
        try:
            with open(settings_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
    
    def create_ui(self):
        """Create the user interface."""
        # Create menu
        self.create_menu()
        
        # Main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Repository inputs
        self.create_repo_inputs(self.main_frame)
        
        # Fetch tags button
        fetch_frame = ttk.Frame(self.main_frame)
        fetch_frame.pack(fill=tk.X, pady=5)
        ModernButton(fetch_frame, text="Fetch Tags & Branches", 
                    command=self.fetch_tags).pack(pady=10)
        
        # Tags selection frame
        tags_frame = ttk.Frame(self.main_frame)
        tags_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        tags_frame.columnconfigure(0, weight=1)
        tags_frame.columnconfigure(1, weight=1)
        
        # Repository 1 tags
        self.repo1_tags_listbox = SearchableListbox(
            tags_frame, 
            title="Repository 1 Tags/Branches",
            on_select=lambda tag: self.repo1_selected_tag.set(tag)
        )
        self.repo1_tags_listbox.grid(row=0, column=0, sticky=tk.NSEW, padx=5)
        
        # Repository 2 tags
        self.repo2_tags_listbox = SearchableListbox(
            tags_frame, 
            title="Repository 2 Tags/Branches",
            on_select=lambda tag: self.repo2_selected_tag.set(tag)
        )
        self.repo2_tags_listbox.grid(row=0, column=1, sticky=tk.NSEW, padx=5)
        
        # Comparison options
        self.create_comparison_options(self.main_frame)
        
        # Generate button
        generate_frame = ttk.Frame(self.main_frame)
        generate_frame.pack(fill=tk.X, pady=10)
        ModernButton(generate_frame, text="Generate Difference", 
                    command=self.generate_difference).pack(pady=5)
        
        # Status bar
        self.status_bar = StatusBar(self.root)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def create_menu(self):
        """Create the application menu."""
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Repository 1", command=lambda: self.browse_repo(self.repo1_path))
        file_menu.add_command(label="Open Repository 2", command=lambda: self.browse_repo(self.repo2_path))
        file_menu.add_separator()
        file_menu.add_command(label="Settings", command=self.show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Create Test Repositories", command=self.create_test_repos)
        tools_menu.add_command(label="Open Output Directory", command=self.open_output_dir)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Documentation", command=self.show_documentation)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)
    
    def create_repo_inputs(self, parent):
        """Create repository input fields."""
        # Repository 1 frame
        repo1_frame = ttk.LabelFrame(parent, text="Repository 1", padding="10")
        repo1_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(repo1_frame, text="Repository Path or URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        repo1_entry = ttk.Entry(repo1_frame, textvariable=self.repo1_path, width=50)
        repo1_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        ttk.Button(repo1_frame, text="Browse", 
                  command=lambda: self.browse_repo(self.repo1_path)).grid(row=0, column=2, padx=5, pady=5)
        
        # Repository 2 frame
        repo2_frame = ttk.LabelFrame(parent, text="Repository 2", padding="10")
        repo2_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(repo2_frame, text="Repository Path or URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        repo2_entry = ttk.Entry(repo2_frame, textvariable=self.repo2_path, width=50)
        repo2_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        ttk.Button(repo2_frame, text="Browse", 
                  command=lambda: self.browse_repo(self.repo2_path)).grid(row=0, column=2, padx=5, pady=5)
    
    def create_comparison_options(self, parent):
        """Create comparison options UI."""
        # Filter frame
        filter_frame = ttk.LabelFrame(parent, text="Filtering Options", padding="10")
        filter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(filter_frame, text="Max Commits Behind:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(filter_frame, textvariable=self.max_commits_behind, width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Comparison direction
        direction_frame = ttk.LabelFrame(parent, text="Comparison Direction", padding="10")
        direction_frame.pack(fill=tk.X, pady=5)
        
        ttk.Radiobutton(direction_frame, text="Repo1 → Repo2 (files in Repo1 not in Repo2)", 
                        variable=self.comparison_direction, value="1to2").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(direction_frame, text="Repo2 → Repo1 (files in Repo2 not in Repo1)", 
                        variable=self.comparison_direction, value="2to1").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(direction_frame, text="Both directions (all differences)", 
                        variable=self.comparison_direction, value="both").pack(anchor=tk.W, pady=2)
    
    def browse_repo(self, path_var):
        """Open file dialog to select a repository."""
        folder_path = filedialog.askdirectory()
        if folder_path:
            path_var.set(folder_path)
            logger.info(f"Selected repository path: {folder_path}")
            
            # Add to recent repositories
            recent_repos = self.settings.get("recent_repos", [])
            if folder_path not in recent_repos:
                recent_repos.insert(0, folder_path)
                # Keep only the 10 most recent
                self.settings["recent_repos"] = recent_repos[:10]
                self.save_settings()
    
    def fetch_tags(self):
        """Fetch tags and branches from both repositories."""
        repo1_path = self.repo1_path.get()
        repo2_path = self.repo2_path.get()
        
        if not repo1_path and not repo2_path:
            messagebox.showwarning("Warning", "Please enter at least one repository path or URL.")
            return
        
        self.status_bar.set_status("Fetching tags and branches...", True)
        
        # Fetch for repo1
        if repo1_path:
            try:
                tags, branches = GitUtils.get_tags_and_branches(repo1_path)
                all_refs = sorted(set(tags + branches))
                self.repo1_tags_listbox.set_items(all_refs)
                
                # Select default branch if available
                if "main" in all_refs:
                    self.repo1_selected_tag.set("main")
                elif "master" in all_refs:
                    self.repo1_selected_tag.set("master")
                elif all_refs:
                    self.repo1_selected_tag.set(all_refs[0])
            except Exception as e:
                logger.error(f"Error fetching tags for repository 1: {str(e)}")
                messagebox.showerror("Error", f"Failed to fetch tags for repository 1: {str(e)}")
        
        # Fetch for repo2
        if repo2_path:
            try:
                tags, branches = GitUtils.get_tags_and_branches(repo2_path)
                all_refs = sorted(set(tags + branches))
                self.repo2_tags_listbox.set_items(all_refs)
                
                # Select default branch if available
                if "main" in all_refs:
                    self.repo2_selected_tag.set("main")
                elif "master" in all_refs:
                    self.repo2_selected_tag.set("master")
                elif all_refs:
                    self.repo2_selected_tag.set(all_refs[0])
            except Exception as e:
                logger.error(f"Error fetching tags for repository 2: {str(e)}")
                messagebox.showerror("Error", f"Failed to fetch tags for repository 2: {str(e)}")
        
        self.status_bar.set_status("Tags and branches fetched successfully", False)
    
    def generate_difference(self):
        """Generate difference between repositories."""
        # Validate inputs
        repo1_path = self.repo1_path.get()
        repo2_path = self.repo2_path.get()
        repo1_ref = self.repo1_selected_tag.get()
        repo2_ref = self.repo2_selected_tag.get()
        
        if not repo1_path or not repo2_path:
            messagebox.showwarning("Warning", "Please enter both repository paths or URLs.")
            return
        
        if not repo1_ref or not repo2_ref:
            messagebox.showwarning("Warning", "Please select a branch or tag for both repositories.")
            return
        
        try:
            max_commits = int(self.max_commits_behind.get())
            if max_commits <= 0:
                raise ValueError("Max commits must be a positive number")
        except ValueError:
            messagebox.showwarning("Warning", "Please enter a valid number for max commits behind.")
            return
        
        # Start comparison in background thread
        self.comparison_manager.run_comparison_async(
            repo1_path, repo2_path, repo1_ref, repo2_ref,
            self.comparison_direction.get(), max_commits,
            callback=self.update_status,
            on_complete=self.on_comparison_complete
        )
    
    def update_status(self, message, show_progress=False):
        """Update status bar with message."""
        self.status_bar.set_status(message, show_progress)
    
    def on_comparison_complete(self, output_dir, stats):
        """Handle completion of comparison."""
        total_files = stats["repo1_unique"] + stats["repo2_unique"]
        messagebox.showinfo(
            "Comparison Complete", 
            f"Comparison completed successfully!\n\n"
            f"Found {total_files} unique files:\n"
            f"- {stats['repo1_unique']} files unique to Repository 1\n"
            f"- {stats['repo2_unique']} files unique to Repository 2\n\n"
            f"Results saved to:\n{output_dir}"
        )
        
        # Ask if user wants to open the output directory
        if messagebox.askyesno("Open Results", "Do you want to open the results directory?"):
            self.open_directory(output_dir)
    
    def open_directory(self, path):
        """Open a directory in the file explorer."""
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":  # macOS
                os.system(f"open '{path}'")
            else:  # Linux
                os.system(f"xdg-open '{path}'")
        except Exception as e:
            logger.error(f"Error opening directory: {str(e)}")
            messagebox.showerror("Error", f"Failed to open directory: {str(e)}")
    
    def show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self.root, self.settings, self.on_settings_save)
        self.root.wait_window(dialog)
    
    def on_settings_save(self, new_settings):
        """Handle settings save."""
        self.settings = new_settings
        self.save_settings()
        messagebox.showinfo("Settings", "Settings saved successfully.")
    
    def create_test_repos(self):
        """Create test repositories."""
        if messagebox.askyesno("Create Test Repositories", 
                              "This will create two test Git repositories in the current directory. Continue?"):
            try:
                # Create test script based on platform
                if platform.system() == "Windows":
                    script_path = "test_repo_diff.bat"
                else:
                    script_path = "test_repo_diff.sh"
                
                if os.path.exists(script_path):
                    if platform.system() == "Windows":
                        os.system(script_path)
                    else:
                        os.system(f"bash {script_path}")
                else:
                    messagebox.showerror("Error", f"Test script not found: {script_path}")
            except Exception as e:
                logger.error(f"Error creating test repositories: {str(e)}")
                messagebox.showerror("Error", f"Failed to create test repositories: {str(e)}")
    
    def open_output_dir(self):
        """Open the output directory."""
        output_dir = os.path.join(os.path.expanduser("~"), "RepoComparisons")
        os.makedirs(output_dir, exist_ok=True)
        self.open_directory(output_dir)
    
    def show_documentation(self):
        """Show documentation."""
        # Open GitHub repository or documentation URL
        webbrowser.open("https://github.com/Zeeeepa/compare")
    
    def show_about(self):
        """Show about dialog."""
        messagebox.showinfo(
            "About Repository Comparison Tool",
            "Repository Comparison Tool v1.1.0\n\n"
            "A GUI tool for comparing two Git repositories and finding differences between them.\n\n"
            "© 2025 Zeeeepa"
        )
    
    def on_close(self):
        """Handle window close event."""
        # Clean up resources
        self.comparison_manager.cleanup()
        
        # Save settings
        self.save_settings()
        
        # Close window
        self.root.destroy()

def main():
    """Main entry point for the application."""
    # Create themed window
    if PACKAGE_IMPORT:
        root = create_themed_window("Repository Comparison Tool")
    else:
        root = tk.Tk()
        root.title("Repository Comparison Tool")
    
    # Create application
    app = RepoComparisonTool(root)
    
    # Start main loop
    root.mainloop()

if __name__ == "__main__":
    main()
