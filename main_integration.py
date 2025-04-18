"""
Main integration script for the GitHub Compare tool.
This script modifies the main gitcompare.py file to integrate the enhanced merge functionality and multithreading.
"""

import os
import sys

def main():
    """Main function to integrate the enhancements"""
    # Check if gitcompare.py exists
    if not os.path.exists('gitcompare.py'):
        print("Error: gitcompare.py not found")
        return 1
    
    # Check if merge_enhancements.py and integration_example.py exist
    if not os.path.exists('merge_enhancements.py') or not os.path.exists('integration_example.py'):
        print("Error: merge_enhancements.py or integration_example.py not found")
        return 1
    
    # Read the content of gitcompare.py
    with open('gitcompare.py', 'r') as f:
        content = f.read()
    
    # Add import for integration_example
    import_line = "from integration_example import integrate_enhancements"
    if import_line not in content:
        # Find the last import line
        import_lines = [line for line in content.split('\n') if line.startswith('import ') or line.startswith('from ')]
        last_import_line = import_lines[-1]
        
        # Add our import after the last import
        content = content.replace(last_import_line, last_import_line + '\n' + import_line)
    
    # Add integration code to the __init__ method
    init_end = "        if self.github_token:\n            self.init_github_client()"
    integration_code = "        if self.github_token:\n            self.init_github_client()\n        \n        # Integrate enhanced merge functionality and multithreading\n        integrate_enhancements(self)"
    
    if integration_code not in content:
        content = content.replace(init_end, integration_code)
    
    # Write the modified content back to gitcompare.py
    with open('gitcompare.py', 'w') as f:
        f.write(content)
    
    print("Successfully integrated enhanced merge functionality and multithreading into gitcompare.py")
    return 0

if __name__ == "__main__":
    sys.exit(main())
