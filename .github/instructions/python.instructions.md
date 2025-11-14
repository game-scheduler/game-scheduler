---
description: "Python coding conventions and guidelines"
applyTo: "**/*.py"
---

# Python Coding Conventions

## Python Instructions

- Write clear and concise comments for each function.
- Ensure functions have descriptive names and always use type hints.
- Use the `typing` module for type annotations (e.g., `List[str]`, `Dict[str, int]`).
- Break down complex functions into smaller, more manageable functions.

## Code Style and Formatting

- Follow the **PEP 8** style guide for Python.
- Maintain proper indentation (use 4 spaces for each level of indentation).
- Ensure lines do not exceed 79 characters.
- Place function and class docstrings immediately after the `def` or `class` keyword.
- Use blank lines to separate functions, classes, and code blocks where
  appropriate.
- Put imports at the top of the file, not in functions, arranged by isort.
- Follow the recommendations for these sections from the Google style guide:
  - [2.2 Imports](https://google.github.io/styleguide/pyguide.html#22-imports)
  - [2.3 Packages](https://google.github.io/styleguide/pyguide.html#23-packages)
  - [3.4.1 Trailing commas in sequences of items](https://google.github.io/styleguide/pyguide.html#341-trailing-commas-in-sequences-of-items)
  - [3.8 Comments and Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)

## Environment Management

- use uv for dependency and virtual environment management
  - because the project is managed with uv, always use `uv run` to execute scripts, tests and commands
- use the (src layout)[https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/] for project structure
- always include a `pyproject.toml` file for project configuration

## Example of Proper Documentation

```python
def calculate_area(radius: float) -> float:
    """
    Calculate the area of a circle given the radius.

    Parameters:
    radius (float): The radius of the circle.

    Returns:
    float: The area of the circle, calculated as π * radius^2.
    """
    import math
    return math.pi * radius ** 2
```
