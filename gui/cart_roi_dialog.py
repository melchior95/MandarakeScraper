"""
Cart ROI Verification Dialog

Shows ROI verification results with detailed breakdown and recommendations.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict
import logging


class CartROIDialog(tk.Toplevel):
    """
    Dialog for verifying cart ROI

    Allows user to select verification method (text, image, hybrid)
    and displays results with recommendations.
    """

    def __init__(self, parent, cart_manager):
        super().__init__(parent)
        self.cart_manager = cart_manager
        self.logger = logging.getLogger(__name__)

        self.title("Verify Cart ROI")
        self.geometry("800x600")

        # Verification result
        self.verification_result = None

        self._create_ui()

        # Position at cursor
        from gui.ui_helpers import position_dialog_at_cursor
        position_dialog_at_cursor(self)

    def _create_ui(self):
        """Create ROI verification UI"""

        # Options frame
        options_frame = ttk.LabelFrame(self, text="Verification Options", padding=10)
        options_frame.pack(fill=tk.X, padx=10, pady=10)

        # Method selection
        ttk.Label(options_frame, text="Method:").grid(row=0, column=0, sticky=tk.W)

        self.method_var = tk.StringVar(value='hybrid')
        methods = [
            ('hybrid', 'Hybrid (Text + Image, Recommended)'),
            ('text', 'Text Only (Fast, keyword matching)'),
            ('image', 'Image Only (Slow, accurate)')
        ]

        for i, (value, label) in enumerate(methods):
            ttk.Radiobutton(
                options_frame,
                text=label,
                variable=self.method_var,
                value=value
            ).grid(row=i, column=1, sticky=tk.W, pady=2)

        # Similarity threshold (for image/hybrid)
        ttk.Label(options_frame, text="Min Similarity %:").grid(row=3, column=0, sticky=tk.W, pady=(10, 0))
        self.similarity_var = tk.IntVar(value=70)
        ttk.Spinbox(
            options_frame,
            from_=50,
            to=95,
            textvariable=self.similarity_var,
            width=10
        ).grid(row=3, column=1, sticky=tk.W, pady=(10, 0))

        # RANSAC toggle
        self.ransac_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="Use RANSAC (slower, more accurate)",
            variable=self.ransac_var
        ).grid(row=4, column=1, sticky=tk.W, pady=5)

        # Action buttons
        button_frame = ttk.Frame(options_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=(10, 0))

        ttk.Button(
            button_frame,
            text="🔍 Start Verification",
            command=self._start_verification
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.destroy
        ).pack(side=tk.LEFT, padx=5)

        # Progress frame (hidden initially)
        self.progress_frame = ttk.LabelFrame(self, text="Progress", padding=10)

        self.progress_label = ttk.Label(self.progress_frame, text="Initializing...")
        self.progress_label.pack()

        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(pady=10)

        # Results frame (hidden initially)
        self.results_frame = ttk.LabelFrame(self, text="Verification Results", padding=10)

        # Summary labels
        self.summary_text = tk.Text(
            self.results_frame,
            height=6,
            width=70,
            wrap=tk.WORD,
            state='disabled',
            font=('TkDefaultFont', 10)
        )
        self.summary_text.pack(fill=tk.X, pady=5)

        # Items treeview
        columns = ('title', 'cost', 'ebay_price', 'profit', 'roi', 'similarity')
        self.items_tree = ttk.Treeview(
            self.results_frame,
            columns=columns,
            show='headings',
            height=15
        )

        self.items_tree.heading('title', text='Item')
        self.items_tree.heading('cost', text='Cost')
        self.items_tree.heading('ebay_price', text='eBay Price')
        self.items_tree.heading('profit', text='Profit')
        self.items_tree.heading('roi', text='ROI %')
        self.items_tree.heading('similarity', text='Similarity %')

        self.items_tree.column('title', width=250)
        self.items_tree.column('cost', width=80, anchor='e')
        self.items_tree.column('ebay_price', width=80, anchor='e')
        self.items_tree.column('profit', width=80, anchor='e')
        self.items_tree.column('roi', width=60, anchor='center')
        self.items_tree.column('similarity', width=80, anchor='center')

        scrollbar = ttk.Scrollbar(self.results_frame, orient=tk.VERTICAL, command=self.items_tree.yview)
        self.items_tree.configure(yscrollcommand=scrollbar.set)

        self.items_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Action buttons for results
        results_buttons = ttk.Frame(self.results_frame)
        results_buttons.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            results_buttons,
            text="📋 Copy Summary",
            command=self._copy_summary
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            results_buttons,
            text="🗑️ Remove Low ROI Items",
            command=self._remove_low_roi_items
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            results_buttons,
            text="✓ Close",
            command=self.destroy
        ).pack(side=tk.LEFT, padx=5)

    def _start_verification(self):
        """Start ROI verification process"""
        method = self.method_var.get()
        min_similarity = self.similarity_var.get()
        use_ransac = self.ransac_var.get()

        # Show progress
        self.progress_frame.pack(fill=tk.X, padx=10, pady=10)
        self.progress_bar['value'] = 0

        def progress_callback(current, total, message):
            """Update progress bar"""
            self.progress_label.config(text=message)
            self.progress_bar['value'] = (current / total) * 100
            self.update_idletasks()

        try:
            from gui.utils import fetch_exchange_rate
            exchange_rate = fetch_exchange_rate()

            result = self.cart_manager.verify_cart_roi(
                method=method,
                exchange_rate=exchange_rate,
                min_similarity=min_similarity,
                use_ransac=use_ransac,
                progress_callback=progress_callback
            )

            self.verification_result = result

            # Hide progress, show results
            self.progress_frame.pack_forget()
            self._display_results(result)

        except Exception as e:
            self.logger.error(f"ROI verification failed: {e}")
            messagebox.showerror("Error", f"Verification failed: {e}")
            self.progress_frame.pack_forget()

    def _display_results(self, result: Dict):
        """Display verification results"""
        self.results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Update summary
        total_cost_jpy = result.get('total_cost_jpy', 0)
        total_cost_usd = result.get('total_cost_usd', 0.0)
        est_revenue_usd = result.get('est_revenue_usd', 0.0)
        profit_usd = result.get('profit_usd', 0.0)
        roi_percent = result.get('roi_percent', 0.0)
        items_verified = result.get('items_verified', 0)
        items_no_match = result.get('items_no_match', 0)

        summary = f"""
Total Cost:     ¥{total_cost_jpy:,} (${total_cost_usd:.2f} USD)
Est. Revenue:   ${est_revenue_usd:.2f} USD (eBay average)
Profit:         ${profit_usd:.2f} USD
ROI:            {roi_percent:.1f}%

Items Verified: {items_verified}
No Match Found: {items_no_match}
        """.strip()

        self.summary_text.config(state='normal')
        self.summary_text.delete('1.0', 'end')
        self.summary_text.insert('1.0', summary)

        # Color code ROI
        if roi_percent >= 30:
            self.summary_text.tag_add('good_roi', '4.0', '4.end')
            self.summary_text.tag_config('good_roi', foreground='green', font=('TkDefaultFont', 10, 'bold'))
        elif roi_percent >= 15:
            self.summary_text.tag_add('ok_roi', '4.0', '4.end')
            self.summary_text.tag_config('ok_roi', foreground='orange', font=('TkDefaultFont', 10, 'bold'))
        else:
            self.summary_text.tag_add('bad_roi', '4.0', '4.end')
            self.summary_text.tag_config('bad_roi', foreground='red', font=('TkDefaultFont', 10, 'bold'))

        self.summary_text.config(state='disabled')

        # Update items tree
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)

        items = result.get('items', [])
        for item_data in items:
            title = item_data.get('title', 'Unknown')[:40]
            cost_jpy = item_data.get('cost_jpy', 0)
            ebay_price_usd = item_data.get('ebay_price_usd', 0.0)
            profit_usd = item_data.get('profit_usd', 0.0)
            roi = item_data.get('roi_percent', 0.0)
            similarity = item_data.get('similarity', 0.0)

            values = (
                title,
                f"¥{cost_jpy:,}",
                f"${ebay_price_usd:.2f}",
                f"${profit_usd:.2f}",
                f"{roi:.1f}%",
                f"{similarity:.1f}%" if similarity > 0 else "N/A"
            )

            item_id = self.items_tree.insert('', 'end', values=values)

            # Color code by ROI
            if roi >= 30:
                self.items_tree.item(item_id, tags=('good',))
            elif roi >= 15:
                self.items_tree.item(item_id, tags=('ok',))
            elif roi > 0:
                self.items_tree.item(item_id, tags=('poor',))
            else:
                self.items_tree.item(item_id, tags=('no_match',))

        # Configure tags
        self.items_tree.tag_configure('good', background='#d4edda')
        self.items_tree.tag_configure('ok', background='#fff3cd')
        self.items_tree.tag_configure('poor', background='#f8d7da')
        self.items_tree.tag_configure('no_match', background='#e2e3e5')

    def _copy_summary(self):
        """Copy summary to clipboard"""
        if self.verification_result:
            summary_text = self.summary_text.get('1.0', 'end-1c')
            self.clipboard_clear()
            self.clipboard_append(summary_text)
            messagebox.showinfo("Success", "Summary copied to clipboard!")

    def _remove_low_roi_items(self):
        """Remove items with low ROI from cart"""
        # TODO: Implement remove from cart functionality
        messagebox.showinfo("Not Implemented", "Remove from cart functionality coming soon!")
