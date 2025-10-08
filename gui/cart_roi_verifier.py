"""
Cart ROI Verifier

Verifies ROI for all items in Mandarake cart by comparing with eBay sold listings.
Supports both text-based "Compare All" and image-based "Image Compare All".
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from gui.utils import fetch_exchange_rate


class CartROIVerifier:
    """Verifies ROI for cart items using eBay comparison"""

    def __init__(self, ebay_search_manager=None, csv_comparison_manager=None):
        """
        Initialize ROI verifier

        Args:
            ebay_search_manager: EbaySearchManager for eBay searches
            csv_comparison_manager: CSVComparisonManager for image comparison
        """
        self.ebay_search_manager = ebay_search_manager
        self.csv_comparison_manager = csv_comparison_manager
        self.logger = logging.getLogger(__name__)

    def verify_cart_text_based(self, cart_items: List[Dict],
                               exchange_rate: float = None,
                               progress_callback=None) -> Dict:
        """
        Verify cart ROI using text-based eBay search (Compare All)

        Args:
            cart_items: List of cart item dicts
            exchange_rate: USD/JPY rate (auto-fetched if not provided)
            progress_callback: Optional callback(current, total, message)

        Returns:
            dict: {
                'total_cost_jpy': int,
                'total_cost_usd': float,
                'est_revenue_usd': float,
                'profit_usd': float,
                'roi_percent': float,
                'exchange_rate': float,
                'items_verified': int,
                'items_flagged': int,
                'verified_items': [...],
                'flagged_items': [...],
                'method': 'text_based'
            }
        """
        if not self.ebay_search_manager:
            return {'error': 'eBay search manager not available'}

        # Get exchange rate
        if not exchange_rate:
            exchange_rate = fetch_exchange_rate()

        verified_items = []
        flagged_items = []
        total_cost_jpy = 0
        total_revenue_usd = 0

        total = len(cart_items)

        for i, item in enumerate(cart_items, 1):
            if progress_callback:
                progress_callback(i, total, f"Searching eBay for: {item.get('title', 'Unknown')[:50]}...")

            # Skip sold out items
            if item.get('status') == 'Sold Out':
                self.logger.info(f"Skipping sold out item: {item.get('title')}")
                continue

            # Search eBay using title
            ebay_results = self._search_ebay_text(item)

            if ebay_results and ebay_results['sold_count'] > 0:
                # Calculate ROI
                avg_price_usd = ebay_results['avg_price_usd']
                cost_usd = item['price_jpy'] / exchange_rate
                profit_usd = avg_price_usd - cost_usd
                roi_percent = (profit_usd / cost_usd * 100) if cost_usd > 0 else 0

                verified_item = {
                    **item,
                    'ebay_avg_price_usd': avg_price_usd,
                    'ebay_sold_count': ebay_results['sold_count'],
                    'cost_usd': cost_usd,
                    'profit_usd': profit_usd,
                    'roi_percent': roi_percent,
                    'verified_at': datetime.now().isoformat()
                }

                verified_items.append(verified_item)
                total_cost_jpy += item['price_jpy']
                total_revenue_usd += avg_price_usd

                # Flag items with low ROI (< 20%)
                if roi_percent < 20:
                    flagged_items.append({
                        **verified_item,
                        'flag_reason': f'Low ROI ({roi_percent:.1f}%)'
                    })

            else:
                # No eBay results found - flag as risky
                flagged_items.append({
                    **item,
                    'flag_reason': 'No eBay sold listings found',
                    'roi_percent': 0,
                    'ebay_sold_count': 0
                })

        # Calculate aggregate metrics
        total_cost_usd = total_cost_jpy / exchange_rate
        profit_usd = total_revenue_usd - total_cost_usd
        roi_percent = (profit_usd / total_cost_usd * 100) if total_cost_usd > 0 else 0

        return {
            'total_cost_jpy': total_cost_jpy,
            'total_cost_usd': round(total_cost_usd, 2),
            'est_revenue_usd': round(total_revenue_usd, 2),
            'profit_usd': round(profit_usd, 2),
            'roi_percent': round(roi_percent, 2),
            'exchange_rate': exchange_rate,
            'items_verified': len(verified_items),
            'items_flagged': len(flagged_items),
            'verified_items': verified_items,
            'flagged_items': flagged_items,
            'method': 'text_based',
            'verified_at': datetime.now().isoformat()
        }

    def verify_cart_image_based(self, cart_items: List[Dict],
                                exchange_rate: float = None,
                                min_similarity: float = 70.0,
                                use_ransac: bool = False,
                                progress_callback=None) -> Dict:
        """
        Verify cart ROI using image-based eBay comparison (Image Compare All)

        Args:
            cart_items: List of cart item dicts
            exchange_rate: USD/JPY rate (auto-fetched if not provided)
            min_similarity: Minimum similarity threshold (default: 70%)
            use_ransac: Enable RANSAC geometric verification
            progress_callback: Optional callback(current, total, message)

        Returns:
            dict: Same format as verify_cart_text_based plus 'similarity' data
        """
        if not self.csv_comparison_manager:
            return {'error': 'CSV comparison manager not available'}

        # Get exchange rate
        if not exchange_rate:
            exchange_rate = fetch_exchange_rate()

        verified_items = []
        flagged_items = []
        total_cost_jpy = 0
        total_revenue_usd = 0

        total = len(cart_items)

        for i, item in enumerate(cart_items, 1):
            if progress_callback:
                progress_callback(i, total, f"Comparing images for: {item.get('title', 'Unknown')[:50]}...")

            # Skip sold out items
            if item.get('status') == 'Sold Out':
                self.logger.info(f"Skipping sold out item: {item.get('title')}")
                continue

            # Search eBay with image comparison
            comparison_results = self._search_ebay_with_images(
                item,
                use_ransac=use_ransac
            )

            if comparison_results and comparison_results['matches']:
                # Filter by minimum similarity
                valid_matches = [
                    m for m in comparison_results['matches']
                    if m.get('similarity', 0) >= min_similarity
                ]

                if valid_matches:
                    # Calculate average price from valid matches
                    avg_price_usd = sum(m['price_usd'] for m in valid_matches) / len(valid_matches)
                    avg_similarity = sum(m['similarity'] for m in valid_matches) / len(valid_matches)

                    # Calculate ROI
                    cost_usd = item['price_jpy'] / exchange_rate
                    profit_usd = avg_price_usd - cost_usd
                    roi_percent = (profit_usd / cost_usd * 100) if cost_usd > 0 else 0

                    verified_item = {
                        **item,
                        'ebay_avg_price_usd': avg_price_usd,
                        'ebay_match_count': len(valid_matches),
                        'avg_similarity': avg_similarity,
                        'cost_usd': cost_usd,
                        'profit_usd': profit_usd,
                        'roi_percent': roi_percent,
                        'verified_at': datetime.now().isoformat(),
                        'best_match': valid_matches[0] if valid_matches else None
                    }

                    verified_items.append(verified_item)
                    total_cost_jpy += item['price_jpy']
                    total_revenue_usd += avg_price_usd

                    # Flag items with low ROI or low similarity
                    if roi_percent < 20:
                        flagged_items.append({
                            **verified_item,
                            'flag_reason': f'Low ROI ({roi_percent:.1f}%)'
                        })
                    elif avg_similarity < min_similarity + 10:  # Close to threshold
                        flagged_items.append({
                            **verified_item,
                            'flag_reason': f'Low similarity ({avg_similarity:.1f}%)'
                        })
                else:
                    # Matches found but below similarity threshold
                    flagged_items.append({
                        **item,
                        'flag_reason': f'No matches above {min_similarity}% similarity',
                        'roi_percent': 0,
                        'ebay_match_count': 0
                    })
            else:
                # No matches found
                flagged_items.append({
                    **item,
                    'flag_reason': 'No similar eBay listings found',
                    'roi_percent': 0,
                    'ebay_match_count': 0
                })

        # Calculate aggregate metrics
        total_cost_usd = total_cost_jpy / exchange_rate
        profit_usd = total_revenue_usd - total_cost_usd
        roi_percent = (profit_usd / total_cost_usd * 100) if total_cost_usd > 0 else 0

        return {
            'total_cost_jpy': total_cost_jpy,
            'total_cost_usd': round(total_cost_usd, 2),
            'est_revenue_usd': round(total_revenue_usd, 2),
            'profit_usd': round(profit_usd, 2),
            'roi_percent': round(roi_percent, 2),
            'exchange_rate': exchange_rate,
            'items_verified': len(verified_items),
            'items_flagged': len(flagged_items),
            'verified_items': verified_items,
            'flagged_items': flagged_items,
            'method': 'image_based',
            'min_similarity': min_similarity,
            'use_ransac': use_ransac,
            'verified_at': datetime.now().isoformat()
        }

    def verify_cart_hybrid(self, cart_items: List[Dict],
                          exchange_rate: float = None,
                          min_similarity: float = 70.0,
                          use_ransac: bool = False,
                          progress_callback=None) -> Dict:
        """
        Verify cart ROI using BOTH text and image comparison (most accurate)

        First tries image comparison, falls back to text search if no matches.

        Args:
            cart_items: List of cart item dicts
            exchange_rate: USD/JPY rate
            min_similarity: Minimum similarity for image matching
            use_ransac: Enable RANSAC verification
            progress_callback: Optional callback

        Returns:
            dict: Verification results with method per item
        """
        if not exchange_rate:
            exchange_rate = get_exchange_rate()

        verified_items = []
        flagged_items = []
        total_cost_jpy = 0
        total_revenue_usd = 0

        total = len(cart_items)

        for i, item in enumerate(cart_items, 1):
            if progress_callback:
                progress_callback(i, total, f"Verifying: {item.get('title', 'Unknown')[:50]}...")

            # Skip sold out
            if item.get('status') == 'Sold Out':
                continue

            # Try image comparison first
            image_results = self._search_ebay_with_images(item, use_ransac=use_ransac)

            if image_results and image_results['matches']:
                valid_matches = [m for m in image_results['matches']
                               if m.get('similarity', 0) >= min_similarity]

                if valid_matches:
                    # Image comparison success
                    avg_price_usd = sum(m['price_usd'] for m in valid_matches) / len(valid_matches)
                    cost_usd = item['price_jpy'] / exchange_rate
                    roi_percent = ((avg_price_usd - cost_usd) / cost_usd * 100) if cost_usd > 0 else 0

                    verified_items.append({
                        **item,
                        'ebay_avg_price_usd': avg_price_usd,
                        'roi_percent': roi_percent,
                        'method_used': 'image',
                        'similarity': sum(m['similarity'] for m in valid_matches) / len(valid_matches)
                    })

                    total_cost_jpy += item['price_jpy']
                    total_revenue_usd += avg_price_usd
                    continue

            # Fall back to text search
            text_results = self._search_ebay_text(item)

            if text_results and text_results['sold_count'] > 0:
                # Text search success
                avg_price_usd = text_results['avg_price_usd']
                cost_usd = item['price_jpy'] / exchange_rate
                roi_percent = ((avg_price_usd - cost_usd) / cost_usd * 100) if cost_usd > 0 else 0

                verified_items.append({
                    **item,
                    'ebay_avg_price_usd': avg_price_usd,
                    'roi_percent': roi_percent,
                    'method_used': 'text'
                })

                total_cost_jpy += item['price_jpy']
                total_revenue_usd += avg_price_usd
            else:
                # No results from either method
                flagged_items.append({
                    **item,
                    'flag_reason': 'No eBay results (image or text)',
                    'roi_percent': 0
                })

        total_cost_usd = total_cost_jpy / exchange_rate
        profit_usd = total_revenue_usd - total_cost_usd
        roi_percent = (profit_usd / total_cost_usd * 100) if total_cost_usd > 0 else 0

        return {
            'total_cost_jpy': total_cost_jpy,
            'total_cost_usd': round(total_cost_usd, 2),
            'est_revenue_usd': round(total_revenue_usd, 2),
            'profit_usd': round(profit_usd, 2),
            'roi_percent': round(roi_percent, 2),
            'exchange_rate': exchange_rate,
            'items_verified': len(verified_items),
            'items_flagged': len(flagged_items),
            'verified_items': verified_items,
            'flagged_items': flagged_items,
            'method': 'hybrid',
            'verified_at': datetime.now().isoformat()
        }

    # Helper methods

    def _search_ebay_text(self, item: Dict) -> Optional[Dict]:
        """Search eBay using text-based search (Compare All)"""
        if not self.ebay_search_manager:
            return None

        try:
            # Extract keywords from title
            title = item.get('title', '')

            # Use eBay search manager
            results = self.ebay_search_manager.search_ebay_sold_listings(
                keyword=title,
                max_results=20
            )

            if results:
                # Calculate average price
                prices = [r['price'] for r in results if r.get('price', 0) > 0]
                if prices:
                    return {
                        'avg_price_usd': sum(prices) / len(prices),
                        'sold_count': len(results),
                        'results': results
                    }

        except Exception as e:
            self.logger.error(f"Error in text search for {item.get('title')}: {e}")

        return None

    def _search_ebay_with_images(self, item: Dict, use_ransac: bool = False) -> Optional[Dict]:
        """Search eBay with image comparison (Image Compare All)"""
        if not self.csv_comparison_manager:
            return None

        try:
            # Create temporary CSV row for comparison
            csv_row = {
                'Title': item.get('title', ''),
                'Price': item.get('price_jpy', 0),
                'Image': item.get('image_url', ''),
                'URL': item.get('product_url', '')
            }

            # Use image comparison manager
            matches = self.csv_comparison_manager.compare_single_item(
                csv_row,
                use_ransac=use_ransac
            )

            if matches:
                return {
                    'matches': matches,
                    'match_count': len(matches)
                }

        except Exception as e:
            self.logger.error(f"Error in image search for {item.get('title')}: {e}")

        return None
