# Minimal Store Integration Plan

## Problem

The original attempt to create a unified Stores tab removed too much functionality:
- Config tree columns missing
- Move up/down buttons gone
- Dynamic config saving broken
- CSV options missing
- All the carefully crafted Mandarake tab features lost

## Solution: Keep Everything, Add Store Selector

Instead of rebuilding the UI, we'll make **minimal changes**:
1. Rename "Mandarake" tab to "Stores"
2. Add store selector dropdown at the top
3. Keep all existing functionality intact
4. Make categories/shops load dynamically based on selected store

---

## Changes Required

### Change 1: Tab Name (DONE)
```python
# Line 383
notebook.add(basic_frame, text="Stores")  # Was: "Mandarake"
```

### Change 2: Add Store Selector
Insert at line 411, before "Mandarake URL input":

```python
# Store selector
ttk.Label(top_pane, text="Store:").grid(row=0, column=0, sticky=tk.W, **pad)
self.current_store = tk.StringVar(value="Mandarake")
ttk.Combobox(
    top_pane,
    textvariable=self.current_store,
    values=["Mandarake", "Suruga-ya"],
    state="readonly",
    width=20
).grid(row=0, column=1, sticky=tk.W, **pad)
```

### Change 3: Shift All Rows Down by 1
- URL: row 0 → row 1
- Keyword: row 1 → row 2
- Main category: row 2 → row 3
- Labels: row 3 → row 4
- Listboxes: row 4 → row 5
- Update rowconfigure: row 4 → row 5

### Change 4: Dynamic Category/Shop Loading
When store changes, reload the categories and shops:

```python
def _on_store_changed(self, event=None):
    store = self.current_store.get()

    if store == "Mandarake":
        # Load Mandarake categories
        self._populate_detail_categories()
        self._populate_shop_list()
    elif store == "Suruga-ya":
        # Load Suruga-ya categories
        from store_codes.surugaya_codes import SURUGAYA_CATEGORIES, SURUGAYA_SHOPS
        self._populate_surugaya_categories()
        self._populate_surugaya_shops()
```

### Change 5: Add Suruga-ya Populate Methods
```python
def _populate_surugaya_categories(self):
    from store_codes.surugaya_codes import SURUGAYA_CATEGORIES
    self.detail_listbox.delete(0, tk.END)
    for code, name in sorted(SURUGAYA_CATEGORIES.items()):
        self.detail_listbox.insert(tk.END, f"{name} ({code})")

def _populate_surugaya_shops(self):
    from store_codes.surugaya_codes import SURUGAYA_SHOPS
    self.shop_listbox.delete(0, tk.END)
    for code, name in sorted(SURUGAYA_SHOPS.items()):
        self.shop_listbox.insert(tk.END, f"{name} ({code})")
```

### Change 6: Update Search Button
Modify "Search Mandarake" button to check current store:

```python
def run_now(self):
    store = self.current_store.get()

    if store == "Mandarake":
        # Existing Mandarake scraper code
        ...
    elif store == "Suruga-ya":
        # Call Suruga-ya scraper
        from scrapers.surugaya_scraper import SurugayaScraper
        scraper = SurugayaScraper()
        results = scraper.search(...)
        # Send results to eBay CSV frame for comparison
```

---

## What Stays the Same

✅ **ALL existing functionality:**
- Config tree with all columns
- Move up/down buttons
- Delete config
- Auto-save on field changes
- Enter to save with new filename
- Hide sold checkbox
- Results per page
- Max pages
- Latest additions dropdown
- Language selector
- Right-click publisher list
- Schedules tab
- ALL the buttons and options

✅ **Results still go to eBay CSV frame** - No separate results pane in Stores tab

✅ **All existing methods work** - No need to rewrite anything

---

## Benefits

1. **Zero Breaking Changes** - Everything works exactly as before
2. **Minimal Code** - Only ~50 lines added
3. **Same UX** - Users familiar with Mandarake tab see same layout
4. **Easy Extension** - Add DejaJapan by adding another case to the store selector

---

## Implementation Steps

1. ✅ Rename tab to "Stores"
2. ✅ Remove old Suruga-ya tab import
3. ✅ Add store selector dropdown (row 0)
4. ✅ Shift all existing rows down by 1
5. ✅ Add `_on_store_changed` method
6. ✅ Add Suruga-ya populate methods
7. ✅ Update `run_now` to check store
8. ✅ Update config save to include store field
9. ⏳ Update config tree to show store column
10. ⏳ Test with both Mandarake and Suruga-ya

---

##Would you like me to proceed with this minimal approach?

This keeps ALL your existing functionality while adding Suruga-ya support.
