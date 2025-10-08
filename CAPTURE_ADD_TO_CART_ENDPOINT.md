# ✅ Mandarake Add-to-Cart Endpoint - CAPTURED

## Captured Endpoint Details

**URL:** `https://tools.mandarake.co.jp/basket/add/`
**Method:** POST
**Content-Type:** `application/x-www-form-urlencoded; charset=UTF-8`

**POST Parameters:**
```
request[id]: <product_id>          # Item code
request[count]: <quantity>          # Quantity (1, 2, 3, etc.)
request[shopType]: webshop          # Always "webshop"
request[langage]: en                # Language
request[countryId]: EN              # Country
request[location]: /order/...       # Current page path
request[referer]: https://order...  # Full referer URL
```

**Required Headers:**
- `Origin: https://order.mandarake.co.jp`
- `Referer: <product_page_or_search_page>`
- `X-Requested-With: XMLHttpRequest` (AJAX indicator)

**Status:** ✅ Implemented in `scrapers/mandarake_cart_api.py`

---

## Original Capture Guide

### 1. Open Browser DevTools

1. Open **Chrome** or **Firefox**
2. Press **F12** to open DevTools
3. Click the **Network** tab
4. Make sure **Preserve log** is checked ✅

### 2. Go to a Product Page

1. Visit any Mandarake product page, for example:
   ```
   https://order.mandarake.co.jp/order/detailPage/item?itemCode=1126279062
   ```

2. Make sure you're **logged in** to your Mandarake account

### 3. Add Item to Cart

1. In the Network tab, click **🗑️ Clear** to clear previous requests
2. On the product page, click **"Add to Cart"** button
3. Watch the Network tab for new requests

### 4. Find the Add-to-Cart Request

Look for a POST request. Common patterns:
- URL contains: `cart`, `add`, `basket`, `addItem`, etc.
- Method: **POST** (not GET)
- Status: **200** or **302** (redirect)

### 5. Capture Request Details

Click on the request, then check these tabs:

#### **Headers Tab**
```
Request URL: https://cart.mandarake.co.jp/cart/add
Request Method: POST
```

Copy the full URL!

#### **Payload Tab** (or Form Data)
```
Example (your actual data may differ):
itemCode: 1126279062
shopCode: nkn
quantity: 1
_csrf: abc123token456
referrer: /order/detailPage/item
```

Copy all the parameters!

#### **Request Headers**
Look for important headers:
```
Cookie: JSESSIONID=...; other cookies
Content-Type: application/x-www-form-urlencoded
Referer: https://order.mandarake.co.jp/...
```

### 6. Test in Python

Once captured, I'll update the `add_to_cart()` method with the real parameters.

---

## 📸 Screenshot Example

When you find the request, it should look like this:

```
Network Tab:
┌─────────────────────────────────────────────────────────┐
│ Name          Method  Status  Type   Size    Time       │
├─────────────────────────────────────────────────────────┤
│ add           POST    200     xhr    1.2kB   345ms   ← │
│ cart          GET     200     doc    15kB    123ms     │
└─────────────────────────────────────────────────────────┘

Click on "add" request to see details
```

---

## ⚡ Quick Test Script

Once you have the endpoint details, save them here and I'll test:

**Endpoint URL:**
```
https://cart.mandarake.co.jp/___________
```

**POST Parameters:**
```
itemCode: _______
shopCode: _______
quantity: _______
_csrf: _______  (if exists)
other: _______
```

**Required Headers:**
```
Cookie: JSESSIONID=...
Content-Type: ...
Referer: ...
```

---

## 🔍 Alternative Method: Copy as cURL

If you find the request in Network tab:
1. Right-click on it
2. **Copy** → **Copy as cURL**
3. Paste the cURL command in a file

Example cURL output:
```bash
curl 'https://cart.mandarake.co.jp/cart/add' \
  -H 'Cookie: JSESSIONID=...' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-raw 'itemCode=1126279062&shopCode=nkn&quantity=1&_csrf=token'
```

I can convert this to Python!

---

**Ready to capture?** Just add any item to your cart with DevTools open and share:
1. The request URL
2. The POST parameters
3. Any special headers

