"""
Advanced Tools Module

Handles category optimization, price validation, search optimization,
and other advanced analytical tools.
"""

import os
import json
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import threading
import re
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, defaultdict
import statistics


class AdvancedTools:
    """Manages advanced analytical and optimization tools."""
    
    def __init__(self, gui_instance):
        """
        Initialize the advanced tools manager.
        
        Args:
            gui_instance: The main GUI instance for accessing widgets and state
        """
        self.gui = gui_instance
        self.category_data = {}
        self.price_history = []
        self.optimization_profiles = {}
        
        # Load optimization data
        self._load_optimization_data()
    
    def _load_optimization_data(self):
        """Load optimization data from files."""
        try:
            # Load category data
            category_file = 'category_optimization.json'
            if os.path.exists(category_file):
                with open(category_file, 'r', encoding='utf-8') as f:
                    self.category_data = json.load(f)
            
            # Load price history
            price_file = 'price_history.json'
            if os.path.exists(price_file):
                with open(price_file, 'r', encoding='utf-8') as f:
                    self.price_history = json.load(f)
            
            # Load optimization profiles
            profiles_file = 'optimization_profiles.json'
            if os.path.exists(profiles_file):
                with open(profiles_file, 'r', encoding='utf-8') as f:
                    self.optimization_profiles = json.load(f)
                    
        except Exception as e:
            print(f"Failed to load optimization data: {e}")
    
    def _save_optimization_data(self):
        """Save optimization data to files."""
        try:
            # Save category data
            with open('category_optimization.json', 'w', encoding='utf-8') as f:
                json.dump(self.category_data, f, indent=2, ensure_ascii=False)
            
            # Save price history
            with open('price_history.json', 'w', encoding='utf-8') as f:
                json.dump(self.price_history, f, indent=2, ensure_ascii=False)
            
            # Save optimization profiles
            with open('optimization_profiles.json', 'w', encoding='utf-8') as f:
                json.dump(self.optimization_profiles, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save optimization data: {str(e)}")
    
    def show_category_optimizer(self):
        """Show category optimization dialog."""
        dialog = tk.Toplevel(self.gui.root)
        dialog.title("Category Optimizer")
        dialog.geometry("700x500")
        dialog.transient(self.gui.root)
        dialog.grab_set()
        
        # Create notebook for different optimization tools
        notebook = tk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Category analysis tab
        analysis_frame = tk.Frame(notebook)
        notebook.add(analysis_frame, text="Category Analysis")
        
        self._create_category_analysis_tab(analysis_frame)
        
        # Category optimization tab
        optimization_frame = tk.Frame(notebook)
        notebook.add(optimization_frame, text="Category Optimization")
        
        self._create_category_optimization_tab(optimization_frame)
        
        # Category comparison tab
        comparison_frame = tk.Frame(notebook)
        notebook.add(comparison_frame, text="Category Comparison")
        
        self._create_category_comparison_tab(comparison_frame)
        
        # Close button
        tk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
    
    def _create_category_analysis_tab(self, parent):
        """Create category analysis tab."""
        # Input frame
        input_frame = tk.Frame(parent)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(input_frame, text="Search Term:").pack(side=tk.LEFT, padx=5)
        search_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=search_var, width=30).pack(side=tk.LEFT, padx=5)
        
        tk.Button(input_frame, text="Analyze Categories", 
                 command=lambda: self._analyze_categories(search_var.get())).pack(side=tk.LEFT, padx=5)
        
        # Results frame
        results_frame = tk.Frame(parent)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create treeview for results
        columns = ('category', 'item_count', 'avg_price', 'price_range', 'success_rate')
        tree = ttk.Treeview(results_frame, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col.replace('_', ' ').title())
            tree.column(col, width=120)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Store tree reference for later use
        parent.category_tree = tree
    
    def _create_category_optimization_tab(self, parent):
        """Create category optimization tab."""
        # Input frame
        input_frame = tk.Frame(parent)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(input_frame, text="Search Term:").pack(side=tk.LEFT, padx=5)
        search_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=search_var, width=30).pack(side=tk.LEFT, padx=5)
        
        tk.Button(input_frame, text="Optimize Categories", 
                 command=lambda: self._optimize_categories(search_var.get())).pack(side=tk.LEFT, padx=5)
        
        # Options frame
        options_frame = tk.Frame(parent)
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(options_frame, text="Optimization Goal:").pack(side=tk.LEFT, padx=5)
        
        goal_var = tk.StringVar(value="best_price")
        goals = [("Best Price", "best_price"), ("Most Results", "most_results"), ("Balanced", "balanced")]
        
        for text, value in goals:
            tk.Radiobutton(options_frame, text=text, variable=goal_var, value=value).pack(side=tk.LEFT, padx=5)
        
        # Results frame
        results_frame = tk.Frame(parent)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Results text
        results_text = tk.Text(results_frame, wrap=tk.WORD, height=15)
        results_scroll = tk.Scrollbar(results_frame, command=results_text.yview)
        results_text.configure(yscrollcommand=results_scroll.set)
        
        results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Store references
        parent.search_var = search_var
        parent.goal_var = goal_var
        parent.results_text = results_text
    
    def _create_category_comparison_tab(self, parent):
        """Create category comparison tab."""
        # Input frame
        input_frame = tk.Frame(parent)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(input_frame, text="Categories to Compare (comma-separated):").pack(side=tk.LEFT, padx=5)
        categories_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=categories_var, width=40).pack(side=tk.LEFT, padx=5)
        
        tk.Button(input_frame, text="Compare", 
                 command=lambda: self._compare_categories(categories_var.get())).pack(side=tk.LEFT, padx=5)
        
        # Results frame
        results_frame = tk.Frame(parent)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create treeview for comparison
        columns = ('category', 'item_count', 'avg_price', 'min_price', 'max_price', 'price_trend')
        tree = ttk.Treeview(results_frame, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col.replace('_', ' ').title())
            tree.column(col, width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Store tree reference
        parent.comparison_tree = tree
    
    def _analyze_categories(self, search_term: str):
        """Analyze categories for a search term."""
        if not search_term:
            messagebox.showwarning("Warning", "Please enter a search term")
            return
        
        # Start analysis in separate thread
        thread = threading.Thread(
            target=self._analyze_categories_worker,
            args=(search_term,),
            daemon=True
        )
        thread.start()
    
    def _analyze_categories_worker(self, search_term: str):
        """Worker thread for category analysis."""
        try:
            self.gui.after(0, lambda: self.gui.status_var.set("Analyzing categories..."))
            
            # Simulate category analysis
            # In a real implementation, this would query the actual stores
            categories = self._simulate_category_analysis(search_term)
            
            # Update GUI in main thread
            self.gui.after(0, lambda: self._display_category_analysis(categories))
            self.gui.after(0, lambda: self.gui.status_var.set("Category analysis complete"))
            
        except Exception as e:
            error_msg = f"Category analysis failed: {str(e)}"
            self.gui.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.gui.after(0, lambda: self.gui.status_var.set("Category analysis failed"))
    
    def _simulate_category_analysis(self, search_term: str) -> List[Dict]:
        """Simulate category analysis (placeholder)."""
        # This would be replaced with actual category analysis logic
        categories = [
            {
                'category': 'Books',
                'item_count': 150,
                'avg_price': 2500,
                'price_range': '¥500 - ¥15,000',
                'success_rate': 85
            },
            {
                'category': 'Merchandise',
                'item_count': 75,
                'avg_price': 3500,
                'price_range': '¥1,000 - ¥25,000',
                'success_rate': 72
            },
            {
                'category': 'Media',
                'item_count': 45,
                'avg_price': 1800,
                'price_range': '¥300 - ¥8,000',
                'success_rate': 90
            }
        ]
        
        return categories
    
    def _display_category_analysis(self, categories: List[Dict]):
        """Display category analysis results."""
        # Find the category analysis dialog
        for widget in self.gui.root.winfo_children():
            if isinstance(widget, tk.Toplevel) and "Category Optimizer" in widget.title():
                # Find the analysis tab
                notebook = None
                for child in widget.winfo_children():
                    if isinstance(child, tk.Notebook):
                        notebook = child
                        break
                
                if notebook:
                    # Get the analysis tab
                    analysis_frame = notebook.winfo_children()[0]
                    if hasattr(analysis_frame, 'category_tree'):
                        tree = analysis_frame.category_tree
                        
                        # Clear existing items
                        for item in tree.get_children():
                            tree.delete(item)
                        
                        # Add new items
                        for category in categories:
                            tree.insert('', 'end', values=(
                                category['category'],
                                category['item_count'],
                                f"¥{category['avg_price']:,.0f}",
                                category['price_range'],
                                f"{category['success_rate']}%"
                            ))
                break
    
    def _optimize_categories(self, search_term: str):
        """Optimize categories for a search term."""
        if not search_term:
            messagebox.showwarning("Warning", "Please enter a search term")
            return
        
        # Start optimization in separate thread
        thread = threading.Thread(
            target=self._optimize_categories_worker,
            args=(search_term,),
            daemon=True
        )
        thread.start()
    
    def _optimize_categories_worker(self, search_term: str):
        """Worker thread for category optimization."""
        try:
            self.gui.after(0, lambda: self.gui.status_var.set("Optimizing categories..."))
            
            # Simulate category optimization
            recommendations = self._simulate_category_optimization(search_term)
            
            # Update GUI in main thread
            self.gui.after(0, lambda: self._display_category_optimization(recommendations))
            self.gui.after(0, lambda: self.gui.status_var.set("Category optimization complete"))
            
        except Exception as e:
            error_msg = f"Category optimization failed: {str(e)}"
            self.gui.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.gui.after(0, lambda: self.gui.status_var.set("Category optimization failed"))
    
    def _simulate_category_optimization(self, search_term: str) -> Dict[str, Any]:
        """Simulate category optimization (placeholder)."""
        return {
            'search_term': search_term,
            'recommendations': [
                {
                    'category': 'Books',
                    'reason': 'Highest item count and good success rate',
                    'confidence': 85,
                    'expected_results': 150,
                    'avg_price': 2500
                },
                {
                    'category': 'Media',
                    'reason': 'Best success rate and lowest average price',
                    'confidence': 78,
                    'expected_results': 45,
                    'avg_price': 1800
                }
            ],
            'optimization_tips': [
                "Consider searching in 'Books' category for maximum results",
                "Use 'Media' category for better success rate",
                "Combine categories for comprehensive coverage"
            ]
        }
    
    def _display_category_optimization(self, recommendations: Dict[str, Any]):
        """Display category optimization results."""
        # Find the category optimization dialog
        for widget in self.gui.root.winfo_children():
            if isinstance(widget, tk.Toplevel) and "Category Optimizer" in widget.title():
                # Find the optimization tab
                notebook = None
                for child in widget.winfo_children():
                    if isinstance(child, tk.Notebook):
                        notebook = child
                        break
                
                if notebook:
                    # Get the optimization tab
                    optimization_frame = notebook.winfo_children()[1]
                    if hasattr(optimization_frame, 'results_text'):
                        text_widget = optimization_frame.results_text
                        
                        # Clear existing content
                        text_widget.delete(1.0, tk.END)
                        
                        # Add recommendations
                        text_widget.insert(tk.END, f"Category Optimization for: {recommendations['search_term']}\n")
                        text_widget.insert(tk.END, "=" * 50 + "\n\n")
                        
                        for i, rec in enumerate(recommendations['recommendations'], 1):
                            text_widget.insert(tk.END, f"{i}. {rec['category']}\n")
                            text_widget.insert(tk.END, f"   Reason: {rec['reason']}\n")
                            text_widget.insert(tk.END, f"   Confidence: {rec['confidence']}%\n")
                            text_widget.insert(tk.END, f"   Expected Results: {rec['expected_results']}\n")
                            text_widget.insert(tk.END, f"   Average Price: ¥{rec['avg_price']:,.0f}\n\n")
                        
                        text_widget.insert(tk.END, "Optimization Tips:\n")
                        text_widget.insert(tk.END, "-" * 20 + "\n")
                        
                        for tip in recommendations['optimization_tips']:
                            text_widget.insert(tk.END, f"• {tip}\n")
                break
    
    def _compare_categories(self, categories_str: str):
        """Compare multiple categories."""
        if not categories_str:
            messagebox.showwarning("Warning", "Please enter categories to compare")
            return
        
        categories = [cat.strip() for cat in categories_str.split(',') if cat.strip()]
        
        if len(categories) < 2:
            messagebox.showwarning("Warning", "Please enter at least 2 categories to compare")
            return
        
        # Start comparison in separate thread
        thread = threading.Thread(
            target=self._compare_categories_worker,
            args=(categories,),
            daemon=True
        )
        thread.start()
    
    def _compare_categories_worker(self, categories: List[str]):
        """Worker thread for category comparison."""
        try:
            self.gui.after(0, lambda: self.gui.status_var.set("Comparing categories..."))
            
            # Simulate category comparison
            comparison_data = self._simulate_category_comparison(categories)
            
            # Update GUI in main thread
            self.gui.after(0, lambda: self._display_category_comparison(comparison_data))
            self.gui.after(0, lambda: self.gui.status_var.set("Category comparison complete"))
            
        except Exception as e:
            error_msg = f"Category comparison failed: {str(e)}"
            self.gui.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.gui.after(0, lambda: self.gui.status_var.set("Category comparison failed"))
    
    def _simulate_category_comparison(self, categories: List[str]) -> List[Dict]:
        """Simulate category comparison (placeholder)."""
        comparison_data = []
        
        for category in categories:
            # Generate mock data for each category
            comparison_data.append({
                'category': category,
                'item_count': len(category) * 25 + 50,  # Mock calculation
                'avg_price': len(category) * 300 + 1000,
                'min_price': 500,
                'max_price': len(category) * 1000 + 5000,
                'price_trend': 'Stable' if len(category) % 2 == 0 else 'Rising'
            })
        
        return comparison_data
    
    def _display_category_comparison(self, comparison_data: List[Dict]):
        """Display category comparison results."""
        # Find the category optimization dialog
        for widget in self.gui.root.winfo_children():
            if isinstance(widget, tk.Toplevel) and "Category Optimizer" in widget.title():
                # Find the comparison tab
                notebook = None
                for child in widget.winfo_children():
                    if isinstance(child, tk.Notebook):
                        notebook = child
                        break
                
                if notebook:
                    # Get the comparison tab
                    comparison_frame = notebook.winfo_children()[2]
                    if hasattr(comparison_frame, 'comparison_tree'):
                        tree = comparison_frame.comparison_tree
                        
                        # Clear existing items
                        for item in tree.get_children():
                            tree.delete(item)
                        
                        # Add new items
                        for data in comparison_data:
                            tree.insert('', 'end', values=(
                                data['category'],
                                data['item_count'],
                                f"¥{data['avg_price']:,.0f}",
                                f"¥{data['min_price']:,.0f}",
                                f"¥{data['max_price']:,.0f}",
                                data['price_trend']
                            ))
                break
    
    def show_price_validator(self):
        """Show price validation dialog."""
        dialog = tk.Toplevel(self.gui.root)
        dialog.title("Price Validator")
        dialog.geometry("600x400")
        dialog.transient(self.gui.root)
        dialog.grab_set()
        
        # Input frame
        input_frame = tk.Frame(dialog)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(input_frame, text="Price to Validate:").pack(side=tk.LEFT, padx=5)
        price_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=price_var, width=15).pack(side=tk.LEFT, padx=5)
        
        tk.Label(input_frame, text="Item Category:").pack(side=tk.LEFT, padx=5)
        category_var = tk.StringVar()
        category_combo = ttk.Combobox(input_frame, textvariable=category_var, width=20)
        category_combo['values'] = ['Books', 'Merchandise', 'Media', 'Games', 'Other']
        category_combo.pack(side=tk.LEFT, padx=5)
        
        tk.Button(input_frame, text="Validate", 
                 command=lambda: self._validate_price(price_var.get(), category_var.get())).pack(side=tk.LEFT, padx=5)
        
        # Results frame
        results_frame = tk.Frame(dialog)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Results text
        results_text = tk.Text(results_frame, wrap=tk.WORD, height=15)
        results_scroll = tk.Scrollbar(results_frame, command=results_text.yview)
        results_text.configure(yscrollcommand=results_scroll.set)
        
        results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Store reference
        dialog.results_text = results_text
    
    def _validate_price(self, price_str: str, category: str):
        """Validate a price against historical data."""
        try:
            price = float(price_str.replace('¥', '').replace(',', '').strip())
        except ValueError:
            messagebox.showwarning("Warning", "Invalid price format")
            return
        
        if not category:
            messagebox.showwarning("Warning", "Please select a category")
            return
        
        # Start validation in separate thread
        thread = threading.Thread(
            target=self._validate_price_worker,
            args=(price, category),
            daemon=True
        )
        thread.start()
    
    def _validate_price_worker(self, price: float, category: str):
        """Worker thread for price validation."""
        try:
            self.gui.after(0, lambda: self.gui.status_var.set("Validating price..."))
            
            # Get price statistics for category
            stats = self._get_price_statistics(category)
            
            # Validate price
            validation_result = self._analyze_price_validation(price, stats)
            
            # Update GUI in main thread
            self.gui.after(0, lambda: self._display_price_validation(validation_result))
            self.gui.after(0, lambda: self.gui.status_var.set("Price validation complete"))
            
        except Exception as e:
            error_msg = f"Price validation failed: {str(e)}"
            self.gui.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.gui.after(0, lambda: self.gui.status_var.set("Price validation failed"))
    
    def _get_price_statistics(self, category: str) -> Dict[str, float]:
        """Get price statistics for a category."""
        # In a real implementation, this would use historical data
        # For now, return mock statistics
        return {
            'min_price': 500,
            'max_price': 15000,
            'avg_price': 2500,
            'median_price': 2000,
            'std_dev': 800
        }
    
    def _analyze_price_validation(self, price: float, stats: Dict[str, float]) -> Dict[str, Any]:
        """Analyze price validation results."""
        # Calculate z-score
        z_score = (price - stats['avg_price']) / stats['std_dev']
        
        # Determine price category
        if price < stats['min_price']:
            price_category = "Below Minimum"
            recommendation = "This price seems too low - possible scam or error"
        elif price > stats['max_price']:
            price_category = "Above Maximum"
            recommendation = "This price seems unusually high - verify authenticity"
        elif abs(z_score) <= 1:
            price_category = "Normal Range"
            recommendation = "Price is within normal range"
        elif abs(z_score) <= 2:
            price_category = "Slightly Unusual"
            recommendation = "Price is somewhat unusual but reasonable"
        else:
            price_category = "Very Unusual"
            recommendation = "Price is very unusual - exercise caution"
        
        return {
            'price': price,
            'price_category': price_category,
            'z_score': z_score,
            'percentile': self._calculate_percentile(price, stats),
            'recommendation': recommendation,
            'statistics': stats
        }
    
    def _calculate_percentile(self, price: float, stats: Dict[str, float]) -> float:
        """Calculate price percentile (simplified)."""
        # This is a simplified calculation
        # In a real implementation, you'd use actual distribution data
        if price <= stats['min_price']:
            return 0.0
        elif price >= stats['max_price']:
            return 100.0
        else:
            return ((price - stats['min_price']) / (stats['max_price'] - stats['min_price'])) * 100
    
    def _display_price_validation(self, validation_result: Dict[str, Any]):
        """Display price validation results."""
        # Find the price validation dialog
        for widget in self.gui.root.winfo_children():
            if isinstance(widget, tk.Toplevel) and "Price Validator" in widget.title():
                if hasattr(widget, 'results_text'):
                    text_widget = widget.results_text
                    
                    # Clear existing content
                    text_widget.delete(1.0, tk.END)
                    
                    # Display results
                    text_widget.insert(tk.END, f"Price Validation Results\n")
                    text_widget.insert(tk.END, "=" * 30 + "\n\n")
                    
                    text_widget.insert(tk.END, f"Price: ¥{validation_result['price']:,.0f}\n")
                    text_widget.insert(tk.END, f"Category: {validation_result['price_category']}\n")
                    text_widget.insert(tk.END, f"Z-Score: {validation_result['z_score']:.2f}\n")
                    text_widget.insert(tk.END, f"Percentile: {validation_result['percentile']:.1f}%\n\n")
                    
                    text_widget.insert(tk.END, f"Recommendation:\n")
                    text_widget.insert(tk.END, f"{validation_result['recommendation']}\n\n")
                    
                    text_widget.insert(tk.END, f"Category Statistics:\n")
                    text_widget.insert(tk.END, f"- Average: ¥{validation_result['statistics']['avg_price']:,.0f}\n")
                    text_widget.insert(tk.END, f"- Median: ¥{validation_result['statistics']['median_price']:,.0f}\n")
                    text_widget.insert(tk.END, f"- Range: ¥{validation_result['statistics']['min_price']:,.0f} - ¥{validation_result['statistics']['max_price']:,.0f}\n")
                break
    
    def show_search_optimizer(self):
        """Show search optimization dialog."""
        dialog = tk.Toplevel(self.gui.root)
        dialog.title("Search Optimizer")
        dialog.geometry("500x400")
        dialog.transient(self.gui.root)
        dialog.grab_set()
        
        # Input frame
        input_frame = tk.Frame(dialog)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(input_frame, text="Search Term:").pack(side=tk.LEFT, padx=5)
        search_var = tk.StringVar(value=self.gui.keyword_var.get())
        tk.Entry(input_frame, textvariable=search_var, width=30).pack(side=tk.LEFT, padx=5)
        
        tk.Button(input_frame, text="Optimize", 
                 command=lambda: self._optimize_search(search_var.get())).pack(side=tk.LEFT, padx=5)
        
        # Results frame
        results_frame = tk.Frame(dialog)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Results text
        results_text = tk.Text(results_frame, wrap=tk.WORD, height=15)
        results_scroll = tk.Scrollbar(results_frame, command=results_text.yview)
        results_text.configure(yscrollcommand=results_scroll.set)
        
        results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Store reference
        dialog.results_text = results_text
    
    def _optimize_search(self, search_term: str):
        """Optimize a search term."""
        if not search_term:
            messagebox.showwarning("Warning", "Please enter a search term")
            return
        
        # Start optimization in separate thread
        thread = threading.Thread(
            target=self._optimize_search_worker,
            args=(search_term,),
            daemon=True
        )
        thread.start()
    
    def _optimize_search_worker(self, search_term: str):
        """Worker thread for search optimization."""
        try:
            self.gui.after(0, lambda: self.gui.status_var.set("Optimizing search..."))
            
            # Analyze and optimize search term
            optimization_result = self._analyze_search_optimization(search_term)
            
            # Update GUI in main thread
            self.gui.after(0, lambda: self._display_search_optimization(optimization_result))
            self.gui.after(0, lambda: self.gui.status_var.set("Search optimization complete"))
            
        except Exception as e:
            error_msg = f"Search optimization failed: {str(e)}"
            self.gui.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.gui.after(0, lambda: self.gui.status_var.set("Search optimization failed"))
    
    def _analyze_search_optimization(self, search_term: str) -> Dict[str, Any]:
        """Analyze and optimize search term."""
        # Analyze search term
        words = search_term.split()
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        filtered_words = [word for word in words if word.lower() not in stop_words]
        
        # Generate alternative search terms
        alternatives = []
        
        # Original term
        alternatives.append(search_term)
        
        # Filtered term
        if filtered_words != words:
            alternatives.append(' '.join(filtered_words))
        
        # Japanese terms (if applicable)
        if any(re.search(r'[a-zA-Z]', word) for word in words):
            # Add Japanese variations if there are English words
            alternatives.append(f"{search_term} 日本語")
        
        # Category-specific terms
        category_suggestions = [
            f"{search_term} 本",  # book
            f"{search_term} グッズ",  # goods
            f"{search_term} CD",  # CD
            f"{search_term} DVD"  # DVD
        ]
        alternatives.extend(category_suggestions)
        
        # Remove duplicates
        alternatives = list(set(alternatives))
        
        return {
            'original_term': search_term,
            'filtered_term': ' '.join(filtered_words),
            'word_count': len(words),
            'filtered_word_count': len(filtered_words),
            'alternatives': alternatives[:5],  # Limit to 5 alternatives
            'suggestions': [
                "Use specific keywords for better results",
                "Include Japanese terms for Japanese items",
                "Try different category combinations",
                "Remove common words that don't add value"
            ]
        }
    
    def _display_search_optimization(self, optimization_result: Dict[str, Any]):
        """Display search optimization results."""
        # Find the search optimization dialog
        for widget in self.gui.root.winfo_children():
            if isinstance(widget, tk.Toplevel) and "Search Optimizer" in widget.title():
                if hasattr(widget, 'results_text'):
                    text_widget = widget.results_text
                    
                    # Clear existing content
                    text_widget.delete(1.0, tk.END)
                    
                    # Display results
                    text_widget.insert(tk.END, f"Search Optimization Results\n")
                    text_widget.insert(tk.END, "=" * 30 + "\n\n")
                    
                    text_widget.insert(tk.END, f"Original Term: {optimization_result['original_term']}\n")
                    text_widget.insert(tk.END, f"Word Count: {optimization_result['word_count']}\n")
                    text_widget.insert(tk.END, f"Filtered Term: {optimization_result['filtered_term']}\n")
                    text_widget.insert(tk.END, f"Filtered Word Count: {optimization_result['filtered_word_count']}\n\n")
                    
                    text_widget.insert(tk.END, f"Alternative Search Terms:\n")
                    text_widget.insert(tk.END, "-" * 25 + "\n")
                    
                    for i, alt in enumerate(optimization_result['alternatives'], 1):
                        text_widget.insert(tk.END, f"{i}. {alt}\n")
                    
                    text_widget.insert(tk.END, f"\nSuggestions:\n")
                    text_widget.insert(tk.END, "-" * 15 + "\n")
                    
                    for suggestion in optimization_result['suggestions']:
                        text_widget.insert(tk.END, f"• {suggestion}\n")
                break
    
    def get_tool_statistics(self) -> Dict[str, Any]:
        """Get statistics about advanced tools usage."""
        return {
            'category_data_count': len(self.category_data),
            'price_history_count': len(self.price_history),
            'optimization_profiles_count': len(self.optimization_profiles),
            'last_updated': tk.datetime.datetime.now().isoformat()
        }
