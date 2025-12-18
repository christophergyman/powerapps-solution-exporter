# Contributing to PowerApps Solution Exporter

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- PowerApps CLI (pac) installed and in your PATH
- Git

### Setting Up the Development Environment

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/christophergyman/powerapps-solution-exporter.git
   cd powerapps-solution-exporter
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install for development**
   ```bash
   pip install -e .
   ```

## How to Contribute

### Reporting Bugs

If you find a bug, please [open an issue](../../issues/new?template=bug_report.md) with:
- A clear description of the problem
- Steps to reproduce the issue
- Expected vs actual behavior
- Your environment details (OS, Python version, pac version)

### Suggesting Features

Have an idea? [Open a feature request](../../issues/new?template=feature_request.md) describing:
- The problem you're trying to solve
- Your proposed solution
- Any alternatives you've considered

### Submitting Changes

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**
   - Write clear, readable code
   - Add comments for complex logic
   - Follow the existing code style

3. **Test your changes**
   ```bash
   python solution_exporter.py
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "Brief description of changes"
   ```

5. **Push and create a Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then open a PR on GitHub.

## Code Style

- Use meaningful variable and function names
- Include docstrings for functions
- Keep functions focused and small
- Use type hints where appropriate

### Example

```python
def export_solution(solution_name: str, output_dir: str = "./exports") -> bool:
    """
    Export a solution by name to the specified directory.
    
    Args:
        solution_name: The unique name of the solution to export
        output_dir: Directory to save the exported solution
        
    Returns:
        True if export was successful, False otherwise
    """
    # Implementation...
```

## Questions?

Feel free to open an issue if you have questions about contributing.

Thank you for helping improve PowerApps Solution Exporter!

