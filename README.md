# Repository Comparison Tool

A modern GUI tool for comparing two Git repositories and finding differences between them.

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
- Cross-platform support (Windows, macOS, Linux)
- Modern UI with themes
- Persistent settings
- Asynchronous processing for better responsiveness

## Installation

### Prerequisites

- Python 3.6+
- Git installed and available in the system PATH

### Option 1: Install from source

```bash
# Clone the repository
git clone https://github.com/Zeeeepa/compare.git
cd compare

# Install dependencies
pip install -r requirements.txt

# Run the tool
python repo_diff_gui_upgraded.py
```

### Option 2: Install as a package

```bash
# Clone the repository
git clone https://github.com/Zeeeepa/compare.git
cd compare

# Install the package
pip install .

# Run the tool
repo-diff
```

## Usage

1. Run the tool using `python repo_diff_gui_upgraded.py` or `repo-diff` if installed as a package
2. Enter the paths or URLs of the two repositories you want to compare
3. Click "Fetch Tags & Branches" to load all branches and tags from both repositories
4. Select a branch or tag from each repository
5. Choose the comparison direction (files unique to Repo1, Repo2, or both)
6. Click "Generate Difference" to create a directory with the unique files

## Testing

You can test the tool with sample repositories by running:

- On Windows: `test_repo_diff.bat`
- On macOS/Linux: `./test_repo_diff.sh`

This will:
1. Create two test repositories with different files
2. Launch the comparison tool

## Configuration

The tool stores settings in `~/.repo_comparison_settings.json`. You can modify these settings through the UI by selecting "Settings" from the File menu.

Available settings include:
- UI theme
- Git clone depth
- Comparison options (ignore whitespace, ignore case)

## Recent Improvements

- Completely refactored codebase with better organization
- Added proper package structure
- Improved UI with modern styling and themes
- Added cross-platform support
- Enhanced error handling and user feedback
- Added settings dialog and persistent settings
- Improved Git operations with GitPython
- Added asynchronous processing for better responsiveness
- Added comprehensive documentation
- Added proper type hints
- Added menu with additional functionality
- Added recent repositories tracking
