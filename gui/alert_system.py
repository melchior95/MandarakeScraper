"""
Alert System Module

Handles notification management, scheduling, alert configuration,
and automated monitoring functionality.
"""

import os
import json
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
import schedule
from dataclasses import dataclass, asdict


@dataclass
class Alert:
    """Data class for alert configuration."""
    id: str
    name: str
    search_term: str
    store: str
    categories: List[str]
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    keywords: List[str] = None
    exclude_keywords: List[str] = None
    enabled: bool = True
    notification_method: str = "desktop"  # desktop, email, file
    check_interval: int = 60  # minutes
    last_check: Optional[str] = None
    last_results: List[Dict] = None
    created_at: str = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.exclude_keywords is None:
            self.exclude_keywords = []
        if self.last_results is None:
            self.last_results = []
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class AlertSystem:
    """Manages alerts, notifications, and automated monitoring."""
    
    def __init__(self, gui_instance):
        """
        Initialize the alert system.
        
        Args:
            gui_instance: The main GUI instance for accessing widgets and state
        """
        self.gui = gui_instance
        self.alerts: Dict[str, Alert] = {}
        self.scheduler_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        
        # Alert configuration file
        self.alerts_file = 'alerts.json'
        
        # Load existing alerts
        self._load_alerts()
        
        # Start scheduler if there are enabled alerts
        if self._has_enabled_alerts():
            self.start_scheduler()
    
    def _load_alerts(self):
        """Load alerts from configuration file."""
        try:
            if os.path.exists(self.alerts_file):
                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    for alert_data in data.get('alerts', []):
                        alert = Alert(**alert_data)
                        self.alerts[alert.id] = alert
                        
        except Exception as e:
            print(f"Failed to load alerts: {e}")
            self.alerts = {}
    
    def _save_alerts(self):
        """Save alerts to configuration file."""
        try:
            data = {
                'alerts': [asdict(alert) for alert in self.alerts.values()],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.alerts_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save alerts: {str(e)}")
    
    def _has_enabled_alerts(self) -> bool:
        """Check if there are any enabled alerts."""
        return any(alert.enabled for alert in self.alerts.values())
    
    def create_alert_dialog(self):
        """Show dialog to create a new alert."""
        dialog = tk.Toplevel(self.gui.root)
        dialog.title("Create New Alert")
        dialog.geometry("500x600")
        dialog.transient(self.gui.root)
        dialog.grab_set()
        
        # Alert name
        tk.Label(dialog, text="Alert Name:").pack(pady=5)
        name_var = tk.StringVar()
        tk.Entry(dialog, textvariable=name_var, width=50).pack(pady=5)
        
        # Search term
        tk.Label(dialog, text="Search Term:").pack(pady=5)
        search_var = tk.StringVar(value=self.gui.keyword_var.get())
        tk.Entry(dialog, textvariable=search_var, width=50).pack(pady=5)
        
        # Store selection
        tk.Label(dialog, text="Store:").pack(pady=5)
        store_var = tk.StringVar(value=self.gui.current_store.get())
        store_frame = tk.Frame(dialog)
        store_frame.pack(pady=5)
        
        stores = ['Mandarake', 'Suruga-ya']
        for store in stores:
            tk.Radiobutton(store_frame, text=store, variable=store_var, 
                          value=store).pack(side=tk.LEFT, padx=10)
        
        # Categories
        tk.Label(dialog, text="Categories (comma-separated):").pack(pady=5)
        categories_var = tk.StringVar()
        categories_entry = tk.Entry(dialog, textvariable=categories_var, width=50)
        categories_entry.pack(pady=5)
        
        # Price range
        price_frame = tk.Frame(dialog)
        price_frame.pack(pady=10)
        
        tk.Label(price_frame, text="Price Range:").pack(side=tk.LEFT, padx=5)
        
        tk.Label(price_frame, text="Min:").pack(side=tk.LEFT, padx=2)
        min_price_var = tk.StringVar()
        tk.Entry(price_frame, textvariable=min_price_var, width=10).pack(side=tk.LEFT, padx=2)
        
        tk.Label(price_frame, text="Max:").pack(side=tk.LEFT, padx=2)
        max_price_var = tk.StringVar()
        tk.Entry(price_frame, textvariable=max_price_var, width=10).pack(side=tk.LEFT, padx=2)
        
        # Keywords
        tk.Label(dialog, text="Include Keywords (comma-separated):").pack(pady=5)
        include_var = tk.StringVar()
        tk.Entry(dialog, textvariable=include_var, width=50).pack(pady=5)
        
        tk.Label(dialog, text="Exclude Keywords (comma-separated):").pack(pady=5)
        exclude_var = tk.StringVar()
        tk.Entry(dialog, textvariable=exclude_var, width=50).pack(pady=5)
        
        # Notification method
        tk.Label(dialog, text="Notification Method:").pack(pady=5)
        notification_var = tk.StringVar(value="desktop")
        notification_frame = tk.Frame(dialog)
        notification_frame.pack(pady=5)
        
        methods = [("Desktop", "desktop"), ("Email", "email"), ("File", "file")]
        for text, value in methods:
            tk.Radiobutton(notification_frame, text=text, variable=notification_var,
                          value=value).pack(side=tk.LEFT, padx=10)
        
        # Check interval
        tk.Label(dialog, text="Check Interval (minutes):").pack(pady=5)
        interval_var = tk.StringVar(value="60")
        tk.Entry(dialog, textvariable=interval_var, width=10).pack(pady=5)
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=20)
        
        def create_alert():
            try:
                # Validate input
                name = name_var.get().strip()
                if not name:
                    messagebox.showwarning("Warning", "Please enter an alert name")
                    return
                
                search_term = search_var.get().strip()
                if not search_term:
                    messagebox.showwarning("Warning", "Please enter a search term")
                    return
                
                # Parse categories
                categories = [cat.strip() for cat in categories_var.get().split(',') if cat.strip()]
                
                # Parse prices
                min_price = None
                max_price = None
                
                if min_price_var.get().strip():
                    try:
                        min_price = float(min_price_var.get())
                    except ValueError:
                        messagebox.showwarning("Warning", "Invalid minimum price")
                        return
                
                if max_price_var.get().strip():
                    try:
                        max_price = float(max_price_var.get())
                    except ValueError:
                        messagebox.showwarning("Warning", "Invalid maximum price")
                        return
                
                # Parse keywords
                include_keywords = [kw.strip() for kw in include_var.get().split(',') if kw.strip()]
                exclude_keywords = [kw.strip() for kw in exclude_var.get().split(',') if kw.strip()]
                
                # Parse interval
                try:
                    interval = int(interval_var.get())
                    if interval < 1:
                        raise ValueError()
                except ValueError:
                    messagebox.showwarning("Warning", "Invalid check interval (minimum 1 minute)")
                    return
                
                # Create alert
                alert_id = f"alert_{int(time.time())}"
                alert = Alert(
                    id=alert_id,
                    name=name,
                    search_term=search_term,
                    store=store_var.get(),
                    categories=categories,
                    price_min=min_price,
                    price_max=max_price,
                    keywords=include_keywords,
                    exclude_keywords=exclude_keywords,
                    notification_method=notification_var.get(),
                    check_interval=interval
                )
                
                self.alerts[alert_id] = alert
                self._save_alerts()
                
                # Start scheduler if needed
                if alert.enabled and not self.scheduler_running:
                    self.start_scheduler()
                
                messagebox.showinfo("Success", f"Alert '{name}' created successfully")
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create alert: {str(e)}")
        
        tk.Button(button_frame, text="Create", command=create_alert).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def manage_alerts_dialog(self):
        """Show dialog to manage existing alerts."""
        dialog = tk.Toplevel(self.gui.root)
        dialog.title("Manage Alerts")
        dialog.geometry("800x500")
        dialog.transient(self.gui.root)
        dialog.grab_set()
        
        # Create main frame
        main_frame = tk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create treeview for alerts
        columns = ('name', 'search_term', 'store', 'interval', 'enabled', 'last_check')
        tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=15)
        
        # Define column headings
        tree.heading('name', text='Name')
        tree.heading('search_term', text='Search Term')
        tree.heading('store', text='Store')
        tree.heading('interval', text='Interval')
        tree.heading('enabled', text='Enabled')
        tree.heading('last_check', text='Last Check')
        
        # Configure column widths
        tree.column('name', width=150)
        tree.column('search_term', width=200)
        tree.column('store', width=80)
        tree.column('interval', width=80)
        tree.column('enabled', width=80)
        tree.column('last_check', width=120)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate tree
        self._populate_alerts_tree(tree)
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def toggle_alert():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Warning", "Please select an alert")
                return
            
            item_id = selection[0]
            alert_id = self._get_alert_id_from_tree(tree, item_id)
            
            if alert_id and alert_id in self.alerts:
                alert = self.alerts[alert_id]
                alert.enabled = not alert.enabled
                self._save_alerts()
                self._populate_alerts_tree(tree)
                
                # Update scheduler
                if alert.enabled and not self.scheduler_running:
                    self.start_scheduler()
                elif not alert.enabled and not self._has_enabled_alerts():
                    self.stop_scheduler()
        
        def edit_alert():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Warning", "Please select an alert")
                return
            
            item_id = selection[0]
            alert_id = self._get_alert_id_from_tree(tree, item_id)
            
            if alert_id and alert_id in self.alerts:
                self._edit_alert_dialog(alert_id, dialog)
        
        def delete_alert():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Warning", "Please select an alert")
                return
            
            item_id = selection[0]
            alert_id = self._get_alert_id_from_tree(tree, item_id)
            
            if alert_id and alert_id in self.alerts:
                alert = self.alerts[alert_id]
                
                if messagebox.askyesno("Confirm", f"Delete alert '{alert.name}'?"):
                    del self.alerts[alert_id]
                    self._save_alerts()
                    self._populate_alerts_tree(tree)
                    
                    # Update scheduler
                    if not self._has_enabled_alerts():
                        self.stop_scheduler()
        
        def run_alert_now():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Warning", "Please select an alert")
                return
            
            item_id = selection[0]
            alert_id = self._get_alert_id_from_tree(tree, item_id)
            
            if alert_id and alert_id in self.alerts:
                alert = self.alerts[alert_id]
                threading.Thread(target=self._check_alert, args=(alert,), daemon=True).start()
        
        tk.Button(button_frame, text="Toggle", command=toggle_alert).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="Edit", command=edit_alert).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="Delete", command=delete_alert).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="Run Now", command=run_alert_now).pack(side=tk.LEFT, padx=2)
        
        # Scheduler controls
        scheduler_frame = tk.Frame(button_frame)
        scheduler_frame.pack(side=tk.RIGHT)
        
        if self.scheduler_running:
            tk.Button(scheduler_frame, text="Stop Scheduler", command=self.stop_scheduler).pack(side=tk.LEFT, padx=2)
        else:
            tk.Button(scheduler_frame, text="Start Scheduler", command=self.start_scheduler).pack(side=tk.LEFT, padx=2)
        
        tk.Button(button_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT, padx=2)
    
    def _populate_alerts_tree(self, tree):
        """Populate the alerts tree with current alerts."""
        # Clear existing items
        for item in tree.get_children():
            tree.delete(item)
        
        # Add alerts
        for alert_id, alert in self.alerts.items():
            values = (
                alert.name,
                alert.search_term,
                alert.store,
                f"{alert.check_interval} min",
                "Yes" if alert.enabled else "No",
                alert.last_check or "Never"
            )
            
            item_id = tree.insert('', 'end', values=values)
            tree.set(item_id, 'alert_id', alert_id)
    
    def _get_alert_id_from_tree(self, tree, item_id) -> Optional[str]:
        """Get alert ID from tree item."""
        try:
            return tree.set(item_id, 'alert_id')
        except:
            return None
    
    def _edit_alert_dialog(self, alert_id: str, parent_dialog):
        """Show dialog to edit an existing alert."""
        if alert_id not in self.alerts:
            return
        
        alert = self.alerts[alert_id]
        
        dialog = tk.Toplevel(parent_dialog)
        dialog.title(f"Edit Alert: {alert.name}")
        dialog.geometry("500x600")
        dialog.transient(parent_dialog)
        dialog.grab_set()
        
        # Similar to create_alert_dialog but pre-populated with existing data
        # (Implementation would be similar to create_alert_dialog)
        
        # For now, show a simple message
        tk.Label(dialog, text=f"Edit functionality for alert '{alert.name}'\nwould be implemented here.").pack(pady=50)
        tk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=20)
    
    def start_scheduler(self):
        """Start the alert scheduler."""
        if self.scheduler_running:
            return
        
        self.scheduler_running = True
        
        # Schedule each enabled alert
        for alert in self.alerts.values():
            if alert.enabled:
                schedule.every(alert.check_interval).minutes.do(self._check_alert, alert)
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        print("Alert scheduler started")
    
    def stop_scheduler(self):
        """Stop the alert scheduler."""
        self.scheduler_running = False
        schedule.clear()
        print("Alert scheduler stopped")
    
    def _run_scheduler(self):
        """Run the scheduler loop."""
        while self.scheduler_running:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds
    
    def _check_alert(self, alert: Alert):
        """Check a single alert for new results."""
        try:
            print(f"Checking alert: {alert.name}")
            
            # Perform search based on alert configuration
            results = self._perform_alert_search(alert)
            
            # Filter results based on alert criteria
            filtered_results = self._filter_alert_results(alert, results)
            
            # Check for new results
            new_results = self._find_new_results(alert, filtered_results)
            
            if new_results:
                # Send notification
                self._send_notification(alert, new_results)
                
                # Update alert
                alert.last_results.extend(new_results)
                alert.last_check = datetime.now().isoformat()
                self._save_alerts()
            
        except Exception as e:
            print(f"Error checking alert {alert.name}: {e}")
    
    def _perform_alert_search(self, alert: Alert) -> List[Dict]:
        """
        Perform search for alert.
        
        Args:
            alert: Alert configuration
            
        Returns:
            List of search results
        """
        # This would integrate with the actual search functionality
        # For now, return empty list
        return []
    
    def _filter_alert_results(self, alert: Alert, results: List[Dict]) -> List[Dict]:
        """
        Filter results based on alert criteria.
        
        Args:
            alert: Alert configuration
            results: Raw search results
            
        Returns:
            Filtered results
        """
        filtered = []
        
        for result in results:
            # Price filtering
            price = result.get('price_numeric', 0)
            
            if alert.price_min and price < alert.price_min:
                continue
            
            if alert.price_max and price > alert.price_max:
                continue
            
            # Keyword filtering
            title = result.get('title', '').lower()
            
            # Must include at least one include keyword
            if alert.keywords:
                if not any(kw.lower() in title for kw in alert.keywords):
                    continue
            
            # Must not include any exclude keywords
            if alert.exclude_keywords:
                if any(kw.lower() in title for kw in alert.exclude_keywords):
                    continue
            
            filtered.append(result)
        
        return filtered
    
    def _find_new_results(self, alert: Alert, current_results: List[Dict]) -> List[Dict]:
        """
        Find new results that haven't been seen before.
        
        Args:
            alert: Alert configuration
            current_results: Current search results
            
        Returns:
            List of new results
        """
        new_results = []
        
        # Create set of existing result URLs or identifiers
        existing_urls = {result.get('url', '') for result in alert.last_results}
        
        for result in current_results:
            url = result.get('url', '')
            if url and url not in existing_urls:
                new_results.append(result)
        
        return new_results
    
    def _send_notification(self, alert: Alert, new_results: List[Dict]):
        """
        Send notification for new results.
        
        Args:
            alert: Alert configuration
            new_results: New results to notify about
        """
        if alert.notification_method == "desktop":
            self._send_desktop_notification(alert, new_results)
        elif alert.notification_method == "email":
            self._send_email_notification(alert, new_results)
        elif alert.notification_method == "file":
            self._send_file_notification(alert, new_results)
    
    def _send_desktop_notification(self, alert: Alert, new_results: List[Dict]):
        """Send desktop notification."""
        try:
            # Update GUI in main thread
            self.gui.after(0, lambda: self._show_desktop_notification(alert, new_results))
        except Exception as e:
            print(f"Failed to send desktop notification: {e}")
    
    def _show_desktop_notification(self, alert: Alert, new_results: List[Dict]):
        """Show desktop notification in GUI."""
        # Create notification dialog
        dialog = tk.Toplevel(self.gui.root)
        dialog.title(f"Alert: {alert.name}")
        dialog.geometry("600x400")
        dialog.transient(self.gui.root)
        
        # Alert info
        info_frame = tk.Frame(dialog)
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(info_frame, text=f"Alert: {alert.name}", font=('Arial', 12, 'bold')).pack()
        tk.Label(info_frame, text=f"Found {len(new_results)} new items").pack()
        
        # Results list
        results_frame = tk.Frame(dialog)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create treeview for results
        columns = ('title', 'price', 'store')
        tree = ttk.Treeview(results_frame, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col.title())
            tree.column(col, width=150)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate results
        for result in new_results:
            tree.insert('', 'end', values=(
                result.get('title', ''),
                result.get('price', ''),
                result.get('store', '')
            ))
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(button_frame, text="View Results", 
                 command=lambda: self._view_alert_results(alert, new_results)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Dismiss", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Auto-close after 30 seconds
        dialog.after(30000, dialog.destroy)
    
    def _view_alert_results(self, alert: Alert, results: List[Dict]):
        """View alert results in main interface."""
        # This would load the results into the main results display
        # Implementation would depend on the main GUI structure
        pass
    
    def _send_email_notification(self, alert: Alert, new_results: List[Dict]):
        """Send email notification (placeholder)."""
        print(f"Email notification for alert '{alert.name}': {len(new_results)} new items")
        # Email implementation would go here
    
    def _send_file_notification(self, alert: Alert, new_results: List[Dict]):
        """Save notification to file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"alert_{alert.id}_{timestamp}.json"
            
            notification_data = {
                'alert': asdict(alert),
                'timestamp': datetime.now().isoformat(),
                'new_results': new_results
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(notification_data, f, indent=2, ensure_ascii=False)
            
            print(f"Alert notification saved to {filename}")
            
        except Exception as e:
            print(f"Failed to save file notification: {e}")
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get statistics about alerts."""
        total_alerts = len(self.alerts)
        enabled_alerts = sum(1 for alert in self.alerts.values() if alert.enabled)
        
        return {
            'total_alerts': total_alerts,
            'enabled_alerts': enabled_alerts,
            'disabled_alerts': total_alerts - enabled_alerts,
            'scheduler_running': self.scheduler_running,
            'last_updated': datetime.now().isoformat()
        }
    
    def export_alerts(self, file_path: str):
        """Export alerts to file."""
        try:
            data = {
                'alerts': [asdict(alert) for alert in self.alerts.values()],
                'exported_at': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Success", f"Exported {len(self.alerts)} alerts")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export alerts: {str(e)}")
    
    def import_alerts(self, file_path: str):
        """Import alerts from file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            imported_count = 0
            for alert_data in data.get('alerts', []):
                try:
                    alert = Alert(**alert_data)
                    # Generate new ID to avoid conflicts
                    alert.id = f"imported_{int(time.time())}_{imported_count}"
                    self.alerts[alert.id] = alert
                    imported_count += 1
                except Exception as e:
                    print(f"Failed to import alert: {e}")
            
            if imported_count > 0:
                self._save_alerts()
                
                # Start scheduler if needed
                if self._has_enabled_alerts() and not self.scheduler_running:
                    self.start_scheduler()
                
                messagebox.showinfo("Success", f"Imported {imported_count} alerts")
            else:
                messagebox.showwarning("Warning", "No valid alerts found in file")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import alerts: {str(e)}")
