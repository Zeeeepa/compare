import re

# Read the original file
with open('gitcompare.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Read the improved functions
with open('temp/improved_commit_removal.py', 'r', encoding='utf-8') as f:
    improved_functions = f.read()

# Add imports at the top of the file
import_pattern = r'import os\nimport webbrowser\nimport threading\nimport json\nimport datetime'
import_replacement = 'import os\nimport webbrowser\nimport threading\nimport json\nimport datetime\nimport time\nimport logging\nimport tempfile\nimport subprocess'

content = re.sub(import_pattern, import_replacement, content)

# Add logging setup after imports
logging_setup = """
# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.expanduser("~"), ".github_compare.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GitHubCompare")
"""

# Find the class definition
class_pattern = r'class GitHubCompare:'
content = re.sub(class_pattern, logging_setup + '\n' + class_pattern, content)

# Replace the remove_selected_commits method
remove_pattern = r'def remove_selected_commits\(self\):.*?def after_commit_removal\(self, num_removed\):.*?messagebox\.showinfo\("Success", f"Successfully removed {num_removed} commits"\)'
remove_pattern = re.compile(remove_pattern, re.DOTALL)

# Extract the improved functions without the imports and logging setup
improved_functions_clean = re.sub(r'import.*?\)\nlogger = logging\.getLogger\("GitHubCompare"\)\n\n', '', improved_functions, flags=re.DOTALL)

# Replace the old functions with the improved ones
content = re.sub(remove_pattern, improved_functions_clean, content)

# Write the updated content back to the file
with open('gitcompare.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated gitcompare.py with improved commit removal functionality")
