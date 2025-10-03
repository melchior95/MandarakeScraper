# Phase 3: DejaJapan Implementation Plan

## Overview

Implement DejaJapan marketplace as the second modular marketplace tab, focusing on seller-based auction searches with time-sensitive features.

**Target Date:** October 2025
**Estimated Effort:** 5 hours
**Dependencies:** Phase 1 (Base Infrastructure) ✅, Phase 2 (Suruga-ya) ✅

---

## DejaJapan Marketplace Analysis

### URL Structure

**Seller Page:**
```
https://www.dejapan.com/en/auction/yahoo/list/pgt?auc_seller={seller_id}
```

**Key Characteristics:**
- ✅ Seller-based searches only (no category/shop filters)
- ✅ Yahoo Auctions proxy service
- ✅ Time-sensitive data (auction end times)
- ✅ Bid tracking (current bids, bid count)
- ✅ Requires seller ID input (not keyword search)

### Data Fields to Extract

**Standard Fields:**
- Title (auction title in Japanese/English)
- Price (current bid price in JPY)
- Currency (JPY)
- Condition (usually from title/description)
- URL (auction page URL)
- Image URL (thumbnail)
- Seller (seller_id)

**Auction-Specific Fields:**
- `bids` (int) - Number of bids
- `end_time` (datetime) - Auction end time
- `status` (str) - "Active", "Ending Soon", "Ended"
- `watch_count` (int) - Number of watchers (if available)
- `starting_price` (float) - Initial bid price
- `buy_now_price` (float) - Buy It Now price (if available)

---

## Implementation Plan

### Step 1: Scraper Implementation (2 hours)

**File:** `scrapers/dejapan_scraper.py`

**Class Design:**
```python
class DejaJapanScraper(BaseScraper):
    """Scraper for DejaJapan (Yahoo Auctions proxy)"""

    def __init__(self):
        super().__init__(
            marketplace_name='dejapan',
            base_url='https://www.dejapan.com',
            rate_limit=2.0
        )

    def search_by_seller(self, seller_id: str, max_results: int = 50) -> List[Dict]:
        """Search auctions by seller ID"""
        # Build URL: /en/auction/yahoo/list/pgt?auc_seller={seller_id}
        # Parse auction cards (.item, .auction-item, or similar)
        # Extract data with parse_item()
        # Normalize results
        # Return list of dicts

    def parse_item(self, item_elem) -> Optional[Dict]:
        """Parse individual auction item"""
        # Extract: title, price, bids, end_time, image_url
        # Return raw dict

    def _parse_end_time(self, time_text: str) -> Optional[datetime]:
        """Convert relative time to datetime"""
        # Formats to handle:
        # - "14:33" (today at 14:33)
        # - "1 day" (tomorrow same time)
        # - "2 days" (2 days from now)
        # - "Oct 3" (specific date)
        # - "Ended" (past auction)

    def _calculate_time_status(self, end_time: datetime) -> str:
        """Determine auction status based on end time"""
        # Returns: "Ended", "Active", "Ending Soon (<1hr)", "Ending Soon (<6hr)"
```

**Key Challenges:**
1. **Time Parsing:** Handle relative times in multiple formats
2. **Pagination:** Detect and follow "Next" links
3. **Language:** DejaJapan shows English/Japanese mixed content
4. **Anti-Detection:** May need rotating user agents

**Testing:**
```bash
python test_dejapan_scraper.py
# Test with seller: yandatsu32 (example)
# Verify: 10+ results, end_time parsed correctly, status accurate
```

---

### Step 2: Tab Implementation (2 hours)

**File:** `gui/dejapan_tab.py`

**Class Design:**
```python
class DejaJapanTab(BaseMarketplaceTab):
    """Tab for DejaJapan seller searches"""

    def __init__(self, parent, settings_manager, alert_manager):
        self.scraper = DejaJapanScraper()
        super().__init__(parent, settings_manager, alert_manager, "DejaJapan")

        # Load favorite sellers
        self.favorite_sellers = self.settings.get_dejapan_favorite_sellers()
        self._populate_favorites_dropdown()

    def _create_marketplace_specific_controls(self, parent, start_row: int):
        """Create DejaJapan-specific controls"""
        pad = {'padx': 5, 'pady': 3}

        # Seller ID entry (replaces keyword)
        ttk.Label(parent, text="Seller ID:").grid(...)
        self.seller_id_var = tk.StringVar()
        seller_entry = ttk.Entry(parent, textvariable=self.seller_id_var, width=30)
        seller_entry.grid(...)

        # Favorite sellers dropdown
        ttk.Label(parent, text="Favorites:").grid(...)
        self.favorite_var = tk.StringVar()
        self.favorite_combo = ttk.Combobox(
            parent,
            textvariable=self.favorite_var,
            values=self._get_favorite_names(),
            state='readonly'
        )
        self.favorite_combo.grid(...)
        self.favorite_combo.bind('<<ComboboxSelected>>', self._on_favorite_selected)

        # Favorite management buttons
        btn_frame = ttk.Frame(parent)
        ttk.Button(btn_frame, text="Add to Favorites",
                   command=self._add_favorite).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Remove Favorite",
                   command=self._remove_favorite).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Edit Favorite",
                   command=self._edit_favorite).pack(side=tk.LEFT, padx=2)
        btn_frame.grid(...)

        # Filters
        filter_frame = ttk.LabelFrame(parent, text="Filters", padding=5)
        self.show_ended_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(filter_frame, text="Show ended auctions",
                        variable=self.show_ended_var).grid(...)

        self.highlight_ending_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(filter_frame, text="Highlight ending soon",
                        variable=self.highlight_ending_var).grid(...)

    def _get_tree_columns(self) -> tuple:
        """Define columns for results tree"""
        return ('title', 'price', 'bids', 'end_time', 'status')

    def _get_column_widths(self) -> Dict[str, int]:
        return {
            'title': 350,
            'price': 80,
            'bids': 60,
            'end_time': 120,
            'status': 100
        }

    def _format_tree_values(self, item: Dict) -> tuple:
        """Format item data for tree display"""
        price_str = f"¥{item['price']:.0f}" if item['price'] > 0 else "N/A"
        bids_str = str(item.get('bids', 0))
        end_time_str = self._format_end_time(item.get('end_time'))
        status = item.get('status', 'Active')

        return (item['title'], price_str, bids_str, end_time_str, status)

    def _apply_row_colors(self):
        """Color code rows by end time"""
        if not self.highlight_ending_var.get():
            return

        for item_id in self.tree.get_children():
            item_data = self.tree.item(item_id)
            status = item_data['values'][4]  # status column

            if "Ended" in status:
                self.tree.item(item_id, tags=('ended',))
            elif "<1hr" in status:
                self.tree.item(item_id, tags=('urgent',))
            elif "<6hr" in status:
                self.tree.item(item_id, tags=('soon',))

        # Define tag colors
        self.tree.tag_configure('ended', foreground='gray')
        self.tree.tag_configure('urgent', foreground='red', font=('', 9, 'bold'))
        self.tree.tag_configure('soon', foreground='orange')

    def _search_worker(self):
        """Background worker for DejaJapan search"""
        seller_id = self.seller_id_var.get().strip()
        if not seller_id:
            self.queue.put(('error', 'Please enter a seller ID'))
            self.queue.put(('complete', None))
            return

        self.queue.put(('status', f"Searching DejaJapan for seller '{seller_id}'..."))

        results = self.scraper.search_by_seller(
            seller_id=seller_id,
            max_results=int(self.max_results_var.get())
        )

        # Filter ended auctions if needed
        if not self.show_ended_var.get():
            results = [r for r in results if r.get('status') != 'Ended']

        self.queue.put(('results', results))
        self.queue.put(('status', f"Found {len(results)} auctions"))
        self.queue.put(('complete', None))

    def _add_favorite(self):
        """Add current seller to favorites"""
        seller_id = self.seller_id_var.get().strip()
        if not seller_id:
            messagebox.showwarning("No Seller", "Enter a seller ID first")
            return

        # Show dialog for name and notes
        dialog = FavoriteSellerDialog(self, seller_id)
        if dialog.result:
            self.settings.add_dejapan_favorite_seller(**dialog.result)
            self._populate_favorites_dropdown()
            messagebox.showinfo("Success", f"Added '{dialog.result['name']}' to favorites")
```

**UI Features:**
- ✅ Seller ID entry (no keyword field)
- ✅ Favorite sellers dropdown with quick-load
- ✅ Add/Edit/Remove favorite buttons
- ✅ "Show ended auctions" filter
- ✅ "Highlight ending soon" toggle
- ✅ Color-coded rows (red <1hr, orange <6hr, gray ended)
- ✅ Bids column
- ✅ End time column (formatted: "14:33 Today", "Tomorrow 10:00", "Ended")

---

### Step 3: Favorite Sellers Management (1 hour)

**Settings Manager Integration:**

Update `settings_manager.py`:
```python
def get_dejapan_favorite_sellers(self) -> List[Dict]:
    """Get list of favorite DejaJapan sellers"""
    return self.get_setting("marketplaces.dejapan.favorite_sellers", [])

def add_dejapan_favorite_seller(self, seller_id: str, name: str, notes: str = ""):
    """Add seller to favorites"""
    favorites = self.get_dejapan_favorite_sellers()

    # Check for duplicates
    if any(f['seller_id'] == seller_id for f in favorites):
        raise ValueError(f"Seller {seller_id} already in favorites")

    favorites.append({
        'seller_id': seller_id,
        'name': name,
        'notes': notes,
        'added_at': datetime.now().isoformat()
    })

    self.set_setting("marketplaces.dejapan.favorite_sellers", favorites)
    self.save_settings()

def remove_dejapan_favorite_seller(self, seller_id: str):
    """Remove seller from favorites"""
    favorites = self.get_dejapan_favorite_sellers()
    favorites = [f for f in favorites if f['seller_id'] != seller_id]
    self.set_setting("marketplaces.dejapan.favorite_sellers", favorites)
    self.save_settings()

def update_dejapan_favorite_seller(self, seller_id: str, name: str = None, notes: str = None):
    """Update seller info"""
    favorites = self.get_dejapan_favorite_sellers()
    for favorite in favorites:
        if favorite['seller_id'] == seller_id:
            if name is not None:
                favorite['name'] = name
            if notes is not None:
                favorite['notes'] = notes
            break

    self.set_setting("marketplaces.dejapan.favorite_sellers", favorites)
    self.save_settings()
```

**Favorite Seller Dialog:**

Create `gui/favorite_seller_dialog.py`:
```python
class FavoriteSellerDialog(tk.Toplevel):
    """Dialog for adding/editing favorite sellers"""

    def __init__(self, parent, seller_id: str, existing_data: Dict = None):
        super().__init__(parent)
        self.title("Add Favorite Seller" if not existing_data else "Edit Favorite")
        self.result = None

        # Seller ID (readonly if editing)
        ttk.Label(self, text="Seller ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.seller_id_var = tk.StringVar(value=seller_id)
        seller_entry = ttk.Entry(self, textvariable=self.seller_id_var, width=30)
        seller_entry.grid(row=0, column=1, padx=5, pady=5)
        if existing_data:
            seller_entry.config(state='readonly')

        # Display name
        ttk.Label(self, text="Display Name:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.name_var = tk.StringVar(value=existing_data.get('name', '') if existing_data else '')
        ttk.Entry(self, textvariable=self.name_var, width=30).grid(row=1, column=1, padx=5, pady=5)

        # Notes
        ttk.Label(self, text="Notes:").grid(row=2, column=0, sticky=tk.NW, padx=5, pady=5)
        self.notes_text = tk.Text(self, width=30, height=4)
        self.notes_text.grid(row=2, column=1, padx=5, pady=5)
        if existing_data:
            self.notes_text.insert('1.0', existing_data.get('notes', ''))

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Save", command=self._save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)

        self.transient(parent)
        self.grab_set()
        self.wait_window()

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Invalid Input", "Display name is required")
            return

        self.result = {
            'seller_id': self.seller_id_var.get().strip(),
            'name': name,
            'notes': self.notes_text.get('1.0', 'end-1c').strip()
        }
        self.destroy()
```

**Export/Import Favorites:**
```python
def export_favorites_to_csv(self):
    """Export favorites to CSV"""
    favorites = self.settings.get_dejapan_favorite_sellers()

    filepath = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV Files", "*.csv")]
    )

    if filepath:
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['seller_id', 'name', 'notes', 'added_at'])
            writer.writeheader()
            writer.writerows(favorites)

def import_favorites_from_csv(self):
    """Import favorites from CSV"""
    filepath = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])

    if filepath:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    self.settings.add_dejapan_favorite_seller(
                        seller_id=row['seller_id'],
                        name=row['name'],
                        notes=row.get('notes', '')
                    )
                except ValueError:
                    pass  # Skip duplicates
```

---

### Step 4: GUI Integration (30 minutes)

**Update `gui_config.py`:**

1. **Add to dynamic tab loading** (around line 390):
```python
if marketplace_toggles.get('dejapan', False):
    from gui.dejapan_tab import DejaJapanTab
    self.dejapan_tab = DejaJapanTab(notebook, self.settings, self.alert_tab.alert_manager)
    notebook.add(self.dejapan_tab, text="DejaJapan")
```

2. **Add to on_closing** (cleanup):
```python
if hasattr(self, 'dejapan_tab'):
    self.dejapan_tab.on_closing()
```

3. **Toggle checkbox is already present** (from Phase 1):
```python
self.dejapan_enabled = tk.BooleanVar(value=marketplace_toggles.get('dejapan', False))
ttk.Checkbutton(marketplace_frame, text="DejaJapan",
                variable=self.dejapan_enabled,
                command=self._on_marketplace_toggle).grid(...)
```

---

### Step 5: Testing (30 minutes)

**Test Script:** `test_dejapan_scraper.py`

```python
#!/usr/bin/env python3
"""Test DejaJapan scraper standalone"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scrapers.dejapan_scraper import DejaJapanScraper

def test_scraper():
    scraper = DejaJapanScraper()

    # Test with real seller ID
    seller_id = "yandatsu32"  # Example seller
    max_results = 10

    print(f"Testing DejaJapan scraper...")
    print(f"Seller ID: {seller_id}")
    print(f"Max results: {max_results}")
    print("=" * 80)

    try:
        results = scraper.search_by_seller(seller_id, max_results=max_results)

        print(f"\n[SUCCESS] Found {len(results)} auctions")

        # Save to JSON
        output_file = "dejapan_test_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)

        print(f"[SUCCESS] Results saved to: {output_file}")

        # Print first result details
        if results:
            item = results[0]
            print(f"\nFirst result:")
            print(f"  Title: {item['title'][:80]}...")
            print(f"  Price: ¥{item['price']:.0f}")
            print(f"  Bids: {item.get('bids', 0)}")
            print(f"  End Time: {item.get('end_time')}")
            print(f"  Status: {item.get('status')}")
            print(f"  URL: {item['url'][:80]}...")

        # Test time parsing
        print(f"\n[TEST] Time Status Breakdown:")
        status_counts = {}
        for item in results:
            status = item.get('status', 'Unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

        for status, count in status_counts.items():
            print(f"  {status}: {count} items")

        return True

    except Exception as e:
        print(f"\n[ERROR] Scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_scraper()
    sys.exit(0 if success else 1)
```

**GUI Test Checklist:**

1. ✅ Enable DejaJapan in Advanced tab
2. ✅ Restart application
3. ✅ Verify "DejaJapan" tab appears
4. ✅ Enter seller ID → Search
5. ✅ Verify results display with bids, end_time
6. ✅ Test color coding (red/orange/gray)
7. ✅ Add seller to favorites
8. ✅ Load from favorites dropdown
9. ✅ Edit favorite seller
10. ✅ Remove favorite seller
11. ✅ Toggle "Show ended auctions" filter
12. ✅ Toggle "Highlight ending soon" color
13. ✅ Export to CSV
14. ✅ Send to Alerts tab
15. ✅ Double-click to open URL

---

## Key Differences from Suruga-ya

| Feature | Suruga-ya | DejaJapan |
|---------|-----------|-----------|
| **Search Type** | Keyword + Category + Shop | Seller ID only |
| **Category Dropdown** | ✅ 70+ categories | ❌ None (seller page) |
| **Shop Dropdown** | ✅ Multiple shops | ❌ None (seller page) |
| **Keyword Field** | ✅ Text input | ❌ Seller ID input |
| **Time-Sensitive** | ❌ Static listings | ✅ Auction end times |
| **Favorites System** | ❌ Not needed | ✅ Save favorite sellers |
| **Color Coding** | ❌ None | ✅ Red/Orange/Gray by time |
| **Bids Column** | ❌ None | ✅ Current bid count |
| **Extra Columns** | Publisher, Release Date | Bids, End Time, Status |

---

## Expected Challenges

### 1. Time Parsing Complexity
**Problem:** DejaJapan uses relative time formats:
- "14:33" → Today at 14:33
- "1 day" → Tomorrow same time
- "Oct 3" → Specific date

**Solution:**
```python
def _parse_end_time(self, time_text: str) -> Optional[datetime]:
    now = datetime.now()

    # Pattern 1: HH:MM (today)
    if re.match(r'\d{1,2}:\d{2}', time_text):
        hour, minute = map(int, time_text.split(':'))
        return now.replace(hour=hour, minute=minute, second=0)

    # Pattern 2: "X day(s)"
    match = re.match(r'(\d+)\s*days?', time_text)
    if match:
        days = int(match.group(1))
        return now + timedelta(days=days)

    # Pattern 3: "Oct 3", "October 3"
    # Use dateutil.parser for flexible parsing

    # Pattern 4: "Ended"
    if 'ended' in time_text.lower():
        return now - timedelta(days=1)  # Past date

    return None
```

### 2. HTML Structure Uncertainty
**Problem:** Don't know exact HTML selectors until we inspect the page

**Solution:**
1. Use WebFetch to inspect seller page HTML
2. Identify item containers (`.auction-item`, `.listing`, etc.)
3. Extract title, price, bids, end_time selectors
4. Document in scraper docstring

### 3. Pagination
**Problem:** May need to paginate through seller listings

**Solution:**
```python
# Detect "Next" button or page numbers
next_link = soup.find('a', class_='next-page')
if next_link and len(results) < max_results:
    next_url = urljoin(self.base_url, next_link['href'])
    # Recursively fetch next page
```

### 4. Seller ID Validation
**Problem:** Invalid seller IDs should show friendly error

**Solution:**
```python
def validate_seller_id(self, seller_id: str) -> bool:
    """Check if seller ID is valid format"""
    # DejaJapan seller IDs are typically alphanumeric
    if not re.match(r'^[a-zA-Z0-9_-]+$', seller_id):
        raise ValueError("Invalid seller ID format")

    # Test with initial request
    response = self.session.get(f"{self.base_url}/en/auction/yahoo/list/pgt?auc_seller={seller_id}")
    if response.status_code == 404:
        raise ValueError(f"Seller '{seller_id}' not found")

    return True
```

---

## File Structure

```
mandarake_scraper/
├── scrapers/
│   ├── base_scraper.py           ✅ (Phase 1)
│   ├── surugaya_scraper.py       ✅ (Phase 2)
│   └── dejapan_scraper.py        🆕 (Phase 3)
│
├── gui/
│   ├── base_marketplace_tab.py   ✅ (Phase 1)
│   ├── surugaya_tab.py           ✅ (Phase 2)
│   ├── dejapan_tab.py            🆕 (Phase 3)
│   └── favorite_seller_dialog.py 🆕 (Phase 3)
│
├── test_dejapan_scraper.py       🆕 (Phase 3)
├── settings_manager.py           ✏️ (Add favorite methods)
├── gui_config.py                 ✏️ (Add tab loading)
└── PHASE3_DEJAPAN_PLAN.md        📄 (This document)
```

---

## Settings Schema Updates

**user_settings.json:**
```json
{
  "marketplaces": {
    "enabled": {
      "mandarake": true,
      "ebay": true,
      "surugaya": false,
      "dejapan": true,      // User enables ← NEW
      "alerts": true
    },
    "dejapan": {
      "favorite_sellers": [   // ← NEW
        {
          "seller_id": "yandatsu32",
          "name": "Yandatsu Camera Shop",
          "notes": "Great vintage camera seller",
          "added_at": "2025-10-02T18:00:00"
        }
      ],
      "default_max_results": 50,
      "highlight_ending_soon": true,
      "show_ended_auctions": false
    }
  }
}
```

---

## Success Criteria

### Scraper Tests ✅
- [ ] Successfully fetch 10+ auctions from test seller
- [ ] Parse all fields: title, price, bids, end_time, status
- [ ] Handle "Ended" auctions correctly
- [ ] Time parsing accurate for all formats
- [ ] Pagination works (if needed)
- [ ] Rate limiting prevents blocks

### GUI Tests ✅
- [ ] Tab loads when enabled in Advanced tab
- [ ] Seller ID search works
- [ ] Results display with all columns
- [ ] Color coding works (red <1hr, orange <6hr, gray ended)
- [ ] Add/Edit/Remove favorites works
- [ ] Load from favorites dropdown works
- [ ] Export to CSV includes all fields
- [ ] Send to Alerts tab works
- [ ] "Show ended" filter works
- [ ] "Highlight ending" toggle works

### Integration Tests ✅
- [ ] Favorite sellers persist across restarts
- [ ] Tab disable/enable works correctly
- [ ] No conflicts with other tabs
- [ ] Alert integration works
- [ ] CSV export format consistent

---

## Timeline

| Task | Estimated Time | Deliverable |
|------|----------------|-------------|
| HTML research & selectors | 30 min | Documented selectors |
| Scraper implementation | 1.5 hours | `dejapan_scraper.py` |
| Time parsing logic | 30 min | `_parse_end_time()` method |
| Tab UI implementation | 1 hour | `dejapan_tab.py` |
| Favorites management | 1 hour | Settings methods + dialog |
| GUI integration | 30 min | Tab loading in `gui_config.py` |
| Testing & debugging | 1 hour | All tests passing |
| **Total** | **~5 hours** | **Phase 3 complete** |

---

## Phase 4 Preview: Yahoo Auctions Direct (Optional)

After DejaJapan is complete, we could add:

**Yahoo Auctions Japan Direct Tab:**
- Bypasses DejaJapan proxy
- Searches Yahoo Auctions directly
- Requires Japanese IP / VPN
- More categories and filters
- Lower fees (no proxy markup)

**Estimated Effort:** 6 hours (more complex anti-detection)

---

## Conclusion

Phase 3 will add DejaJapan as a fully modular marketplace tab with unique auction-focused features:

**New Capabilities:**
- ✅ Seller-based auction searches
- ✅ Time-sensitive color coding
- ✅ Favorite sellers management
- ✅ Bid tracking
- ✅ Auction status monitoring

**Reuses from Phase 1 & 2:**
- ✅ BaseScraper (HTTP, rate limiting, normalization)
- ✅ BaseMarketplaceTab (UI framework, threading, export)
- ✅ Settings Manager (persistence, toggles)
- ✅ Alert integration (send to review workflow)

**Architecture Benefits Validated:**
- ~5 hours to add new marketplace (vs ~20+ hours monolithic)
- Zero impact on existing tabs
- User control via toggles
- Clean separation of concerns

**Phase 3 Status:** 📋 Planned, ready to implement

**Next Step:** Research DejaJapan HTML structure with WebFetch
