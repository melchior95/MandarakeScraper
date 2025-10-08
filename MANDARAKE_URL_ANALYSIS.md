# Mandarake URL Structure Analysis

## Example URL
```
https://order.mandarake.co.jp/order/detailPage/item?itemCode=1312244361&ref=list&keyword=MINAMO%20first%20photograph&lang=en
```

## Key Findings from Item #1312244361

### 1. Item Identification
- **Item Code (Public)**: `1312244361` - Used in URL
- **Item Code (Internal)**: `kb5J06-00LP9Y89` - Store's internal code
- **SKU**: `0101825896-3400002` - Full SKU identifier

### 2. Item Details
- **Title**: "MINAMO MINAMO First Photograph Collection"
- **Publisher**: Tokuma Shoten
- **Category**: AV actress/Photograph Collection
- **Store**: Kyoto (京都店)
- **Condition**: (7)/With Obi
- **Status**: Store Front Item (Check Required)

### 3. Critical Discovery: "Store Front Item (Check Required)"

**This means**:
- Item is NOT in the online warehouse
- Item is physically in Kyoto store
- Must be verified/checked before shipping
- **Cannot appear in other stores** because it's a physical item in one location

## Implications for Auto-Purchase

### ❌ Items CANNOT Move Between Stores If:
- Status: "Store Front Item"
- These are physical items in one store location
- Will never appear in other stores

### ✅ Items CAN Move Between Stores If:
- Status: "Warehouse Item" or "Immediately Available"
- These come from central warehouse
- Can be listed under multiple stores

## Search Strategy Refinement

### Method 1: Check Item Status First
```python
def can_item_appear_in_other_stores(item_url: str) -> bool:
    """
    Determine if item can appear in other stores

    Returns:
        True: Item from warehouse, can appear anywhere
        False: Store front item, locked to one location
    """
    # Scrape item page
    soup = get_item_page(item_url)

    # Check item information
    item_info = soup.find('td', string=lambda t: t and 'Item Information' in t)
    if item_info:
        next_td = item_info.find_next('td')
        if next_td:
            info_text = next_td.get_text()

            # Store Front Item = locked to one store
            if 'Store Front Item' in info_text:
                return False

            # Warehouse items can appear anywhere
            if 'Warehouse' in info_text or 'Immediately' in info_text:
                return True

    # Default: assume it might move
    return True
```

### Method 2: Search Strategy Based on Item Type

**For Store Front Items**:
- Monitor ONLY the original URL
- Don't search other stores (waste of API calls)
- Item will only restock at same store

**For Warehouse Items**:
- Search ALL stores using exact title
- Item can appear under any shop location
- Use image comparison to verify

## URL Parameters Analysis

### Required Parameters
- `itemCode`: Unique item identifier (e.g., 1312244361)

### Optional Parameters
- `ref`: Referrer (e.g., "list" - came from search results)
- `keyword`: Search term used to find item
- `lang`: Language (en/ja)

### URL Without Keywords
```
https://order.mandarake.co.jp/order/detailPage/item?itemCode=1312244361
```
This works! Keywords are optional.

## Item Code Structure

### Public Item Code: `1312244361`
- 10 digits
- Used in URLs
- Publicly visible
- Unique per listing

### Internal Code: `kb5J06-00LP9Y89`
- Alphanumeric
- Store's internal tracking
- Format varies by store

### SKU: `0101825896-3400002`
- Full product SKU
- Format: `XXXXXXXXXX-XXXXXXX`
- Links to product database

## Auto-Purchase Optimization

### Updated Monitor Logic

```python
def _check_item_availability_smart(self, item):
    """
    Smart availability check based on item type
    """
    # Step 1: Check if we know the item type
    if item.get('item_type') == 'store_front':
        # Only check original URL (no multi-store search)
        return self._check_original_url(item)

    # Step 2: For warehouse items or unknown, search all stores
    elif item.get('item_type') == 'warehouse':
        return self._check_item_availability_all_stores(item)

    # Step 3: First time checking? Determine item type
    else:
        item_type = self._determine_item_type(item['store_link'])
        item['item_type'] = item_type

        if item_type == 'store_front':
            return self._check_original_url(item)
        else:
            return self._check_item_availability_all_stores(item)

def _determine_item_type(self, url: str) -> str:
    """
    Scrape item page to determine if store front or warehouse

    Returns:
        'store_front': Only at one store
        'warehouse': Can appear at any store
    """
    soup = self._fetch_item_page(url)

    item_info = soup.find('td', string=lambda t: t and 'Item Information' in t)
    if item_info:
        info_text = item_info.find_next('td').get_text()

        if 'Store Front Item' in info_text:
            return 'store_front'
        elif 'Warehouse' in info_text:
            return 'warehouse'

    return 'unknown'  # Default to checking all stores
```

## Database Schema Addition

Add `item_type` field to `auto_purchase_queue`:

```sql
ALTER TABLE auto_purchase_queue
ADD COLUMN item_type TEXT DEFAULT 'unknown';
-- Values: 'store_front', 'warehouse', 'unknown'
```

## Performance Impact

### Before Optimization
- Check 15 stores per item = 15 API calls per check
- 10 items × 15 stores = 150 API calls per interval

### After Optimization
- Store Front Items: 1 API call (original URL only)
- Warehouse Items: 15 API calls (all stores)
- Mixed (5 store + 5 warehouse): 5×1 + 5×15 = 80 API calls
- **47% reduction in API calls!**

## Summary

### Key Learnings

1. **Item codes are reliable identifiers**
   - 10-digit public code in URL
   - Can be used for direct access

2. **Items have different types**
   - Store Front: Physical item at one location
   - Warehouse: Can appear under any store

3. **Multi-store search only needed for warehouse items**
   - Saves 93% of API calls for store front items
   - Still catches all warehouse item relocations

4. **Item status visible in "Item Information" field**
   - Parse once on first check
   - Cache result for future checks

### Recommended Implementation

1. **First check**: Determine item type
2. **Store front items**: Monitor original URL only
3. **Warehouse items**: Search all stores with image verification
4. **Cache item type**: Don't re-check every time
5. **Log item type**: Help users understand monitoring behavior
