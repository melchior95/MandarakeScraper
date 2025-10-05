#!/usr/bin/env python3
"""
Sold Listing Image Matcher - Requests Version

Uses the existing browser_mimic.py system that already works with eBay,
instead of Playwright which gets blocked more easily.
"""

import logging
import re
import cv2
import numpy as np
import requests
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

from browser_mimic import BrowserMimic
from search_optimizer import SearchOptimizer


@dataclass
class SoldListing:
    """Data structure for a sold listing"""
    title: str
    price: float
    currency: str
    sold_date: str
    image_url: str
    listing_url: str
    image_similarity: float = 0.0
    confidence_score: float = 0.0


@dataclass
class ImageMatchResult:
    """Result of image matching analysis"""
    matches_found: int
    best_match: Optional[SoldListing]
    all_matches: List[SoldListing]
    average_price: float
    price_range: Tuple[float, float]
    confidence: str


class SoldListingMatcherRequests:
    """Matches product images with sold listings using requests (browser mimic)"""

    def __init__(self, similarity_threshold: float = 0.7, debug_output_dir: str = None):
        self.similarity_threshold = similarity_threshold
        self.search_optimizer = SearchOptimizer()

        # Image comparison settings
        self.image_size = (400, 400)  # Larger size for better feature detection
        self.feature_detector = cv2.ORB_create(nfeatures=2000)  # More features for better matching

        # Browser mimic for eBay requests
        self.browser = BrowserMimic("ebay_sold_listings.pkl")

        # Cache for downloaded images
        self.image_cache = {}

        # Debug output directory
        self.debug_output_dir = debug_output_dir
        if self.debug_output_dir:
            import os
            os.makedirs(self.debug_output_dir, exist_ok=True)
            logging.info(f"Debug output directory: {self.debug_output_dir}")

    def find_matching_sold_listings(self,
                                   reference_image_path: str,
                                   search_term: str,
                                   max_results: int = 5,
                                   days_back: int = 90) -> ImageMatchResult:
        """
        Find sold listings that match the reference image

        Args:
            reference_image_path: Path to the product image to match
            search_term: Search term for finding listings
            max_results: Maximum number of results to analyze
            days_back: How many days back to search for sold items

        Returns:
            ImageMatchResult with matches and pricing data
        """
        try:
            logging.info(f"Starting image matching for: {search_term}")

            # Step 1: Load and prepare reference image
            reference_features = self._load_and_process_image(reference_image_path)
            if reference_features is None:
                raise ValueError("Could not process reference image")

            # Step 2: Search for sold listings (use exact search term, no optimization needed)
            listings_to_analyze = self._search_sold_listings(search_term, max_results, days_back)

            logging.info(f"Found {len(listings_to_analyze)} unique sold listings to analyze")

            # Step 3: Compare images and find matches
            matches = self._compare_images_with_listings(
                reference_features, listings_to_analyze
            )

            # Step 4: Analyze results
            result = self._analyze_matches(matches)

            logging.info(f"Image matching complete: {result.matches_found} matches found")
            return result

        except Exception as e:
            logging.error(f"Error in image matching: {e}")
            return ImageMatchResult(
                matches_found=0,
                best_match=None,
                all_matches=[],
                average_price=0.0,
                price_range=(0.0, 0.0),
                confidence="error"
            )

    def _search_sold_listings(self,
                             search_term: str,
                             max_results: int,
                             days_back: int) -> List[SoldListing]:
        """Search for sold listings using browser mimic (requests)"""
        try:
            # Build eBay sold listings URL
            sold_url = self._build_ebay_sold_url(search_term, days_back)

            logging.info(f"Searching eBay sold listings: {search_term}")

            # Add extra delay before eBay search to reduce blocking
            self.browser.add_ebay_search_delay()

            # Use browser mimic to get the page
            response = self.browser.get(sold_url)

            if response.status_code != 200:
                logging.warning(f"eBay returned status {response.status_code}")
                return []

            # Check for blocking indicators
            if "blocked" in response.text.lower() or "captcha" in response.text.lower():
                logging.warning("eBay may be blocking requests")
                return []

            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Debug: Save the HTML response for inspection
            if self.debug_output_dir:
                import os
                html_debug_path = os.path.join(self.debug_output_dir, f"ebay_response_{search_term.replace(' ', '_')}.html")
                with open(html_debug_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                logging.info(f"Saved eBay HTML response to: {html_debug_path}")

            # Check for common blocking indicators
            page_text = response.text.lower()
            page_title = soup.find('title')
            title_text = page_title.get_text() if page_title else ""

            blocking_indicators = [
                'blocked', 'captcha', 'robot', 'automation',
                'pardon our interruption', 'access denied', 'rate limit'
            ]

            if any(indicator in page_text for indicator in blocking_indicators):
                logging.warning(f"eBay blocking detected: '{title_text}'")
                logging.warning("eBay is likely rate limiting or blocking automated requests")
                logging.warning("Try waiting a few minutes before retrying, or use different search terms")
                return []

            # Extract listing data
            listings = self._extract_listing_data_from_soup(soup, max_results)

            logging.info(f"Extracted {len(listings)} listings for '{search_term}'")
            return listings

        except Exception as e:
            logging.error(f"Error searching sold listings: {e}")

            # Provide helpful feedback for common issues
            if "timeout" in str(e).lower() or "connection" in str(e).lower():
                logging.warning("Network timeout - eBay may be slow or blocking requests")

            return []

    def _build_ebay_sold_url(self, search_term: str, days_back: int) -> str:
        """Build eBay sold listings URL"""
        base_url = "https://www.ebay.com/sch/i.html"

        # Clean search term
        clean_term = search_term.strip()

        params = {
            '_nkw': clean_term,
            '_sacat': '0',
            'LH_Sold': '1',
            'LH_Complete': '1',
            '_sop': '12',  # Sort by ending soonest
            '_ipg': '25'   # 25 results per page
        }

        # Build URL
        param_parts = []
        for k, v in params.items():
            if k == '_nkw':
                # Preserve + for spaces in search term
                encoded_value = clean_term.replace(' ', '+')
            else:
                encoded_value = str(v)
            param_parts.append(f"{k}={encoded_value}")

        url = f"{base_url}?{'&'.join(param_parts)}"
        logging.debug(f"Built eBay URL: {url}")
        return url

    def _extract_listing_data_from_soup(self, soup: BeautifulSoup, max_results: int) -> List[SoldListing]:
        """Extract sold listing data from BeautifulSoup - updated for modern eBay structure"""
        listings = []

        try:
            # Debug: Check page title and basic content
            page_title = soup.find('title')
            if page_title:
                logging.info(f"eBay page title: {page_title.get_text()[:100]}...")
            else:
                logging.warning("No page title found")

            # First, try to extract prefetch images (modern eBay approach)
            prefetch_listings = self._extract_from_prefetch_images(soup, max_results)
            if prefetch_listings:
                logging.info(f"Found {len(prefetch_listings)} listings from prefetch images")
                return prefetch_listings

            # Fallback: Try traditional selectors
            item_selectors = [
                '.s-item',
                '[data-view="mi:1686|iid:1"]',
                '.srp-result',
                '.s-item__wrapper',
                '.it-ttl',  # Alternative eBay selector
                '.lvtitle'  # Another alternative
            ]

            items = []
            for selector in item_selectors:
                items = soup.select(selector)
                if items:
                    logging.info(f"Found {len(items)} items using selector: {selector}")
                    break
                else:
                    logging.debug(f"No items found with selector: {selector}")

            if not items:
                logging.warning("No listing items found on page")

                # Debug: Check what content is actually on the page
                body_text = soup.get_text()[:500] if soup.find('body') else "No body found"
                logging.debug(f"Page content sample: {body_text}")

                # Check for common eBay page elements
                common_elements = soup.select('.srp-results, .listingscnt, .srp-river-results')
                if common_elements:
                    logging.info(f"Found some eBay page elements: {len(common_elements)}")
                else:
                    logging.warning("No recognizable eBay page structure found")

                return []

            logging.info(f"Processing {min(len(items), max_results)} items...")

            for i, item in enumerate(items[:max_results]):
                try:
                    logging.debug(f"Processing item {i + 1}/{min(len(items), max_results)}")
                    listing = self._extract_single_listing(item)
                    if listing and listing.price > 0 and listing.image_url:
                        listings.append(listing)
                        logging.info(f"Successfully extracted listing {i + 1}: {listing.title[:50]}...")
                    else:
                        if listing:
                            logging.debug(f"Skipped listing {i + 1}: price={listing.price}, has_image={bool(listing.image_url)}")
                        else:
                            logging.debug(f"Failed to extract listing {i + 1}")

                except Exception as e:
                    logging.debug(f"Error extracting listing {i + 1}: {e}")
                    continue

        except Exception as e:
            logging.error(f"Error extracting listings from soup: {e}")

        logging.info(f"Successfully extracted {len(listings)} valid listings")
        return listings

    def _extract_from_prefetch_images(self, soup: BeautifulSoup, max_results: int) -> List[SoldListing]:
        """Extract listings from eBay's prefetch images (modern eBay approach)"""
        listings = []

        try:
            # Find the prefetch image container
            prefetch_container = soup.select_one('.s-prefetch-image')
            if not prefetch_container:
                logging.debug("No prefetch image container found")
                return []

            # Extract all prefetch images
            prefetch_images = prefetch_container.select('img[src*="ebayimg.com"]')
            if not prefetch_images:
                logging.debug("No eBay images found in prefetch container")
                return []

            logging.info(f"Found {len(prefetch_images)} prefetch images")

            # Extract title information from page content
            page_title = soup.find('title')
            search_term = ""
            if page_title:
                title_text = page_title.get_text()
                # Extract search term from title like "Pokemon Card for sale | eBay"
                if " for sale" in title_text:
                    search_term = title_text.split(" for sale")[0]
                elif ":" in title_text:
                    search_term = title_text.split(":")[0]

            # Generate listings from prefetch images
            for i, img in enumerate(prefetch_images[:max_results]):
                try:
                    img_src = img.get('src')
                    if not img_src:
                        continue

                    # Create a basic listing with the image
                    # Since we can't get exact titles/prices from prefetch images,
                    # we'll create placeholder listings that will be useful for image comparison
                    listing = SoldListing(
                        title=f"{search_term} - Listing {i+1}" if search_term else f"eBay Listing {i+1}",
                        price=1.0,  # Placeholder price to pass validation
                        currency="USD",
                        sold_date="Recent",
                        image_url=img_src,
                        listing_url=f"https://www.ebay.com/listing/{i+1}"  # Placeholder URL
                    )

                    listings.append(listing)
                    logging.debug(f"Added prefetch listing {i+1}: {img_src[:80]}...")

                except Exception as e:
                    logging.warning(f"Error processing prefetch image {i+1}: {e}")
                    continue

            logging.info(f"Created {len(listings)} listings from prefetch images")
            return listings

        except Exception as e:
            logging.error(f"Error extracting from prefetch images: {e}")
            return []

    def _extract_single_listing(self, item) -> Optional[SoldListing]:
        """Extract data from a single listing item"""
        try:
            # Extract title
            title_selectors = [
                '.s-item__title',
                '.s-item__link',
                'h3.s-item__title',
                'a .s-item__title'
            ]
            title = ""
            for selector in title_selectors:
                title_elem = item.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break

            if not title or title.lower() in ['shop on ebay', 'new listing']:
                return None

            # Extract price
            price_selectors = [
                '.s-item__price',
                '.notranslate',
                '.s-item__price .notranslate'
            ]
            price_text = ""
            for selector in price_selectors:
                price_elem = item.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    break

            price, currency = self._parse_price(price_text)
            if price <= 0:
                return None

            # Extract sold date
            sold_date = "Unknown"
            date_selectors = [
                '.s-item__title--tag',
                '.s-item__purchase-options-with-icon',
                '.s-item__ended-date'
            ]
            for selector in date_selectors:
                date_elem = item.select_one(selector)
                if date_elem:
                    sold_date = date_elem.get_text(strip=True)
                    break

            # Extract image URL
            image_url = ""
            img_selectors = [
                '.s-item__image img',
                'img.s-item__image',
                '.s-item__wrapper img'
            ]
            for selector in img_selectors:
                img_elem = item.select_one(selector)
                if img_elem:
                    image_url = img_elem.get('src') or img_elem.get('data-src') or ""
                    if image_url:
                        # Ensure it's a full URL
                        if image_url.startswith('//'):
                            image_url = 'https:' + image_url
                        elif image_url.startswith('/'):
                            image_url = 'https://www.ebay.com' + image_url
                        break

            # Extract listing URL
            listing_url = ""
            link_selectors = [
                '.s-item__link',
                'a[href*="/itm/"]'
            ]
            for selector in link_selectors:
                link_elem = item.select_one(selector)
                if link_elem:
                    listing_url = link_elem.get('href', '')
                    if listing_url.startswith('/'):
                        listing_url = 'https://www.ebay.com' + listing_url
                    break

            return SoldListing(
                title=title,
                price=price,
                currency=currency,
                sold_date=sold_date,
                image_url=image_url,
                listing_url=listing_url
            )

        except Exception as e:
            logging.debug(f"Error extracting single listing: {e}")
            return None

    def _parse_price(self, price_text: str) -> Tuple[float, str]:
        """Parse price text and extract amount and currency"""
        try:
            # Clean up the price text
            price_text = price_text.replace('Sold  ', '').replace('to ', '').strip()

            # Extract currency and amount using regex
            price_match = re.search(r'([£$€¥])([\d,]+\.?\d*)', price_text)
            if price_match:
                currency_symbol = price_match.group(1)
                amount_str = price_match.group(2).replace(',', '')
                amount = float(amount_str)

                # Map currency symbols
                currency_map = {'$': 'USD', '£': 'GBP', '€': 'EUR', '¥': 'JPY'}
                currency = currency_map.get(currency_symbol, 'USD')

                return amount, currency

        except Exception as e:
            logging.debug(f"Error parsing price '{price_text}': {e}")

        return 0.0, 'USD'

    def _compare_images_with_listings(self,
                                     reference_features: dict,
                                     listings: List[SoldListing]) -> List[SoldListing]:
        """Compare reference image with listing images"""
        matches = []

        logging.info(f"Starting image comparison with {len(listings)} listings")
        logging.info(f"Similarity threshold: {self.similarity_threshold:.2f}")

        for i, listing in enumerate(listings):
            try:
                logging.info(f"\n=== Comparing listing {i + 1}/{len(listings)} ===")
                logging.info(f"Title: {listing.title[:60]}...")
                logging.info(f"Price: ${listing.price}")
                logging.info(f"Image URL: {listing.image_url}")

                # Download and process listing image
                listing_features = self._download_and_process_image(listing.image_url, i)

                if listing_features is not None:
                    # Calculate similarity
                    similarity = self._calculate_image_similarity(reference_features, listing_features)

                    logging.info(f"Similarity score: {similarity:.3f} (threshold: {self.similarity_threshold:.3f})")

                    if similarity >= self.similarity_threshold:
                        listing.image_similarity = similarity
                        listing.confidence_score = self._calculate_confidence_score(listing, similarity)
                        matches.append(listing)

                        logging.info(f"✅ MATCH FOUND! Similarity: {similarity:.3f}")
                    else:
                        logging.info(f"❌ Below threshold. Similarity: {similarity:.3f} < {self.similarity_threshold:.3f}")
                else:
                    logging.warning(f"❌ Could not process image for listing {i + 1}")

            except Exception as e:
                logging.error(f"Error comparing image for listing {i + 1}: {e}")
                continue

        logging.info(f"\n=== COMPARISON COMPLETE ===")
        logging.info(f"Total matches found: {len(matches)}")

        # Sort by similarity score
        matches.sort(key=lambda x: x.image_similarity, reverse=True)
        return matches

    def _load_and_process_image(self, image_path: str) -> Optional[dict]:
        """Load and extract features from reference image"""
        try:
            if not Path(image_path).exists():
                raise FileNotFoundError(f"Reference image not found: {image_path}")

            logging.info(f"Loading reference image: {image_path}")

            # Load image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")

            logging.info(f"Reference image loaded: {image.shape} shape")

            # Save debug copy of reference image if requested
            if self.debug_output_dir:
                import os
                debug_path = os.path.join(self.debug_output_dir, "reference_image.jpg")
                cv2.imwrite(debug_path, image)
                logging.info(f"Saved reference image copy: {debug_path}")

            # Extract features
            features = self._extract_image_features(image)

            if features is not None:
                feature_count = len(features) if hasattr(features, '__len__') else "histogram"
                logging.info(f"Extracted features from reference: {feature_count} features")
            else:
                logging.warning("No features extracted from reference image")

            return features

        except Exception as e:
            logging.error(f"Error processing reference image: {e}")
            return None

    def _download_and_process_image(self, image_url: str, listing_index: int = 0) -> Optional[dict]:
        """Download and process image from URL"""
        try:
            # Check cache first
            if image_url in self.image_cache:
                logging.debug(f"Using cached image: {image_url}")
                return self.image_cache[image_url]

            logging.info(f"Downloading image {listing_index + 1}: {image_url}")

            # Download image using browser mimic
            response = self.browser.get(image_url)

            if response.status_code != 200:
                logging.warning(f"Failed to download image (status {response.status_code}): {image_url}")
                return None

            logging.info(f"Downloaded image {listing_index + 1}: {len(response.content)} bytes")

            # Convert to OpenCV format
            image_array = np.frombuffer(response.content, np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            if image is None:
                logging.warning(f"Failed to decode image: {image_url}")
                return None

            logging.info(f"Decoded image {listing_index + 1}: {image.shape} shape")

            # Save debug image if requested
            if self.debug_output_dir:
                import os
                filename = f"listing_{listing_index + 1:02d}.jpg"
                debug_path = os.path.join(self.debug_output_dir, filename)
                cv2.imwrite(debug_path, image)
                logging.info(f"Saved debug image: {debug_path}")

            # Extract features
            features = self._extract_image_features(image)

            if features is not None:
                feature_count = len(features) if hasattr(features, '__len__') else "histogram"
                logging.info(f"Extracted features from image {listing_index + 1}: {feature_count} features")
            else:
                logging.warning(f"No features extracted from image {listing_index + 1}")

            # Cache result
            self.image_cache[image_url] = features

            return features

        except Exception as e:
            logging.error(f"Error downloading/processing image {image_url}: {e}")
            return None

    def _extract_image_features(self, image: np.ndarray) -> dict:
        """Extract multiple types of features from image for robust comparison"""
        try:
            # Resize image for consistent comparison
            resized = cv2.resize(image, self.image_size)

            # Convert to grayscale
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

            features = {}

            # 1. ORB features for keypoint matching
            keypoints, descriptors = self.feature_detector.detectAndCompute(gray, None)
            features['orb'] = descriptors if descriptors is not None else np.array([])

            # 2. Color histogram for overall color similarity
            hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
            hist_h = cv2.calcHist([hsv], [0], None, [50], [0, 180])
            hist_s = cv2.calcHist([hsv], [1], None, [60], [0, 256])
            hist_v = cv2.calcHist([hsv], [2], None, [60], [0, 256])
            features['color_hist'] = np.concatenate([hist_h.flatten(), hist_s.flatten(), hist_v.flatten()])

            # 3. Structural similarity (using template matching on smaller scale)
            small_gray = cv2.resize(gray, (64, 64))
            features['structure'] = small_gray.flatten().astype(np.float32)

            # 4. Edge features for shape comparison
            edges = cv2.Canny(gray, 50, 150)
            edge_hist = cv2.calcHist([edges], [0], None, [256], [0, 256])
            features['edges'] = edge_hist.flatten()

            return features

        except Exception as e:
            logging.debug(f"Error extracting image features: {e}")
            return {'orb': np.array([]), 'color_hist': np.array([]), 'structure': np.array([]), 'edges': np.array([])}

    def _calculate_image_similarity(self, features1: dict, features2: dict) -> float:
        """Calculate similarity between two multi-feature sets using weighted combination"""
        try:
            if not features1 or not features2:
                return 0.0

            similarities = {}
            weights = {
                'orb': 0.4,      # ORB features are most important for exact matches
                'color_hist': 0.3, # Color similarity is very important for similar products
                'structure': 0.2,  # Overall structure similarity
                'edges': 0.1       # Edge patterns
            }

            # 1. ORB feature matching
            orb_sim = 0.0
            if len(features1['orb']) > 0 and len(features2['orb']) > 0:
                try:
                    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                    matches = bf.match(features1['orb'], features2['orb'])

                    if len(matches) > 0:
                        # Use more lenient distance threshold for similar but not identical images
                        good_matches = [m for m in matches if m.distance < 70]  # Increased from 50
                        # Normalize by minimum feature count for better scaling
                        min_features = min(len(features1['orb']), len(features2['orb']))
                        orb_sim = len(good_matches) / max(min_features, 1)
                        orb_sim = min(orb_sim, 1.0)
                except Exception as e:
                    logging.debug(f"ORB matching error: {e}")
                    orb_sim = 0.0
            similarities['orb'] = orb_sim

            # 2. Color histogram similarity
            if len(features1['color_hist']) > 0 and len(features2['color_hist']) > 0:
                color_sim = cv2.compareHist(features1['color_hist'], features2['color_hist'], cv2.HISTCMP_CORREL)
                color_sim = max(0.0, color_sim)  # Ensure non-negative
            else:
                color_sim = 0.0
            similarities['color_hist'] = color_sim

            # 3. Structural similarity (normalized cross-correlation)
            if len(features1['structure']) > 0 and len(features2['structure']) > 0:
                # Normalize features
                struct1 = features1['structure'] / (np.linalg.norm(features1['structure']) + 1e-8)
                struct2 = features2['structure'] / (np.linalg.norm(features2['structure']) + 1e-8)
                struct_sim = np.dot(struct1, struct2)
                struct_sim = max(0.0, struct_sim)  # Ensure non-negative
            else:
                struct_sim = 0.0
            similarities['structure'] = struct_sim

            # 4. Edge similarity
            if len(features1['edges']) > 0 and len(features2['edges']) > 0:
                edge_sim = cv2.compareHist(features1['edges'], features2['edges'], cv2.HISTCMP_CORREL)
                edge_sim = max(0.0, edge_sim)  # Ensure non-negative
            else:
                edge_sim = 0.0
            similarities['edges'] = edge_sim

            # Calculate weighted average
            total_similarity = sum(similarities[key] * weights[key] for key in weights.keys())

            # Bonus for multiple good matches
            good_feature_count = sum(1 for sim in similarities.values() if sim > 0.5)
            if good_feature_count >= 2:
                total_similarity *= 1.1  # 10% bonus for multiple good feature matches

            total_similarity = min(total_similarity, 1.0)

            # Debug logging for similar images
            if total_similarity > 0.2:
                logging.info("Similarity breakdown: ORB=%.3f, Color=%.3f, Structure=%.3f, Edges=%.3f, Total=%.3f" % (
                    similarities['orb'], similarities['color_hist'], similarities['structure'],
                    similarities['edges'], total_similarity
                ))

            return total_similarity

        except Exception as e:
            logging.debug(f"Error calculating similarity: {e}")
            return 0.0

    def _calculate_confidence_score(self, listing: SoldListing, similarity: float) -> float:
        """Calculate overall confidence score for a match"""
        # Base confidence from image similarity
        confidence = similarity

        # Boost confidence for recent sales
        try:
            if 'day' in listing.sold_date.lower():
                if 'yesterday' in listing.sold_date.lower() or '1 day' in listing.sold_date.lower():
                    confidence += 0.1
            elif 'week' in listing.sold_date.lower():
                confidence += 0.05
        except (AttributeError, TypeError):
            pass  # sold_date is None or not a string

        # Boost confidence for reasonable prices (not too high/low)
        if 10 <= listing.price <= 1000:
            confidence += 0.05

        return min(confidence, 1.0)

    def _analyze_matches(self, matches: List[SoldListing]) -> ImageMatchResult:
        """Analyze matches and calculate statistics"""
        if not matches:
            return ImageMatchResult(
                matches_found=0,
                best_match=None,
                all_matches=[],
                average_price=0.0,
                price_range=(0.0, 0.0),
                confidence="no_matches"
            )

        # Calculate price statistics
        prices = [match.price for match in matches]
        avg_price = sum(prices) / len(prices)
        price_range = (min(prices), max(prices))

        # Determine confidence level
        confidence = "high" if len(matches) >= 3 else "medium" if len(matches) >= 2 else "low"

        return ImageMatchResult(
            matches_found=len(matches),
            best_match=matches[0],  # Already sorted by similarity
            all_matches=matches,
            average_price=avg_price,
            price_range=price_range,
            confidence=confidence
        )

    def cleanup(self):
        """Clean up resources"""
        try:
            self.browser.cleanup()
        except Exception as e:
            logging.debug(f"Error cleaning up browser: {e}")


# Convenience function
def match_product_with_sold_listings_requests(reference_image_path: str,
                                            search_term: str,
                                            similarity_threshold: float = 0.7,
                                            max_results: int = 5,
                                            debug_output_dir: str = None) -> ImageMatchResult:
    """
    Convenience function to match a product image with sold listings using requests

    Args:
        reference_image_path: Path to product image
        search_term: Search term for the product
        similarity_threshold: Image similarity threshold (0.0-1.0)
        max_results: Maximum results to analyze
        debug_output_dir: Directory to save downloaded images for debugging

    Returns:
        ImageMatchResult with pricing data
    """
    matcher = SoldListingMatcherRequests(
        similarity_threshold=similarity_threshold,
        debug_output_dir=debug_output_dir
    )
    try:
        return matcher.find_matching_sold_listings(
            reference_image_path, search_term, max_results
        )
    finally:
        matcher.cleanup()


if __name__ == '__main__':
    # Example usage and testing
    import sys

    if len(sys.argv) < 3:
        print("Usage: python sold_listing_matcher_requests.py <image_path> <search_term>")
        print("Example: python sold_listing_matcher_requests.py image.jpg 'yura kano photobook'")
        sys.exit(1)

    image_path = sys.argv[1]
    search_term = sys.argv[2]

    print(f"=== SOLD LISTING MATCHER (REQUESTS VERSION) ===")
    print(f"Image: {image_path}")
    print(f"Search term: {search_term}")
    print()

    result = match_product_with_sold_listings_requests(
        image_path, search_term, similarity_threshold=0.6, max_results=5
    )

    print(f"=== RESULTS ===")
    print(f"Matches found: {result.matches_found}")
    print(f"Confidence: {result.confidence}")

    if result.best_match:
        print(f"\nBest match:")
        print(f"  Title: {result.best_match.title}")
        print(f"  Price: {result.best_match.currency} {result.best_match.price}")
        print(f"  Similarity: {result.best_match.image_similarity:.2f}")
        print(f"  Sold: {result.best_match.sold_date}")

    if result.matches_found > 0:
        print(f"\nPrice analysis:")
        print(f"  Average price: ${result.average_price:.2f}")
        print(f"  Price range: ${result.price_range[0]:.2f} - ${result.price_range[1]:.2f}")

        print(f"\nAll matches:")
        for i, match in enumerate(result.all_matches, 1):
            print(f"  {i}. {match.title[:60]}... - ${match.price:.2f} (sim: {match.image_similarity:.2f})")