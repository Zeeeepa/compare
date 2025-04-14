"""
UI components for the Repository Comparison Tool.
"""
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
from typing import Callable, List, Dict, Any, Optional
from ttkthemes import ThemedTk
import platform
from PIL import Image, ImageTk

logger = logging.getLogger('RepoComparisonTool.UIComponents')

class ModernButton(ttk.Button):
    """A modern styled button with hover effects."""
    
    def __init__(self, master=None, **kwargs):
        self.style_name = kwargs.pop('style_name', 'ModernButton.TButton')
        
        # Create a custom style
        style = ttk.Style()
        style.configure(self.style_name, 
                        background='#4a7dfc',
                        foreground='white',
                        padding=(10, 5),
                        font=('Segoe UI', 10))
        
        style.map(self.style_name,
                 background=[('active', '#3a6efc'), ('disabled', '#cccccc')],
                 foreground=[('disabled', '#999999')])
        
        kwargs['style'] = self.style_name
        super().__init__(master, **kwargs)
        
        # Bind hover events
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
    
    def _on_enter(self, event):
        """Handle mouse enter event."""
        self.configure(cursor="hand2")
    
    def _on_leave(self, event):
        """Handle mouse leave event."""
        self.configure(cursor="")

class SearchableListbox(ttk.Frame):
    """A listbox with search functionality."""
    
    def __init__(self, master=None, title: str = "", on_select: Optional[Callable] = None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.title = title
        self.on_select_callback = on_select
        self.items = []
        self.filtered_items = []
        
        # Create UI
        self._create_ui()
    
    def _create_ui(self):
        """Create the UI components."""
        # Frame with border
        self.configure(padding=10, relief="groove", borderwidth=1)
        
        # Title
        ttk.Label(self, text=self.title, font=('Segoe UI', 11, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
        # Search box
        search_frame = ttk.Frame(self)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Bind search event
        self.search_var.trace_add("write", self._on_search)
        
        # Listbox with scrollbar
        listbox_frame = ttk.Frame(self)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.listbox = tk.Listbox(listbox_frame, height=10, 
                                 selectmode=tk.SINGLE,
                                 activestyle='dotbox',
                                 exportselection=False)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        # Bind selection event
        if self.on_select_callback:
            self.listbox.bind('<<ListboxSelect>>', self._on_select)
    
    def set_items(self, items: List[str]):
        """Set the items in the listbox."""
        self.items = items
        self.filtered_items = items.copy()
        self._update_listbox()
    
    def get_selected_item(self) -> Optional[str]:
        """Get the currently selected item."""
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            if 0 <= index < len(self.filtered_items):
                return self.filtered_items[index]
        return None
    
    def _on_search(self, *args):
        """Handle search input changes."""
        search_text = self.search_var.get().lower()
        if search_text:
            self.filtered_items = [item for item in self.items if search_text in item.lower()]
        else:
            self.filtered_items = self.items.copy()
        
        self._update_listbox()
    
    def _update_listbox(self):
        """Update the listbox with filtered items."""
        self.listbox.delete(0, tk.END)
        for item in self.filtered_items:
            self.listbox.insert(tk.END, item)
    
    def _on_select(self, event):
        """Handle item selection."""
        if self.on_select_callback:
            selected_item = self.get_selected_item()
            if selected_item:
                self.on_select_callback(selected_item)

class StatusBar(ttk.Frame):
    """A status bar for displaying messages."""
    
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.status_var = tk.StringVar(value="Ready")
        
        # Create UI
        self._create_ui()
    
    def _create_ui(self):
        """Create the UI components."""
        self.configure(padding=5, relief="sunken", borderwidth=1)
        
        # Status label
        self.status_label = ttk.Label(self, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # Progress bar (initially hidden)
        self.progress = ttk.Progressbar(self, mode='indeterminate', length=100)
        
        # Version label
        version_label = ttk.Label(self, text="v1.1.0")
        version_label.pack(side=tk.RIGHT, padx=5)
    
    def set_status(self, message: str, show_progress: bool = False):
        """Set the status message and optionally show progress bar."""
        self.status_var.set(message)
        
        if show_progress and not self.progress.winfo_ismapped():
            self.progress.pack(side=tk.RIGHT, padx=5, before=self.status_label)
            self.progress.start(10)
        elif not show_progress and self.progress.winfo_ismapped():
            self.progress.stop()
            self.progress.pack_forget()
        
        # Update the UI
        self.update_idletasks()

class SettingsDialog(tk.Toplevel):
    """Dialog for application settings."""
    
    def __init__(self, parent, settings: Dict[str, Any], on_save: Callable[[Dict[str, Any]], None]):
        super().__init__(parent)
        
        self.parent = parent
        self.settings = settings.copy()
        self.on_save = on_save
        
        # Configure dialog
        self.title("Settings")
        self.geometry("400x300")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # Create UI
        self._create_ui()
        
        # Center dialog
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'+{x}+{y}')
    
    def _create_ui(self):
        """Create the UI components."""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Theme selection
        theme_frame = ttk.LabelFrame(main_frame, text="Theme", padding=10)
        theme_frame.pack(fill=tk.X, pady=5)
        
        self.theme_var = tk.StringVar(value=self.settings.get('theme', 'arc'))
        themes = ['arc', 'clearlooks', 'radiance', 'equilux', 'black', 'blue', 'aquativo']
        
        ttk.Label(theme_frame, text="Select theme:").grid(row=0, column=0, sticky=tk.W, pady=5)
        theme_combo = ttk.Combobox(theme_frame, textvariable=self.theme_var, values=themes, state="readonly")
        theme_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Git settings
        git_frame = ttk.LabelFrame(main_frame, text="Git Settings", padding=10)
        git_frame.pack(fill=tk.X, pady=5)
        
        self.git_depth_var = tk.StringVar(value=str(self.settings.get('git_clone_depth', 1)))
        
        ttk.Label(git_frame, text="Clone depth:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(git_frame, textvariable=self.git_depth_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Comparison settings
        comp_frame = ttk.LabelFrame(main_frame, text="Comparison Settings", padding=10)
        comp_frame.pack(fill=tk.X, pady=5)
        
        self.ignore_whitespace_var = tk.BooleanVar(value=self.settings.get('ignore_whitespace', False))
        ttk.Checkbutton(comp_frame, text="Ignore whitespace changes", variable=self.ignore_whitespace_var).pack(anchor=tk.W, pady=2)
        
        self.ignore_case_var = tk.BooleanVar(value=self.settings.get('ignore_case', False))
        ttk.Checkbutton(comp_frame, text="Ignore case differences", variable=self.ignore_case_var).pack(anchor=tk.W, pady=2)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Save", command=self._on_save).pack(side=tk.RIGHT, padx=5)
    
    def _on_save(self):
        """Save settings and close dialog."""
        try:
            git_depth = int(self.git_depth_var.get())
            if git_depth < 1:
                raise ValueError("Clone depth must be at least 1")
            
            # Update settings
            self.settings['theme'] = self.theme_var.get()
            self.settings['git_clone_depth'] = git_depth
            self.settings['ignore_whitespace'] = self.ignore_whitespace_var.get()
            self.settings['ignore_case'] = self.ignore_case_var.get()
            
            # Call save callback
            self.on_save(self.settings)
            
            # Close dialog
            self.destroy()
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))

def create_themed_window(title: str, theme: str = "arc") -> ThemedTk:
    """Create a themed window with the specified theme."""
    root = ThemedTk(theme=theme)
    root.title(title)
    
    # Set icon if available
    try:
        if platform.system() == "Windows":
            root.iconbitmap("icons/app_icon.ico")
        else:
            icon = Image.open("icons/app_icon.png")
            photo = ImageTk.PhotoImage(icon)
            root.iconphoto(True, photo)
    except Exception as e:
        logger.warning(f"Could not set application icon: {str(e)}")
    
    return root
