    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GitHub Branch Comparison Tool")
        self.root.geometry("1000x700")  # Larger default window size
        
        # Initialize variables
        self.github_token = ""
        self.g = None
        self.cache = {
            "repos": [],
            "branches": {},
            "last_updated": None
        }
        
        # Initialize thread pool and merge manager
        self.thread_pool = ThreadPoolManager(max_workers=5)
        
        # Load token from config file
        self.config_file = os.path.join(os.path.expanduser("~"), ".github_compare_config")
        self.load_config()
        
        # Initialize merge manager after loading token
        self.merge_manager = MergeManager(self.github_token, self.root)
        
        # Set up a timer to process callbacks from the thread pool
        self._setup_callback_timer()
        
        # Register cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Create main frame with status bar
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
