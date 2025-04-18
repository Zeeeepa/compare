# GitHub Compare Enhancements

This directory contains enhancements for the GitHub Compare tool, focusing on improved multithreading and merge functionality.

## Features

### Enhanced Multithreading

- **Thread Pool Manager**: Efficiently manages a pool of worker threads for better resource utilization
- **Task Tracking**: Each task gets a unique ID for better management and cancellation
- **Callback Processing**: Properly handles callbacks from background threads in the UI thread
- **Resource Cleanup**: Ensures all threads are properly cleaned up when the application exits
- **Error Handling**: Improved error reporting and recovery for threaded operations

### Enhanced Merge Functionality

- **Multiple Merge Strategies**: Support for merge, squash, and rebase strategies
- **Fallback Methods**: Three different methods for merging commits with automatic fallback
- **Conflict Detection**: Ability to check for merge conflicts before attempting a merge
- **Automatic Conflict Resolution**: Options to automatically resolve conflicts using different strategies
- **Batch Processing**: Process commits in batches for better performance with large repositories

## Files

- `thread_pool.py`: Thread pool manager implementation
- `merge_enhancements.py`: Enhanced merge functionality
- `integration_example.py`: Example of how to use the enhancements
- `main_integration.py`: Script to integrate the enhancements into the main application

## Installation

To integrate these enhancements into the main GitHub Compare application, run:

```bash
python enhancements/main_integration.py
```

This will:
1. Create a backup of the original `gitcompare.py` file
2. Patch the file with our enhanced functionality
3. Allow you to run the original application with the enhancements

## Usage

After integration, you can use the GitHub Compare tool as usual:

```bash
python gitcompare.py
```

The enhancements will be automatically available, providing:

- Better performance for long-running operations
- Improved error handling and recovery
- Enhanced merge functionality with multiple strategies
- Automatic cleanup of resources

## Example

You can also run the example application to see the enhancements in action:

```bash
python enhancements/integration_example.py
```

This will show a simple UI demonstrating the enhanced merge functionality.

## Reverting Changes

If you need to revert to the original version, simply copy the backup file:

```bash
cp gitcompare.py.bak gitcompare.py
```

## Requirements

- Python 3.6+
- PyGithub
- tkinter

## License

Same as the main GitHub Compare application.
