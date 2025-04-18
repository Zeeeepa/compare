#!/usr/bin/env python3
"""
Script to integrate the threading and merging enhancements into the main gitcompare.py file.
"""
import re

# Read the original file
with open('gitcompare.py', 'r') as f:
    original_content = f.read()

# Extract the imports to add
imports_to_add = """
# Import the new modules
from thread_pool import ThreadPool, Task
from merge_operations import MergeOperations, MergeStrategy
"""

# Add imports after the existing imports
import_pattern = r'(from functools import partial\n)'
modified_content = re.sub(import_pattern, r'\1\n' + imports_to_add, original_content)

# Add thread_pool and merge_operations initialization to __init__
init_pattern = r'([ ]{8}# Initialize GitHub client if token exists\n[ ]{8}if self\.github_token:\n[ ]{12}self\.init_github_client\(\))'
init_addition = """
        # Initialize thread pool
        self.thread_pool = ThreadPool(num_workers=5)
        self.merge_operations = None  # Will be initialized when GitHub client is initialized
        
\\1"""
modified_content = re.sub(init_pattern, init_addition, modified_content)

# Write the modified content back to the file
with open('gitcompare.py.new', 'w') as f:
    f.write(modified_content)

print("Changes integrated successfully. New file created as gitcompare.py.new")
