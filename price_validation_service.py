#!/usr/bin/env python3
"""
Price Validation Service

Integrates sold listing image matching with the main scraper to provide
automated price validation and market analysis.
"""

import logging
import asyncio
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import asdict
from sold_listing_matcher import SoldListingMatcher, ImageMatchResult, SoldListing


class PriceValidationService:
    """Service for validating product prices using sold listing image matching"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.matcher = None

        # Configuration settings
        self.headless = config.get('price_validation', {}).get('headless', True)
        self.similarity_threshold = config.get('price_validation', {}).get('similarity_threshold', 0.7)
        self.max_results = config.get('price_validation', {}).get('max_results', 5)
        self.days_back = config.get('price_validation', {}).get('days_back', 90)
        self.enabled = config.get('price_validation', {}).get('enabled', False)

    async def validate_product_price(self,
                                   product_data: Dict[str, Any],
                                   image_path: str) -> Optional[Dict[str, Any]]:
        """
        Validate a product's price by comparing with sold listings

        Args:
            product_data: Product information from scraper
            image_path: Path to the product image

        Returns:
            Dict with validation results or None if validation failed
        """
        if not self.enabled:
            logging.debug("Price validation is disabled")
            return None

        try:
            # Initialize matcher if needed
            if not self.matcher:
                self.matcher = SoldListingMatcher(
                    headless=self.headless,
                    similarity_threshold=self.similarity_threshold
                )

            # Create search term from product data
            search_term = self._create_search_term(product_data)

            logging.info(f"Validating price for: {search_term}")

            # Find matching sold listings
            result = await self.matcher.find_matching_sold_listings(
                reference_image_path=image_path,
                search_term=search_term,
                max_results=self.max_results,
                days_back=self.days_back
            )

            # Process and return results
            return self._process_validation_result(product_data, result)

        except Exception as e:
            logging.error(f"Error in price validation: {e}")
            return None

    def _create_search_term(self, product_data: Dict[str, Any]) -> str:
        """Create optimal search term from product data"""
        # Extract key information
        title = product_data.get('title', '').strip()
        shop = product_data.get('shop', '').strip()

        # Use title as base, but clean it up
        search_term = title

        # Remove common Japanese shop/category terms that might not help eBay search
        terms_to_remove = [
            'まんだらけ', 'mandarake', '中古', '新品', '未開封',
            '限定', '特典', '初回', '通常版', '完全版'
        ]

        for term in terms_to_remove:
            search_term = search_term.replace(term, ' ')

        # Clean up extra spaces
        search_term = ' '.join(search_term.split())

        # Don't add 'sold' - it's handled by eBay's LH_Sold=1 parameter
        # search_term += ' sold'

        return search_term

    def _process_validation_result(self,
                                 product_data: Dict[str, Any],
                                 result: ImageMatchResult) -> Dict[str, Any]:
        """Process validation result and create report"""

        # Extract original price from product data
        original_price = product_data.get('price', 0)
        original_currency = product_data.get('currency', 'JPY')

        # Create validation report
        validation_report = {
            'product_title': product_data.get('title', 'Unknown'),
            'original_price': original_price,
            'original_currency': original_currency,
            'validation_timestamp': asyncio.get_event_loop().time(),

            # Match results
            'matches_found': result.matches_found,
            'confidence_level': result.confidence,
            'similarity_threshold': self.similarity_threshold,

            # Price analysis
            'market_data': {},
            'price_recommendation': {},
            'matches': []
        }

        if result.matches_found > 0:
            # Add market data
            validation_report['market_data'] = {
                'average_sold_price': result.average_price,
                'price_range_min': result.price_range[0],
                'price_range_max': result.price_range[1],
                'currency': 'USD',  # eBay prices are typically USD
                'sample_size': result.matches_found
            }

            # Convert JPY to USD for comparison (rough estimate)
            usd_estimate = original_price / 150 if original_currency == 'JPY' else original_price

            # Calculate price recommendation
            avg_price = result.average_price
            price_difference = avg_price - usd_estimate
            percentage_diff = (price_difference / avg_price * 100) if avg_price > 0 else 0

            validation_report['price_recommendation'] = {
                'estimated_usd_value': usd_estimate,
                'market_average_usd': avg_price,
                'price_difference_usd': price_difference,
                'percentage_difference': percentage_diff,
                'recommendation': self._get_price_recommendation(percentage_diff, result.confidence)
            }

            # Add match details
            validation_report['matches'] = [
                {
                    'title': match.title,
                    'price': match.price,
                    'currency': match.currency,
                    'sold_date': match.sold_date,
                    'similarity_score': match.image_similarity,
                    'confidence_score': match.confidence_score,
                    'listing_url': match.listing_url
                }
                for match in result.all_matches
            ]

        return validation_report

    def _get_price_recommendation(self, percentage_diff: float, confidence: str) -> str:
        """Generate price recommendation based on market analysis"""

        if confidence == "low":
            return "insufficient_data"

        if percentage_diff > 20:
            return "overpriced"
        elif percentage_diff > 10:
            return "slightly_overpriced"
        elif percentage_diff < -20:
            return "underpriced"
        elif percentage_diff < -10:
            return "slightly_underpriced"
        else:
            return "fairly_priced"

    async def batch_validate_products(self,
                                    products: List[Dict[str, Any]],
                                    image_directory: str) -> List[Dict[str, Any]]:
        """
        Validate multiple products in batch

        Args:
            products: List of product data dictionaries
            image_directory: Directory containing product images

        Returns:
            List of validation results
        """
        results = []

        try:
            # Initialize matcher once for batch processing
            if not self.matcher:
                self.matcher = SoldListingMatcher(
                    headless=self.headless,
                    similarity_threshold=self.similarity_threshold
                )

            for i, product in enumerate(products):
                try:
                    logging.info(f"Validating product {i+1}/{len(products)}")

                    # Find corresponding image file
                    image_path = self._find_product_image(product, image_directory)

                    if image_path:
                        result = await self.validate_product_price(product, image_path)
                        if result:
                            results.append(result)

                        # Add delay between requests to be respectful
                        await asyncio.sleep(2)
                    else:
                        logging.warning(f"No image found for product: {product.get('title', 'Unknown')}")

                except Exception as e:
                    logging.error(f"Error validating product {i}: {e}")
                    continue

        except Exception as e:
            logging.error(f"Error in batch validation: {e}")

        return results

    def _find_product_image(self, product: Dict[str, Any], image_directory: str) -> Optional[str]:
        """Find the image file for a product"""
        try:
            image_dir = Path(image_directory)
            if not image_dir.exists():
                return None

            # Try to match by product ID or title
            product_id = product.get('id', '')
            title = product.get('title', '')

            # Common image extensions
            extensions = ['.jpg', '.jpeg', '.png', '.webp']

            # Try product ID first
            if product_id:
                for ext in extensions:
                    image_path = image_dir / f"{product_id}{ext}"
                    if image_path.exists():
                        return str(image_path)

            # Try first few words of title
            if title:
                # Clean title for filename
                clean_title = ''.join(c for c in title if c.isalnum() or c in ' -_')
                title_words = clean_title.split()[:3]  # First 3 words
                title_prefix = '_'.join(title_words)

                for ext in extensions:
                    # Try exact match
                    image_path = image_dir / f"{title_prefix}{ext}"
                    if image_path.exists():
                        return str(image_path)

                    # Try partial matches
                    for file_path in image_dir.glob(f"*{title_words[0]}*{ext}"):
                        return str(file_path)

        except Exception as e:
            logging.debug(f"Error finding product image: {e}")

        return None

    async def cleanup(self):
        """Clean up resources"""
        if self.matcher:
            await self.matcher.cleanup()

    async def __aenter__(self):
        """Context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.cleanup()


# Integration functions for existing scraper
def add_price_validation_to_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Add price validation configuration to existing config"""

    if 'price_validation' not in config:
        config['price_validation'] = {
            'enabled': False,  # Disabled by default
            'headless': True,
            'similarity_threshold': 0.7,
            'max_results': 5,
            'days_back': 90,
            'batch_delay': 2.0
        }

    return config


async def validate_scraped_products(products: List[Dict[str, Any]],
                                  config: Dict[str, Any],
                                  image_directory: str) -> List[Dict[str, Any]]:
    """
    Convenience function to validate scraped products

    Args:
        products: List of scraped product data
        config: Scraper configuration
        image_directory: Directory with product images

    Returns:
        List of products with added validation data
    """
    if not config.get('price_validation', {}).get('enabled', False):
        logging.info("Price validation is disabled")
        return products

    async with PriceValidationService(config) as validator:
        validation_results = await validator.batch_validate_products(products, image_directory)

        # Merge validation results back into product data
        for product in products:
            # Find matching validation result
            for validation in validation_results:
                if validation['product_title'] == product.get('title'):
                    product['price_validation'] = validation
                    break

    return products


if __name__ == '__main__':
    # Example usage and testing
    import json

    async def test_validation():
        # Test configuration
        test_config = {
            'price_validation': {
                'enabled': True,
                'headless': False,  # Show browser for testing
                'similarity_threshold': 0.6,
                'max_results': 3,
                'days_back': 60
            }
        }

        # Test product data
        test_product = {
            'title': 'Yura Kano Magical Girlfriend Photo Book',
            'price': 3000,
            'currency': 'JPY',
            'shop': 'Mandarake',
            'id': 'test_001'
        }

        print("=== PRICE VALIDATION SERVICE TEST ===")
        print(f"Product: {test_product['title']}")
        print(f"Original price: {test_product['price']} {test_product['currency']}")
        print()

        # Test validation (would need actual image file)
        if len(sys.argv) > 1:
            image_path = sys.argv[1]

            async with PriceValidationService(test_config) as validator:
                result = await validator.validate_product_price(test_product, image_path)

                if result:
                    print("=== VALIDATION RESULTS ===")
                    print(json.dumps(result, indent=2, default=str))
                else:
                    print("No validation results obtained")
        else:
            print("Usage: python price_validation_service.py <image_path>")
            print("Example: python price_validation_service.py test_image.jpg")

    import sys
    if len(sys.argv) > 1:
        asyncio.run(test_validation())
    else:
        print("Price Validation Service")
        print("Run with image path to test validation")