# GitHub Branch Comparison Tool

A powerful desktop application for comparing and managing GitHub repository branches with a user-friendly interface.

## Features

### Local Compare Tab
- Compare different branches within the same repository
- View commit differences between branches
- Filter commits by:
  - Recent commits (last 30 days)
  - Verified commits only
- Interactive commit list with detailed information

### Origin Compare Tab
- Compare your fork with its parent repository
- Track commits ahead/behind the parent repository
- Cherry-pick specific commits from parent to your fork
- Create pull requests directly from the interface
- View detailed commit information and differences

### General Features
- GitHub token-based authentication
- Repository search functionality
- Cached repository and branch information
- Progress indicators for long operations
- Status bar for operation feedback
- Settings management for GitHub tokens
- Automatic refresh of repository data

## Installation

1. Ensure you have Python installed on your system
2. Install required dependencies:
```bash
pip install PyGithub tkinter
```

3. Run the application:
```bash
python gitcompare.py
```

## Configuration

The application stores your GitHub token in `~/.github_compare_config`. You can set this up through the Settings interface in the application.

## Usage

1. Launch the application
2. Enter your GitHub token in Settings if not already configured
3. Select a repository from the dropdown
4. Choose branches to compare
5. Use the comparison tabs:
   - Local Compare: Compare branches within the same repository
   - Origin Compare: Compare your fork with its parent repository

### Local Branch Comparison
1. Select the repository
2. Choose base and compare branches
3. Click "Compare Branches" to see differences
4. Use filters to focus on specific commits

### Origin/Fork Comparison
1. Select your forked repository
2. Choose branches to compare with the parent
3. View commits ahead/behind
4. Merge specific commits or create pull requests

## Contributing

Feel free to submit issues and enhancement requests!

## License

MIT License - feel free to use and modify as needed.
