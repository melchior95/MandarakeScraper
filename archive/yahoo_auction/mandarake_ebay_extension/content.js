/**
 * Mandarake Price Checker - eBay Content Script
 * Injects "Check Price" buttons with lazy loading
 */

const API_BASE = 'http://localhost:5000';
const USD_JPY_RATE = 151.5; // Can be updated from settings

// Cache for fetched prices
const priceCache = new Map();

/**
 * Parse USD price from eBay listing
 */
function parsePrice(priceText) {
    const match = priceText.match(/\$?([\d,]+\.?\d*)/);
    return match ? parseFloat(match[1].replace(',', '')) : 0;
}

/**
 * Create "Check Price" button
 */
function createCheckPriceButton() {
    const button = document.createElement('button');
    button.className = 'mandarake-check-btn';
    button.textContent = '🔍 Check Mandarake Price';
    button.title = 'Click to search Mandarake for this item';
    return button;
}

/**
 * Create price overlay with stock status
 */
function createPriceOverlay(data, ebayPrice) {
    const overlay = document.createElement('div');
    overlay.className = 'mandarake-overlay';

    const mandarakePriceUSD = data.mandarake_price_jpy / USD_JPY_RATE;
    const profit = ebayPrice - mandarakePriceUSD;
    const profitPercent = ((profit / mandarakePriceUSD) * 100).toFixed(0);

    // Determine profit color
    let profitClass = 'neutral';
    if (profitPercent >= 50) profitClass = 'high';
    else if (profitPercent >= 20) profitClass = 'good';
    else if (profitPercent < 10) profitClass = 'low';

    // Stock icon
    const stockIcon = data.in_stock ? '✅' : '❌';
    const stockText = data.in_stock ? 'In Stock' : 'Out of Stock';
    const stockClass = data.in_stock ? 'in-stock' : 'out-of-stock';

    overlay.innerHTML = `
        <div class="mandarake-price-box ${profitClass}">
            <div class="mandarake-price">
                💰 Mandarake: ¥${data.mandarake_price_jpy.toLocaleString()}
                ($${mandarakePriceUSD.toFixed(2)})
            </div>
            <div class="mandarake-profit">
                📊 Profit: ${profit >= 0 ? '+' : ''}$${profit.toFixed(2)}
                (${profitPercent}%)
            </div>
            <div class="mandarake-stock ${stockClass}">
                ${stockIcon} ${stockText} @ ${data.store}
            </div>
            <a href="${data.link}" target="_blank" class="mandarake-link">
                🔗 View on Mandarake
            </a>
            ${data.from_cache ? '<div class="cache-indicator">📦 Cached</div>' : ''}
        </div>
    `;

    return overlay;
}

/**
 * Fetch price from Mandarake API
 */
async function fetchMandarakePrice(title) {
    // Check cache first
    if (priceCache.has(title)) {
        const cached = priceCache.get(title);
        return { ...cached, from_cache: true };
    }

    try {
        const response = await fetch(`${API_BASE}/api/mandarake/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title })
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();

        // Cache the result
        if (data.found) {
            priceCache.set(title, data);
        }

        return data;
    } catch (error) {
        console.error('Error fetching Mandarake price:', error);
        return { found: false, error: error.message };
    }
}

// Track how many listings we've debugged (global counter)
let debuggedCount = 0;

/**
 * Process individual eBay listing
 */
async function processListing(listing) {
    // Skip sponsored/ads
    if (listing.classList.contains('s-item--ad')) return;

    // Check if already processed
    if (listing.querySelector('.mandarake-check-btn') ||
        listing.querySelector('.mandarake-overlay')) {
        return;
    }

    // Try multiple selector strategies for title (ordered by specificity)
    let titleElem =
        listing.querySelector('.s-item__title') ||  // Old layout
        listing.querySelector('span[role="heading"]') ||  // New layout (most common)
        listing.querySelector('h3') ||  // Generic heading
        listing.querySelector('[class*="title"]') ||  // Wildcard
        listing.querySelector('.s-card__title') ||  // Card title variant
        listing.querySelector('a[role="heading"]') ||  // Link heading
        listing.querySelector('[data-testid*="title"]');  // Test ID variant

    // Try multiple selector strategies for price (ordered by specificity)
    let priceElem =
        listing.querySelector('.s-item__price') ||  // Old layout
        listing.querySelector('[class*="s-item__price"]') ||  // Price variants
        listing.querySelector('[class*="price"][class*="display"]') ||  // Display price
        listing.querySelector('span[aria-label*="rice"]') ||  // Accessibility label (P might be trimmed)
        listing.querySelector('[class*="POSITIVE"]') ||  // eBay uses color classes for prices
        listing.querySelector('[data-testid*="price"]');  // Test ID variant

    if (!titleElem || !priceElem) {
        // Debug: Show detailed structure for first 3 listings
        if (debuggedCount < 3) {
            debuggedCount++;
            console.log(`\n=== DEBUG LISTING #${debuggedCount} ===`);
            console.log('Listing classes:', listing.className);
            console.log('Listing ID:', listing.id);
            console.log('Title found:', !!titleElem, titleElem ? `"${titleElem.textContent.substring(0, 50).trim()}"` : 'MISSING');
            console.log('Price found:', !!priceElem, priceElem ? `"${priceElem.textContent.trim()}"` : 'MISSING');

            // Find all links
            const links = Array.from(listing.querySelectorAll('a'));
            console.log('\nLinks found:', links.length);
            links.slice(0, 3).forEach((link, i) => {
                console.log(`  Link ${i + 1} [${link.className}]:`, link.textContent.substring(0, 60).trim());
                console.log(`    → role="${link.getAttribute('role')}"`, `data-testid="${link.getAttribute('data-testid')}"`);
            });

            // Find all spans with their attributes
            const spans = Array.from(listing.querySelectorAll('span'));
            console.log('\nSpans found:', spans.length);
            spans.slice(0, 15).forEach((span, i) => {
                const text = span.textContent.substring(0, 40).trim();
                if (text) {  // Only show spans with text
                    const role = span.getAttribute('role');
                    const ariaLabel = span.getAttribute('aria-label');
                    const testId = span.getAttribute('data-testid');
                    console.log(`  Span ${i + 1} [${span.className || 'no-class'}]: "${text}"`);
                    if (role) console.log(`    → role="${role}"`);
                    if (ariaLabel) console.log(`    → aria-label="${ariaLabel}"`);
                    if (testId) console.log(`    → data-testid="${testId}"`);
                }
            });

            // Find all divs with classes
            const divsWithClass = Array.from(listing.querySelectorAll('div[class]'));
            console.log('\nDivs with classes (first 8):', divsWithClass.slice(0, 8).map(d => d.className));

            // Look for price-like text ($ followed by numbers)
            const allText = listing.textContent;
            const priceMatches = allText.match(/\$[\d,]+\.?\d*/g);
            console.log('\nPrice-like text found:', priceMatches);

            // Try to find elements with role="heading"
            const headings = Array.from(listing.querySelectorAll('[role="heading"]'));
            console.log('\nElements with role="heading":', headings.length);
            headings.forEach((h, i) => {
                console.log(`  Heading ${i + 1} [${h.tagName}.${h.className}]:`, h.textContent.substring(0, 50).trim());
            });

            console.log('=== END DEBUG ===\n');
        }
        return;
    }

    const title = titleElem.textContent.trim();
    const ebayPrice = parsePrice(priceElem.textContent);

    if (!title || ebayPrice === 0) return;

    // Create and inject "Check Price" button
    const checkButton = createCheckPriceButton();

    checkButton.addEventListener('click', async (e) => {
        e.preventDefault();
        e.stopPropagation();

        // Show loading state
        checkButton.textContent = '⏳ Searching Mandarake...';
        checkButton.disabled = true;

        try {
            // Fetch price data
            const result = await fetchMandarakePrice(title);

            if (result.found) {
                // Create and show price overlay
                const overlay = createPriceOverlay(result, ebayPrice);
                checkButton.replaceWith(overlay);
            } else {
                checkButton.textContent = '❌ Not Found on Mandarake';
                checkButton.className = 'mandarake-check-btn not-found';
            }
        } catch (error) {
            checkButton.textContent = '⚠️ Error - Click to Retry';
            checkButton.disabled = false;
        }
    });

    // Find a good place to inject the button - try multiple containers
    let container = listing.querySelector('.s-item__detail');
    if (!container) container = listing.querySelector('.s-item__info');
    if (!container) container = listing.querySelector('.s-item__details');
    if (!container) container = listing.querySelector('.su-card-container');

    if (container) {
        container.appendChild(checkButton);
    } else {
        // Fallback: append directly to listing
        listing.appendChild(checkButton);
    }
}

/**
 * Process all listings on page
 */
function processAllListings() {
    // Try multiple selectors (eBay changes their structure frequently)
    let listings = document.querySelectorAll('.s-card');  // NEW eBay layout (2025)

    if (listings.length === 0) {
        listings = document.querySelectorAll('.s-item');  // Old layout
    }

    if (listings.length === 0) {
        listings = document.querySelectorAll('ul.srp-results > li');  // Direct children
    }

    if (listings.length === 0) {
        listings = document.querySelectorAll('[data-view]');  // Fallback
    }

    console.log(`Mandarake Extension: Found ${listings.length} listings`);
    console.log('Using selector:',
        listings.length > 0 ? (listings[0].className || listings[0].tagName) : 'none');

    listings.forEach(listing => {
        try {
            processListing(listing);
        } catch (error) {
            console.error('Error processing listing:', error);
        }
    });
}

/**
 * Initialize extension
 */
function init() {
    console.log('Mandarake Price Checker: Initializing...');

    // Process initial listings
    processAllListings();

    // Watch for new listings (pagination, infinite scroll)
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === 1) {
                    // Check if it matches any listing selector (new or old eBay layout)
                    if (node.classList?.contains('s-card') ||  // NEW layout
                        node.classList?.contains('s-item') ||  // OLD layout
                        node.tagName === 'LI' ||
                        node.hasAttribute('data-view')) {
                        processListing(node);
                    }
                }
            });
        });
    });

    // Try multiple container selectors
    let searchResults = document.querySelector('.srp-results');
    if (!searchResults) {
        searchResults = document.querySelector('ul.srp-results');
    }
    if (!searchResults) {
        searchResults = document.querySelector('[role="list"]');
    }

    if (searchResults) {
        observer.observe(searchResults, {
            childList: true,
            subtree: true
        });
        console.log('Mutation observer attached to:', searchResults);
    } else {
        console.log('Could not find search results container for mutation observer');
    }

    console.log('Mandarake Price Checker: Ready!');
}

// Start when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
