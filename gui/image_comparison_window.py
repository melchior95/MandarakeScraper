"""
Image comparison window for viewing side-by-side images from alerts.

Displays store and eBay images side by side for visual comparison.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
import logging
from pathlib import Path


class ImageComparisonWindow:
    """Window to display side-by-side image comparison."""

    def __init__(self, parent, alert_data: dict):
        """
        Initialize image comparison window.

        Args:
            parent: Parent widget
            alert_data: Alert dictionary with image URLs and metadata
        """
        self.window = tk.Toplevel(parent)
        self.alert_data = alert_data

        # Window configuration
        store_title = alert_data.get('store_title', 'Unknown Item')
        self.window.title(f"Image Comparison - {store_title[:50]}")
        self.window.geometry("900x600")

        # Load and display images
        self._build_ui()

    def _build_ui(self):
        """Build the UI with side-by-side images."""
        # Top info frame
        info_frame = ttk.Frame(self.window, padding=10)
        info_frame.pack(fill=tk.X)

        # Alert metadata
        similarity = self.alert_data.get('similarity', 0)
        profit = self.alert_data.get('profit_margin', 0)
        store_price = self.alert_data.get('store_price', '')
        ebay_price = self.alert_data.get('ebay_price', '')

        info_text = (
            f"Similarity: {similarity:.1f}% | "
            f"Profit: {profit:.1f}% | "
            f"Store: {store_price} → eBay: {ebay_price}"
        )
        ttk.Label(info_frame, text=info_text, font=('TkDefaultFont', 10, 'bold')).pack()

        # Separator
        ttk.Separator(self.window, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # Image comparison frame
        images_frame = ttk.Frame(self.window, padding=10)
        images_frame.pack(fill=tk.BOTH, expand=True)

        # Left: Store image
        store_frame = ttk.LabelFrame(images_frame, text="Store Item", padding=10)
        store_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        store_title = self.alert_data.get('store_title', 'N/A')
        ttk.Label(store_frame, text=store_title, wraplength=380, justify='left').pack(pady=5)

        self.store_image_label = ttk.Label(store_frame)
        self.store_image_label.pack(fill=tk.BOTH, expand=True)

        # Right: eBay image
        ebay_frame = ttk.LabelFrame(images_frame, text="eBay Sold Listing", padding=10)
        ebay_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        ebay_title = self.alert_data.get('ebay_title', 'N/A')
        ttk.Label(ebay_frame, text=ebay_title, wraplength=380, justify='left').pack(pady=5)

        self.ebay_image_label = ttk.Label(ebay_frame)
        self.ebay_image_label.pack(fill=tk.BOTH, expand=True)

        # Bottom buttons
        button_frame = ttk.Frame(self.window, padding=10)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="Open Store Link", command=self._open_store_link).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Open eBay Link", command=self._open_ebay_link).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=self.window.destroy).pack(side=tk.RIGHT, padx=5)

        # Load images
        self._load_images()

    def _load_images(self):
        """Load and display images from URLs or local paths."""
        import requests
        from io import BytesIO
        from PIL import Image, ImageTk

        # Load store image (Mandarake)
        store_image_url = self.alert_data.get('store_thumbnail', '')

        if store_image_url:
            try:
                # Try as local file first
                if Path(store_image_url).exists():
                    img = Image.open(store_image_url)
                else:
                    # Download from URL
                    response = requests.get(store_image_url, timeout=10)
                    if response.status_code == 200:
                        img = Image.open(BytesIO(response.content))
                    else:
                        raise Exception(f"HTTP {response.status_code}")

                # Resize to fit
                img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.store_image_label.config(image=photo)
                self.store_image_label.image = photo  # Keep reference
            except Exception as e:
                logging.error(f"Failed to load store image: {e}")
                self.store_image_label.config(text="[Image not available]")

        # Load eBay image (best match from comparison)
        ebay_image_url = self.alert_data.get('ebay_thumbnail', self.alert_data.get('thumbnail', ''))

        if ebay_image_url:
            try:
                # Try as local file first
                if Path(ebay_image_url).exists():
                    img = Image.open(ebay_image_url)
                else:
                    # Download from URL
                    response = requests.get(ebay_image_url, timeout=10)
                    if response.status_code == 200:
                        img = Image.open(BytesIO(response.content))
                    else:
                        raise Exception(f"HTTP {response.status_code}")

                # Resize to fit
                img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.ebay_image_label.config(image=photo)
                self.ebay_image_label.image = photo  # Keep reference
            except Exception as e:
                logging.error(f"Failed to load eBay image: {e}")
                self.ebay_image_label.config(text="[Image not available]")

    def _open_store_link(self):
        """Open store link in browser."""
        import webbrowser
        link = self.alert_data.get('store_link', '')
        if link:
            webbrowser.open(link)

    def _open_ebay_link(self):
        """Open eBay link in browser."""
        import webbrowser
        link = self.alert_data.get('ebay_link', '')
        if link:
            webbrowser.open(link)
