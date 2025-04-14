# Repository Comparison Tool

A GUI tool for comparing two Git repositories and finding differences between them.

## Features

- Compare local repositories or remote GitHub repositories
- Select specific branches or tags for comparison
- Filter results based on commit differences
- Generate a directory with all unique files from each repository
- Support for both local and remote repositories
- Proper validation of repository paths and URLs
- Detailed logging for troubleshooting
- Improved branch/tag detection and selection
- Better error handling and user feedback
- Automatic detection of default branches

## Usage

1. Run the tool using `run_repo_diff.bat` or directly with `python repo_diff_gui.py`
2. Enter the paths or URLs of the two repositories you want to compare
3. Click "Fetch Tags" to load all branches and tags from both repositories
4. Select a branch or tag from each repository
5. Choose the comparison direction (files unique to Repo1, Repo2, or both)
6. Click "Generate Difference" to create a directory with the unique files

## Requirements

- Python 3.6+
- Git installed and available in the system PATH
- Tkinter (included with most Python installations)

## Testing

You can test the tool with sample repositories by running `test_repo_diff.bat`, which will:
1. Create two test repositories with different files
2. Launch the comparison tool

## Recent Improvements

- Added comprehensive logging for better troubleshooting
- Improved repository validation for both local and remote repositories
- Enhanced branch/tag detection with better sorting and filtering
- Fixed issues with head/main branch validation and detection
- Added more robust error handling for Git operations
- Improved handling of repository cloning and checkout
- Added fallback mechanisms when branch checkout fails
- Enhanced user feedback with more detailed status messages
- Added a summary file with comparison details
- Fixed issues with file copying and error handling
