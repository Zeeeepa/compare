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

1. Download and extract the files
2. Make sure you have Python and Git installed
3. Run `run_repo_diff.bat` or directly run `python repo_diff_gui.py`

## Usage

1. Enter repository paths or URLs in the respective fields
   - You can use local repository paths or GitHub repository URLs
   - Example URL: `https://github.com/username/repository.git`

2. Click "Fetch Tags" to retrieve available tags and branches
   - This will show all tags and branches with commit difference indicators
   - Format: `branch_name (+ahead/-behind)`

3. Select the desired tags/branches for each repository
   - Use the search box to find specific tags/branches
   - Use the "Max Commits Behind" filter to hide outdated versions

4. Choose the comparison direction:
   - Repo1 → Repo2: Find files in Repo1 not in Repo2
   - Repo2 → Repo1: Find files in Repo2 not in Repo1
   - Both directions: Find all differences

5. Click "Generate Difference" to create the output
   - The tool will create a directory on your desktop with all the differences
   - The directory structure will be preserved
   - The output folder will open automatically when complete

## Testing

You can run the included test script `test_repo_diff.bat` to create sample repositories with known differences and test the tool.

## Troubleshooting

- Make sure Git is installed and available in your system PATH
- For GitHub repositories, ensure you have proper access permissions
- If you encounter issues with URL input, make sure the URL is in the correct format
- For large repositories, the fetching process may take some time
