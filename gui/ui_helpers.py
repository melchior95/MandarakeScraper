"""UI Helper Functions - Dialog boxes and informational windows."""

import tkinter as tk
from tkinter import ttk, messagebox


def position_dialog_at_cursor(dialog):
    """
    Position a dialog window at the current cursor position.

    Args:
        dialog: Toplevel window to position
    """
    # Get cursor position
    x = dialog.winfo_pointerx()
    y = dialog.winfo_pointery()

    # Update window to get actual size
    dialog.update_idletasks()

    # Get window dimensions
    width = dialog.winfo_width()
    height = dialog.winfo_height()

    # Get screen dimensions
    screen_width = dialog.winfo_screenwidth()
    screen_height = dialog.winfo_screenheight()

    # Adjust position to keep window on screen
    # Position with a small offset so cursor isn't covering the title bar
    x_offset = 10
    y_offset = 10

    # Check right edge
    if x + width + x_offset > screen_width:
        x = screen_width - width - 20
    else:
        x = x + x_offset

    # Check bottom edge
    if y + height + y_offset > screen_height:
        y = screen_height - height - 20
    else:
        y = y + y_offset

    # Ensure window isn't off the left or top edge
    x = max(0, x)
    y = max(0, y)

    dialog.geometry(f"+{x}+{y}")


def show_ransac_info():
    """Show RANSAC information dialog."""
    info_text = """
RANSAC GEOMETRIC VERIFICATION

What it does:
• Verifies that matched image features have consistent spatial relationships
• Uses RANSAC (Random Sample Consensus) algorithm to detect true matches
• Adds ~40-50% processing time but significantly improves accuracy

When to use:
✓ When you need maximum accuracy for difficult matches
✓ When comparing similar-looking items that are different editions
✓ When false positives are costly (e.g., expensive items)

When to skip:
• For quick exploratory searches
• When processing large batches (hundreds of items)
• When visual similarity is good enough

Current algorithm (without RANSAC):
• Template matching: 60% weight
• Feature matching: 25% weight
• SSIM: 10% weight
• Histogram: 5% weight
• Consistency bonus: up to 25% boost

With RANSAC enabled:
• Adds geometric coherence verification (15-20% weight)
• Penalizes random/scattered feature matches
• Increases match confidence scores
    """

    messagebox.showinfo("RANSAC Geometric Verification", info_text)


def show_image_search_help(parent):
    """Show image search help dialog.

    Args:
        parent: Parent window for the dialog
    """
    help_text = """
IMAGE SEARCH HELP

🎯 QUICK START:
1. Click "Select Image..." to upload a product photo
2. Use the search functionality to find similar items

📊 RESULTS:
- Shows sold item counts and price ranges
- Calculates profit margins with different scenarios
- Estimates fees and shipping costs
- Provides market recommendations
    """

    # Create help window
    help_window = tk.Toplevel(parent)
    help_window.title("Image Search Help")
    help_window.geometry("500x400")
    help_window.transient(parent)

    text_frame = ttk.Frame(help_window)
    text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Arial", 10))
    scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
    text_widget.configure(yscrollcommand=scrollbar.set)

    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    text_widget.insert(tk.END, help_text)
    text_widget.config(state=tk.DISABLED)

    ttk.Button(help_window, text="Close", command=help_window.destroy).pack(pady=10)
