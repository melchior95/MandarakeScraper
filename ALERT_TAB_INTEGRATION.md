# Alert Tab Integration Guide

## Files Created

1. **`gui/alert_states.py`** - Alert state management (enums, transitions, colors)
2. **`gui/alert_storage.py`** - JSON persistence layer
3. **`gui/alert_manager.py`** - Core business logic
4. **`gui/alert_tab.py`** - UI component (the Alert tab itself)

## Integration Steps

### Step 1: Add Alert Tab to Notebook

In your main GUI file (`gui_config.py`), add the Alert tab to the notebook:

```python
from gui.alert_tab import AlertTab

class MandarakeGUI(tk.Tk):
    def __init__(self):
        # ... existing code ...

        # Create notebook
        notebook = ttk.Notebook(self)

        # Add existing tabs
        # ... Mandarake Search tab ...
        # ... eBay Search tab ...
        # ... CSV Results tab ...

        # ADD THIS: Create Alert tab
        self.alert_tab = AlertTab(notebook)
        notebook.add(self.alert_tab, text="Review/Alerts")

        # ... rest of your code ...
```

### Step 2: Connect eBay Search Results to Alerts

In your eBay Search tab, after comparison results are displayed, add a button to send results to alerts:

```python
# In the eBay Search tab's display_results method or similar:
def display_ebay_comparison_results(self, comparison_results):
    # ... existing code to display results in treeview ...

    # ADD THIS: Button to send to alerts
    send_to_alerts_btn = ttk.Button(
        button_frame,
        text="Send to Alerts",
        command=lambda: self.send_to_alerts(comparison_results)
    )
    send_to_alerts_btn.pack(side=tk.LEFT, padx=5)

def send_to_alerts(self, comparison_results):
    """Send comparison results to Alert tab."""
    # Access the alert tab via parent GUI
    alert_tab = self.master.alert_tab  # or however you reference it
    alert_tab.add_comparison_results_to_alerts(comparison_results)
```

### Step 3: Auto-send to Alerts (Optional)

If you want results to automatically appear in alerts when they meet thresholds:

```python
# After comparison completes in eBay Search tab:
def on_comparison_complete(self, comparison_results):
    # Display in treeview
    self.display_comparison_results(comparison_results)

    # Auto-send to alerts if thresholds are met
    alert_tab = self.master.alert_tab
    alert_tab.add_comparison_results_to_alerts(comparison_results)
```

## Usage Flow

### For Users:

1. **Set Thresholds** in Alert tab (default: 70% similarity, 20% profit)
2. **Run Comparison** in eBay Search tab
3. **Results meeting thresholds** automatically appear in Alert tab as "Pending"
4. **Review items**:
   - Mark interesting items as "Yay"
   - Mark unwanted items as "Nay"
5. **Bulk Actions**:
   - Select multiple "Yay" items → Click "Purchase" → All marked as Purchased
   - Select "Purchased" items → Click "Shipped" → All marked as Shipped
   - And so on through the workflow: Received → Posted → Sold

### State Workflow:

```
Pending → [Yay / Nay]
   ↓
  Yay → Purchased → Shipped → Received → Posted → Sold
```

## Features

### Treeview Columns:
- **ID**: Alert unique ID
- **State**: Current state with color coding
- **Similarity %**: Image similarity score
- **Profit %**: Profit margin
- **Mandarake Title**: Original listing title
- **eBay Title**: Comparable eBay listing
- **Mandarake Price**: Source price in ¥
- **eBay Price**: Sold price in $
- **Shipping**: eBay shipping cost
- **Sold Date**: When eBay item sold

### Color Coding:
- White: Pending
- Light Green: Yay
- Light Red: Nay
- Sky Blue: Purchased
- Plum: Shipped
- Khaki: Received
- Gold: Posted
- Lime Green: Sold

### Actions:
- **Double-click**: Open Mandarake or eBay link
- **Right-click**: Context menu with quick actions
- **Bulk Actions**: Select multiple items and apply state changes

### Persistence:
- All alerts saved to `alerts.json`
- Survives application restart
- Tracks created/updated timestamps

## Example Integration in gui_config.py

```python
# At the top
from gui.alert_tab import AlertTab

# In __init__ or wherever you build the notebook:
def _build_notebook(self):
    notebook = ttk.Notebook(self)

    # Existing tabs
    mandarake_tab = ttk.Frame(notebook)
    notebook.add(mandarake_tab, text="Mandarake Search")
    # ... build mandarake tab ...

    ebay_tab = ttk.Frame(notebook)
    notebook.add(ebay_tab, text="eBay Search")
    # ... build ebay tab ...

    csv_tab = ttk.Frame(notebook)
    notebook.add(csv_tab, text="CSV Results")
    # ... build csv tab ...

    # NEW: Alert tab
    self.alert_tab = AlertTab(notebook)
    notebook.add(self.alert_tab, text="Review/Alerts")

    return notebook

# In your eBay comparison display method:
def display_csv_comparison_results(self, comparison_results):
    # ... existing display code ...

    # Add button to send to alerts
    ttk.Button(
        button_frame,
        text="→ Send to Alerts",
        command=lambda: self.alert_tab.add_comparison_results_to_alerts(comparison_results)
    ).pack(side=tk.LEFT, padx=5)
```

## Testing

1. Run the application
2. Navigate to "Review/Alerts" tab
3. Set thresholds (e.g., 70% similarity, 20% profit)
4. Go to eBay Search tab
5. Run a comparison
6. Items meeting thresholds should appear in Alerts tab
7. Test bulk actions: select items → mark as Yay → purchase → etc.

## Storage Location

Alerts are stored in: `alerts.json` (in project root)

Format:
```json
[
  {
    "alert_id": 1,
    "state": "yay",
    "ebay_title": "...",
    "mandarake_title": "...",
    "mandarake_link": "https://...",
    "ebay_link": "https://...",
    "similarity": 85.5,
    "profit_margin": 45.2,
    "mandarake_price": "¥3,000",
    "ebay_price": "$35.00",
    "shipping": "$5.00",
    "sold_date": "2025-01-15",
    "thumbnail": "https://...",
    "created_at": "2025-10-01T12:00:00",
    "updated_at": "2025-10-01T12:05:00"
  }
]
```
