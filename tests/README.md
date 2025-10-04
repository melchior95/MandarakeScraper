# Test Files

This directory contains test files that are still useful after the GUI modularization.

## Files

- `test_gui_compatibility.py` - Tests for the modularized GUI components
- `test_gui_utils.py` - Tests for GUI utility functions

## Running Tests

To run all tests:
```bash
python -m pytest tests/

To run a specific test:
```bash
python tests/test_gui_compatibility.py
```

## Note

Many obsolete test files were removed during the modularization cleanup process.
The remaining tests focus on testing the new modular architecture.
