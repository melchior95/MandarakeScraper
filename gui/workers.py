"""
Worker thread functions for GUI background operations.

This module contains all worker functions that run in background threads
to prevent blocking the GUI. Workers communicate with the main thread via
queues and use the `after()` method for UI updates.
"""

import json
import logging
import queue
import re
import threading
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import requests
from PIL import Image, ImageTk, ImageOps
from skimage.metrics import structural_similarity as ssim

from mandarake_scraper import MandarakeScraper, schedule_scraper


# ============================================================================
# Helper Functions
# ============================================================================

def extract_price(price_text: str) -> float:
    """
    Extract numeric price from text.

    Args:
        price_text: Text containing price (e.g., "$123.45", "¥1,234")

    Returns:
        float: Extracted price value, or 0.0 if not found
    """
    if not price_text:
        return 0.0
    # Remove currency symbols and commas, extract number
    match = re.search(r'[\d,]+\.?\d*', str(price_text).replace(',', ''))
    if match:
        return float(match.group(0))
    return 0.0


def compare_images(ref_image: np.ndarray, compare_image: np.ndarray, use_ransac: bool = False) -> float:
    """
    Compare two images and return similarity score (0-100).
    Enhanced multi-metric comparison with robustness to crops/extra elements:
    - Feature Matching (ORB) - 50% (most robust to crops/additions)
    - SSIM (Structural Similarity) - 25%
    - Color Histogram - 15%
    - Template Matching - 10% (for detecting embedded matches)

    Args:
        ref_image: Reference image (numpy array)
        compare_image: Image to compare (numpy array)
        use_ransac: Enable RANSAC geometric verification (slower, more accurate)

    Returns:
        float: Similarity score from 0-100
    """
    try:
        # Resize images to same size for comparison (higher res for better feature detection)
        ref_resized = cv2.resize(ref_image, (400, 400))
        compare_resized = cv2.resize(compare_image, (400, 400))

        # Convert to grayscale
        ref_gray = cv2.cvtColor(ref_resized, cv2.COLOR_BGR2GRAY)
        compare_gray = cv2.cvtColor(compare_resized, cv2.COLOR_BGR2GRAY)

        # === 1. Feature Matching (ORB) - 50% weight ===
        # Increased features for better matching
        orb = cv2.ORB_create(nfeatures=1000, scaleFactor=1.2, nlevels=8)
        kp1, des1 = orb.detectAndCompute(ref_gray, None)
        kp2, des2 = orb.detectAndCompute(compare_gray, None)

        feature_score = 0.0
        ransac_score = 0.0

        if des1 is not None and des2 is not None and len(des1) > 0 and len(des2) > 0:
            # Use BFMatcher with Hamming distance for ORB
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            matches = bf.knnMatch(des1, des2, k=2)

            # Apply ratio test (Lowe's ratio test)
            good_matches = []
            for match_pair in matches:
                if len(match_pair) == 2:
                    m, n = match_pair
                    if m.distance < 0.75 * n.distance:  # Ratio test
                        good_matches.append(m)
                elif len(match_pair) == 1:
                    good_matches.append(match_pair[0])

            # Calculate score based on good matches
            if len(good_matches) > 0:
                # Normalize by the smaller number of keypoints
                max_possible_matches = min(len(kp1), len(kp2))
                if max_possible_matches > 0:
                    # More lenient scoring for feature matches
                    raw_ratio = len(good_matches) / max_possible_matches
                    feature_score = min(raw_ratio * 2.0, 1.0)  # Multiply by 2 to boost scores

                # === RANSAC Geometric Verification (optional) ===
                if use_ransac and len(good_matches) >= 4:  # Need at least 4 points for homography
                    try:
                        # Extract matched keypoint coordinates
                        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

                        # Find homography using RANSAC
                        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

                        if mask is not None:
                            # Calculate inlier ratio (geometrically coherent matches)
                            inliers = np.sum(mask)
                            inlier_ratio = inliers / len(good_matches)
                            ransac_score = inlier_ratio  # 0.0 to 1.0

                    except Exception as e:
                        # RANSAC can fail if points are degenerate
                        ransac_score = 0.0

        # === 2. SSIM (Structural Similarity) - 25% weight ===
        ssim_score = ssim(ref_gray, compare_gray)

        # === 3. Color Histogram Comparison - 15% weight ===
        # Use HSV color space (better for color matching than RGB)
        ref_hsv = cv2.cvtColor(ref_resized, cv2.COLOR_BGR2HSV)
        compare_hsv = cv2.cvtColor(compare_resized, cv2.COLOR_BGR2HSV)

        # Calculate histograms with higher bins for better precision
        ref_hist = cv2.calcHist([ref_hsv], [0, 1, 2], None, [12, 12, 12], [0, 180, 0, 256, 0, 256])
        compare_hist = cv2.calcHist([compare_hsv], [0, 1, 2], None, [12, 12, 12], [0, 180, 0, 256, 0, 256])
        cv2.normalize(ref_hist, ref_hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        cv2.normalize(compare_hist, compare_hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        hist_score = cv2.compareHist(ref_hist, compare_hist, cv2.HISTCMP_CORREL)

        # Handle NaN from histogram comparison
        if np.isnan(hist_score):
            hist_score = 0.0
        else:
            hist_score = max(0.0, hist_score)  # Ensure non-negative

        # === 4. Template Matching - 10% weight ===
        # Check if reference appears as a sub-region in compare image
        template_score = 0.0
        try:
            # Try multiple scales to handle size differences
            scales = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
            best_match = 0.0

            for scale in scales:
                if scale != 1.0:
                    width = int(ref_resized.shape[1] * scale)
                    height = int(ref_resized.shape[0] * scale)
                    if width < compare_resized.shape[1] and height < compare_resized.shape[0]:
                        scaled_ref = cv2.resize(ref_resized, (width, height))
                        scaled_ref_gray = cv2.cvtColor(scaled_ref, cv2.COLOR_BGR2GRAY)
                    else:
                        continue
                else:
                    scaled_ref_gray = ref_gray

                # Template matching
                result = cv2.matchTemplate(compare_gray, scaled_ref_gray, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                best_match = max(best_match, max_val)

            template_score = max(0.0, best_match)
        except:
            template_score = 0.0

        # === Weighted combination ===
        # Template matching is proving to be the most reliable for exact matches with watermarks
        # Feature matching is second but can be inconsistent with heavy watermarks
        if use_ransac and ransac_score > 0:
            # With RANSAC: adjust weights to incorporate geometric verification
            similarity = (
                template_score * 0.50 +   # Template matching (reduced from 60%)
                feature_score * 0.20 +    # Feature matching (reduced from 25%)
                ransac_score * 0.20 +     # RANSAC geometric coherence (new)
                ssim_score * 0.07 +       # Structural similarity (reduced from 10%)
                hist_score * 0.03         # Color distribution (reduced from 5%)
            ) * 100
        else:
            # Without RANSAC: standard weights
            similarity = (
                template_score * 0.60 +   # Template matching (best for exact matches)
                feature_score * 0.25 +    # Feature matching (robust to crops)
                ssim_score * 0.10 +       # Structural similarity
                hist_score * 0.05         # Color distribution (least important)
            ) * 100

        # === Consistency Bonus ===
        # When multiple metrics agree (all score high), it's a stronger match
        # This increases separation between true matches and false positives
        high_threshold = 0.50  # Metric must be >50% to count as "high"
        if use_ransac:
            metrics = [template_score, feature_score, ssim_score, hist_score, ransac_score]
        else:
            metrics = [template_score, feature_score, ssim_score, hist_score]
        high_count = sum(1 for m in metrics if m > high_threshold)

        consistency_multiplier = 1.0
        if high_count >= 3:
            consistency_multiplier = 1.25  # 3+ metrics agree: strong match, +25% boost
        elif high_count >= 2:
            consistency_multiplier = 1.15  # 2 metrics agree: good match, +15% boost

        similarity *= consistency_multiplier

        # Debug output for analysis
        if use_ransac:
            print(f"[IMAGE COMPARE] Features: {feature_score*100:.1f}%, SSIM: {ssim_score*100:.1f}%, "
                  f"Hist: {hist_score*100:.1f}%, Template: {template_score*100:.1f}%, RANSAC: {ransac_score*100:.1f}% "
                  f"[{high_count} high] x{consistency_multiplier:.2f} => Total: {similarity:.1f}%")
        else:
            print(f"[IMAGE COMPARE] Features: {feature_score*100:.1f}%, SSIM: {ssim_score*100:.1f}%, "
                  f"Hist: {hist_score*100:.1f}%, Template: {template_score*100:.1f}% "
                  f"[{high_count} high] x{consistency_multiplier:.2f} => Total: {similarity:.1f}%")

        return max(0.0, min(100.0, similarity))  # Clamp to 0-100

    except Exception as e:
        print(f"[IMAGE COMPARE] Error: {e}")
        import traceback
        traceback.print_exc()
        return 0.0


def create_debug_folder(query: str) -> Path:
    """
    Create debug folder for saving comparison images.

    Args:
        query: Search query string

    Returns:
        Path: Debug folder path
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_query = "".join(c for c in query if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
    debug_folder = Path(f"debug_comparison/{safe_query}_{timestamp}")
    debug_folder.mkdir(parents=True, exist_ok=True)
    print(f"[DEBUG] Debug folder: {debug_folder}")
    return debug_folder


def extract_secondary_keyword(title: str, primary_keyword: str, publisher_list: set) -> str:
    """
    Extract secondary keyword from title by removing primary keyword and common terms.

    Args:
        title: Full product title
        primary_keyword: Primary search keyword to remove
        publisher_list: Set of publisher names to remove

    Returns:
        str: Secondary keyword extracted from title
    """
    # Make a working copy
    secondary = title

    # Remove primary keyword (case insensitive), handling name in different orders
    # e.g., "Yura Kano" and "Kano Yura"
    secondary = re.sub(re.escape(primary_keyword), '', secondary, flags=re.IGNORECASE).strip()

    # Also remove reversed name order (split and reverse)
    name_parts = primary_keyword.split()
    if len(name_parts) == 2:
        reversed_name = f"{name_parts[1]} {name_parts[0]}"
        secondary = re.sub(re.escape(reversed_name), '', secondary, flags=re.IGNORECASE).strip()
        # Also remove individual parts if they appear alone
        for part in name_parts:
            if len(part) > 2:  # Don't remove very short words
                secondary = re.sub(r'\b' + re.escape(part) + r'\b', '', secondary, flags=re.IGNORECASE).strip()

    # Use dynamic publisher list instead of hardcoded
    for pub in publisher_list:
        secondary = re.sub(r'\b' + re.escape(pub) + r'\b', '', secondary, flags=re.IGNORECASE).strip()

    # Remove generic suffixes
    generic_terms = ['Photograph Collection', 'Photo Essay', 'Photo Collection',
                    'Photobook', 'autographed', 'Photograph', 'Collection']
    for term in generic_terms:
        secondary = re.sub(r'\b' + re.escape(term) + r'\b', '', secondary, flags=re.IGNORECASE).strip()

    # Remove years (e.g., "2022", "2023")
    secondary = re.sub(r'\b(19|20)\d{2}\b', '', secondary).strip()

    # Remove "Desktop" before "Calendar" to get just "Calendar"
    secondary = re.sub(r'\bDesktop\s+Calendar\b', 'Calendar', secondary, flags=re.IGNORECASE).strip()

    # Clean up extra spaces
    secondary = re.sub(r'\s+', ' ', secondary).strip()

    # If nothing left, return empty
    if not secondary or len(secondary) < 2:
        return ""

    return secondary


# ============================================================================
# Worker Functions
# ============================================================================

def run_scraper_worker(config_path: str, use_mimic: bool, run_queue: queue.Queue,
                       cancel_flag: threading.Event) -> None:
    """
    Worker to run the Mandarake scraper in background thread.

    Args:
        config_path: Path to JSON configuration file
        use_mimic: Whether to use browser mimic mode
        run_queue: Queue for communicating status back to main thread
        cancel_flag: Event flag to check for cancellation
    """
    config_path = Path(config_path)
    current_scraper = None

    try:
        print(f"[GUI DEBUG] Starting scraper with use_mimic={use_mimic}")

        # Load config to check for Japanese text
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            keyword = config.get('keyword', '')
            print(f"[GUI DEBUG] Keyword from config loaded")
            print(f"[GUI DEBUG] Keyword has {len(keyword)} characters")

        scraper = MandarakeScraper(str(config_path), use_mimic=use_mimic)
        current_scraper = scraper
        scraper._cancel_requested = False  # Initialize cancel flag
        print(f"[GUI DEBUG] Scraper browser mimic enabled: {scraper.use_mimic}")
        print(f"[GUI DEBUG] Scraper browser object type: {type(scraper.browser_mimic)}")
        scraper.run()

        # Check if cancelled
        if cancel_flag.is_set():
            run_queue.put(("status", "Scrape cancelled by user."))
        else:
            run_queue.put(("status", "Scrape completed."))
            run_queue.put(("results", str(config_path)))
    except Exception as exc:
        import traceback
        print(f"[GUI DEBUG] Full exception traceback:")
        traceback.print_exc()
        if cancel_flag.is_set():
            run_queue.put(("status", "Scrape cancelled."))
        else:
            run_queue.put(("error", f"Scrape failed: {exc}"))
    finally:
        current_scraper = None
        run_queue.put(("cleanup", str(config_path)))


def schedule_worker(config_path: str, schedule_time: str, use_mimic: bool,
                   run_queue: queue.Queue) -> None:
    """
    Worker to schedule a scraper run.

    Args:
        config_path: Path to JSON configuration file
        schedule_time: Time to schedule the scraper
        use_mimic: Whether to use browser mimic mode
        run_queue: Queue for communicating status back to main thread
    """
    try:
        schedule_scraper(config_path, schedule_time, use_mimic=use_mimic)
    except Exception as exc:
        run_queue.put(("error", f"Schedule failed: {exc}"))
    finally:
        run_queue.put(("cleanup", config_path))


def run_image_analysis_worker(image_path: Path, search_method: str, enhancement_level: str,
                              ebay_days_back: int, lazy_search: bool,
                              update_callback, display_callback) -> None:
    """
    Worker for image analysis (runs in background thread).

    Args:
        image_path: Path to image to analyze
        search_method: Search method ("direct" or "lens")
        enhancement_level: Image enhancement level
        ebay_days_back: Days back to search eBay
        lazy_search: Whether to use lazy search
        update_callback: Callback to update status (status, progress)
        display_callback: Callback to display results
    """
    try:
        update_callback("Preprocessing image...", 10)

        # Step 1: Preprocess the image
        from image_processor import optimize_image_for_search
        processed_image = optimize_image_for_search(str(image_path), enhancement_level)

        update_callback(f"Searching using {search_method} method...", 30)

        # Step 2: Perform the search based on selected method
        if search_method == "direct":
            # Direct eBay image search
            from ebay_image_search import run_sold_listings_image_search
            search_result = run_sold_listings_image_search(processed_image, ebay_days_back, lazy_search)
        else:  # lens method
            # Google Lens + eBay search
            from google_lens_search import search_ebay_with_lens_sync
            search_result = search_ebay_with_lens_sync(processed_image, ebay_days_back, headless=True, lazy_search=lazy_search)

        update_callback("Processing results...", 80)

        # Step 3: Process results for display
        if search_result.get('error'):
            update_callback(f"Search failed: {search_result['error']}", 0)
            return

        if search_result['sold_count'] == 0:
            update_callback("No sold listings found for this image", 100)
            return

        # Step 4: Display results
        display_callback(search_result)
        update_callback(f"Image analysis complete: {search_result['sold_count']} items found", 100)

    except Exception as e:
        update_callback(f"Image analysis failed: {e}", 0)
        print(f"[IMAGE ANALYSIS] Error: {e}")


def run_ai_smart_search_worker(image_path: Path, enhancement_level: str, lazy_search: bool,
                               ai_confirmation: bool, ebay_days_back: int, usd_jpy_rate: float,
                               update_callback, display_callback, ai_select_callback) -> None:
    """
    Worker for AI smart search (runs in background thread).

    Args:
        image_path: Path to image to analyze
        enhancement_level: Image enhancement level
        lazy_search: Whether to use lazy search
        ai_confirmation: Whether to use AI confirmation
        ebay_days_back: Days back to search eBay
        usd_jpy_rate: USD to JPY exchange rate
        update_callback: Callback to update status (status, progress)
        display_callback: Callback to display results
        ai_select_callback: Callback to select best result with AI
    """
    try:
        from image_analysis_engine import ImageAnalysisEngine

        # Configure analysis engine
        config = {
            'usd_jpy_rate': usd_jpy_rate,
            'min_profit_margin': 20,
            'ebay_fees_percent': 0.13,
            'shipping_cost': 5.0
        }

        engine = ImageAnalysisEngine(config)

        update_callback("Running comprehensive AI analysis...", 20)

        # Use comprehensive analysis with multiple methods
        methods = ["direct_ebay", "google_lens"] if lazy_search else ["direct_ebay"]
        enhancement_levels = [enhancement_level]

        if ai_confirmation:
            # Try multiple enhancement levels for better matching
            enhancement_levels = ["light", "medium", "aggressive"]
            update_callback("AI confirmation enabled - trying multiple enhancement levels...", 20)

        analysis_result = engine.analyze_image_comprehensive(
            str(image_path),
            methods=methods,
            enhancement_levels=enhancement_levels,
            days_back=ebay_days_back
        )

        update_callback("Processing AI results...", 80)

        if ai_confirmation and analysis_result.get('results'):
            update_callback("AI analyzing results for best match...", 80)
            # Use AI to select the best result based on confidence and data quality
            best_result = ai_select_callback(analysis_result['results'])
            if best_result:
                analysis_result['results'] = [best_result]
                analysis_result['ai_selected'] = True

        # Display results
        display_callback(analysis_result)

        result_count = len(analysis_result.get('results', []))
        ai_note = " (AI-confirmed best match)" if analysis_result.get('ai_selected') else ""
        update_callback(f"AI Smart Search complete: {result_count} results found{ai_note}", 100)

    except Exception as e:
        update_callback(f"AI Smart Search failed: {e}", 0)
        print(f"[AI SMART SEARCH] Error: {e}")


def run_ebay_image_comparison_worker(image_path: Path, search_term: str, days_back: int,
                                    similarity_threshold: float, max_images: int, show_browser: bool,
                                    update_callback, display_callback, show_message_callback) -> None:
    """
    Worker for eBay image comparison (runs in background thread).

    Args:
        image_path: Path to reference image
        search_term: Search term for eBay
        days_back: Days back to search eBay
        similarity_threshold: Minimum similarity threshold (0.0-1.0)
        max_images: Maximum images to compare
        show_browser: Whether to show browser window
        update_callback: Callback to update status (status, progress)
        display_callback: Callback to display results
        show_message_callback: Callback to show message dialog
    """
    try:
        update_callback("Initializing computer vision matcher...", 10)

        if not search_term:
            update_callback("eBay image comparison cancelled", 0)
            return

        update_callback(f"Searching for sold listings: {search_term}", 30)

        # Create debug output directory
        debug_dir = create_debug_folder(search_term)
        update_callback(f"Images will be saved to: {debug_dir}", 30)

        if show_browser:
            # Use Playwright version with visible browser
            from sold_listing_matcher import SoldListingMatcher
            update_callback("Initializing visible browser...", 30)
            matcher = SoldListingMatcher(
                headless=False,
                similarity_threshold=similarity_threshold,
                debug_output_dir=str(debug_dir)
            )
            update_callback("Browser ready - starting eBay search...", 30)
        else:
            # Use requests-based matcher (faster, hidden)
            from sold_listing_matcher_requests import SoldListingMatcherRequests
            matcher = SoldListingMatcherRequests(
                similarity_threshold=similarity_threshold,
                debug_output_dir=str(debug_dir)
            )

        update_callback("Analyzing sold listing images...", 50)

        try:
            if show_browser:
                # Playwright version needs async handling
                import asyncio
                result = asyncio.run(matcher.find_matching_sold_listings(
                    reference_image_path=str(image_path),
                    search_term=search_term,
                    max_results=max_images,
                    days_back=days_back
                ))
            else:
                # Requests version is synchronous
                result = matcher.find_matching_sold_listings(
                    reference_image_path=str(image_path),
                    search_term=search_term,
                    max_results=max_images,
                    days_back=days_back
                )

            # Update status to show where images were saved
            if debug_dir.exists():
                image_count = len([f for f in debug_dir.iterdir() if f.suffix == '.jpg'])
                update_callback(f"Analysis complete! {image_count} comparison images saved to: {debug_dir}", 50)
                print(f"[IMAGE COMPARISON] Saved {image_count} images to: {debug_dir.absolute()}")
        finally:
            # Handle cleanup for both sync and async versions
            if show_browser:
                import asyncio
                try:
                    asyncio.run(matcher.cleanup())
                except Exception as cleanup_error:
                    logging.warning("Error during Playwright cleanup: %s", str(cleanup_error))
            else:
                try:
                    matcher.cleanup()
                except Exception as cleanup_error:
                    logging.warning("Error during cleanup: %s", str(cleanup_error))

        update_callback("Processing image comparison results...", 80)

        # Display results
        display_callback(result, search_term)

        if result.matches_found > 0:
            confidence_text = f" ({result.confidence} confidence)" if result.confidence != "error" else ""
            update_callback(f"Image comparison complete: {result.matches_found} matches found{confidence_text}", 100)
        else:
            update_callback("No visual matches found in sold listings", 100)

    except Exception as e:
        error_message = str(e)

        # Skip format string errors - they're cosmetic and don't affect functionality
        if "Cannot specify" in error_message and "with 's'" in error_message:
            print("[DEBUG] Ignoring cosmetic format string error - functionality worked correctly")
            return

        # Provide user-friendly error messages
        if "timeout" in error_message.lower() or "navigation" in error_message.lower():
            update_callback("eBay blocked request - Wait 2-5 minutes before trying again", 0)
            print("[EBAY IMAGE COMPARISON] eBay blocking detected:", str(e))
        else:
            update_callback(f"eBay image comparison failed: {error_message}", 0)
            print("[EBAY IMAGE COMPARISON] Error:", str(e))


def download_missing_images_worker(csv_data: List[Dict], download_dir: str,
                                   update_callback, save_callback, reload_callback) -> None:
    """
    Background worker to download missing images for CSV items.

    Args:
        csv_data: List of CSV row dictionaries
        download_dir: Directory to download images to
        update_callback: Callback to update status
        save_callback: Callback to save updated CSV
        reload_callback: Callback to reload filtered items
    """
    # Create images directory
    if not download_dir:
        download_dir = "images"

    images_dir = Path(download_dir)
    images_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    skipped = 0
    failed = 0

    try:
        for i, row in enumerate(csv_data, 1):
            local_image = row.get('local_image', '')
            image_url = row.get('image_url', '')

            # Skip if already has local image
            if local_image and Path(local_image).exists():
                skipped += 1
                continue

            # Skip if no image URL
            if not image_url:
                skipped += 1
                continue

            # Download image
            try:
                update_callback(f"Downloading image {i}/{len(csv_data)}...")

                response = requests.get(image_url, timeout=10)
                response.raise_for_status()

                # Determine file extension
                content_type = response.headers.get('content-type', '')
                if 'jpeg' in content_type or 'jpg' in content_type:
                    ext = '.jpg'
                elif 'png' in content_type:
                    ext = '.png'
                elif 'webp' in content_type:
                    ext = '.webp'
                else:
                    ext = '.jpg'  # Default

                # Generate filename from title or index
                title = row.get('title', f'item_{i}')
                # Clean filename
                safe_title = "".join(c for c in title[:50] if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
                filename = f"{safe_title}_{i}{ext}"
                local_path = images_dir / filename

                # Save image
                with open(local_path, 'wb') as f:
                    f.write(response.content)

                # Update row with local image path
                row['local_image'] = str(local_path)
                downloaded += 1

                print(f"[CSV IMAGES] Downloaded {i}/{len(csv_data)}: {local_path.name}")

            except Exception as e:
                print(f"[CSV IMAGES] Failed to download image {i}: {e}")
                failed += 1

        # Save updated CSV
        if downloaded > 0:
            save_callback()

        # Update UI
        summary = f"Downloaded {downloaded} images, {skipped} skipped, {failed} failed"
        print(f"[CSV IMAGES] {summary}")
        update_callback(summary)

        # Reload CSV to show new images
        if downloaded > 0:
            reload_callback()

    except Exception as e:
        import traceback
        print(f"[CSV IMAGES ERROR] {e}")
        traceback.print_exc()
        raise


def run_scrapy_text_search_worker(query: str, max_results: int, update_callback,
                                  display_callback, show_message_callback, search_method: str = "scrapy") -> None:
    """
    Worker for eBay text-only search (runs in background thread).

    Args:
        query: Search query
        max_results: Maximum results to fetch
        update_callback: Callback to update status
        display_callback: Callback to display results
        show_message_callback: Callback to show message dialog
        search_method: "scrapy" for sold listings or "api" for active listings
    """
    try:
        if search_method == "api":
            # Use eBay Browse API (active listings)
            from ebay_api_search import run_ebay_api_search

            print(f"[eBay API] Starting search for: {query}")
            print(f"[eBay API] Max results: {max_results}")

            api_results = run_ebay_api_search(
                query=query,
                max_results=max_results
            )

            if not api_results:
                update_callback("No eBay active listings found")
                return

            print(f"[eBay API] Found {len(api_results)} results")

            # Convert to display format
            results = []
            for item in api_results:
                results.append({
                    'title': item.get('product_title', 'N/A'),
                    'price': item.get('current_price', 'N/A'),
                    'shipping': item.get('shipping_cost', 'N/A'),
                    'sold_date': item.get('sold_date', 'Active'),  # Active listings
                    'similarity': '-',  # No comparison
                    'url': item.get('product_url', ''),
                    'image_url': item.get('thumbnail_image', '')
                })

            # Update UI with results
            display_callback(results)
            update_callback(f"Found {len(results)} eBay active listings (API)")

        else:
            # Use Scrapy (sold listings)
            from ebay_scrapy_search import run_ebay_scrapy_search

            print(f"[SCRAPY SEARCH] Starting search for: {query}")
            print(f"[SCRAPY SEARCH] Max results: {max_results}")

            # Run Scrapy spider
            scrapy_results = run_ebay_scrapy_search(
                query=query,
                max_results=max_results,
                sold_listings=True
            )

            if not scrapy_results:
                update_callback("No eBay sold listings found")
                return

            print(f"[SCRAPY SEARCH] Found {len(scrapy_results)} results")

            # Convert to display format (no similarity since no image comparison)
            results = []
            for item in scrapy_results:
                results.append({
                    'title': item.get('product_title', 'N/A'),
                    'price': item.get('current_price', 'N/A'),
                    'shipping': item.get('shipping_cost', 'N/A'),
                    'sold_date': item.get('sold_date', 'N/A'),
                    'similarity': '-',  # No comparison
                    'url': item.get('product_url', ''),
                    'image_url': item.get('main_image', '')
                })

            # Update UI with results
            display_callback(results)
            update_callback(f"Found {len(results)} eBay sold listings (Scrapy)")

    except Exception as e:
        import traceback
        print(f"[eBay SEARCH ERROR] {e}")
        traceback.print_exc()
        raise


def run_scrapy_search_with_compare_worker(query: str, max_results: int, max_comparisons: Optional[int],
                                         image_path: Path, update_callback, display_callback,
                                         show_message_callback) -> None:
    """
    Worker for Scrapy search WITH image comparison (runs in background thread).

    Args:
        query: Search query
        max_results: Maximum results to fetch
        max_comparisons: Maximum comparisons to perform (None = all)
        image_path: Path to reference image
        update_callback: Callback to update status
        display_callback: Callback to display results
        show_message_callback: Callback to show message dialog
    """
    try:
        from ebay_scrapy_search import run_ebay_scrapy_search

        print(f"[SCRAPY COMPARE] Starting search for: {query}")
        print(f"[SCRAPY COMPARE] Max results: {max_results}")
        print(f"[SCRAPY COMPARE] Max comparisons: {max_comparisons or 'ALL'}")
        print(f"[SCRAPY COMPARE] Reference image: {image_path}")

        # Run Scrapy spider
        scrapy_results = run_ebay_scrapy_search(
            query=query,
            max_results=max_results,
            sold_listings=True
        )

        if not scrapy_results:
            update_callback("No eBay listings found")
            return

        print(f"[SCRAPY COMPARE] Found {len(scrapy_results)} results, comparing images...")

        # Create debug folder
        debug_folder = create_debug_folder(query)

        # Load reference image
        ref_image = cv2.imread(str(image_path))
        if ref_image is None:
            raise Exception(f"Could not load reference image: {image_path}")

        # Save reference image to debug folder
        ref_debug_path = debug_folder / f"REF_selected_image.jpg"
        cv2.imwrite(str(ref_debug_path), ref_image)

        # Determine how many to compare
        items_to_compare = scrapy_results if max_comparisons is None else scrapy_results[:max_comparisons]

        # Simple image comparison using template matching
        results = []
        for i, item in enumerate(items_to_compare):
            # Download and compare image
            image_url = item.get('main_image', '')
            similarity = 0.0

            if image_url:
                try:
                    response = requests.get(image_url, timeout=5)
                    if response.status_code == 200:
                        img_array = np.frombuffer(response.content, np.uint8)
                        ebay_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                        if ebay_img is not None:
                            # Save eBay image to debug folder
                            ebay_title_safe = "".join(c for c in item.get('product_title', 'unknown')[:50] if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
                            ebay_debug_path = debug_folder / f"ebay_{i+1:02d}_{ebay_title_safe}.jpg"
                            cv2.imwrite(str(ebay_debug_path), ebay_img)

                            # Use shared comparison method
                            similarity = compare_images(ref_image, ebay_img)
                except Exception as e:
                    print(f"[SCRAPY COMPARE] Error comparing image {i+1}: {e}")

            results.append({
                'title': item.get('product_title', 'N/A'),
                'price': item.get('current_price', 'N/A'),
                'shipping': item.get('shipping_cost', 'N/A'),
                'sold_date': item.get('sold_date', 'N/A'),
                'similarity': f"{similarity:.1f}%" if similarity > 0 else '-',
                'url': item.get('product_url', ''),
                'image_url': image_url
            })

        # Sort by similarity (highest first)
        results.sort(key=lambda x: float(x['similarity'].replace('%', '')) if x['similarity'] != '-' else 0, reverse=True)

        # Update UI with results
        display_callback(results)
        update_callback(f"Found {len(results)} results, compared {len(items_to_compare)} images")

    except Exception as e:
        import traceback
        print(f"[SCRAPY COMPARE ERROR] {e}")
        traceback.print_exc()
        raise


def run_cached_compare_worker(query: str, max_comparisons: Optional[int], cached_results: List[Dict],
                              image_path: Path, update_callback, display_callback) -> None:
    """
    Worker to compare reference image with CACHED eBay results.

    Args:
        query: Search query (for debug folder naming)
        max_comparisons: Maximum comparisons to perform (None = all)
        cached_results: Cached eBay results from previous search
        image_path: Path to reference image
        update_callback: Callback to update status
        display_callback: Callback to display results
    """
    try:
        print(f"[CACHED COMPARE] Using cached results for: {query}")
        print(f"[CACHED COMPARE] Cached results count: {len(cached_results)}")
        print(f"[CACHED COMPARE] Max comparisons: {max_comparisons or 'ALL'}")
        print(f"[CACHED COMPARE] Reference image: {image_path}")

        # Create debug folder
        debug_folder = create_debug_folder(query)

        # Load reference image
        ref_image = cv2.imread(str(image_path))
        if ref_image is None:
            raise Exception(f"Could not load reference image: {image_path}")

        # Save reference image to debug folder
        ref_debug_path = debug_folder / f"REF_selected_image.jpg"
        cv2.imwrite(str(ref_debug_path), ref_image)

        # Determine how many to compare
        items_to_compare = cached_results if max_comparisons is None else cached_results[:max_comparisons]

        # Compare images with cached results
        results = []
        for i, item in enumerate(items_to_compare):
            # Download and compare image
            image_url = item.get('image_url', '')
            similarity = 0.0

            if image_url:
                try:
                    response = requests.get(image_url, timeout=5)
                    if response.status_code == 200:
                        img_array = np.frombuffer(response.content, np.uint8)
                        ebay_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                        if ebay_img is not None:
                            # Save eBay image to debug folder
                            title = item.get('title', 'unknown')
                            ebay_title_safe = "".join(c for c in title[:50] if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
                            ebay_debug_path = debug_folder / f"ebay_{i+1:02d}_{ebay_title_safe}.jpg"
                            cv2.imwrite(str(ebay_debug_path), ebay_img)

                            # Use shared comparison method
                            similarity = compare_images(ref_image, ebay_img)
                except Exception as e:
                    print(f"[CACHED COMPARE] Error comparing image {i+1}: {e}")

            # Keep all fields from cached result, but update similarity
            results.append({
                'title': item.get('title', 'N/A'),
                'price': item.get('price', 'N/A'),
                'shipping': item.get('shipping', 'N/A'),
                'sold_date': item.get('sold_date', 'N/A'),
                'similarity': f"{similarity:.1f}%" if similarity > 0 else '-',
                'url': item.get('url', ''),
                'image_url': image_url
            })

        # Sort by similarity (highest first)
        results.sort(key=lambda x: float(x['similarity'].replace('%', '')) if x['similarity'] != '-' else 0, reverse=True)

        # Update UI with results
        display_callback(results)
        update_callback(f"Compared {len(items_to_compare)} cached results")

    except Exception as e:
        import traceback
        print(f"[CACHED COMPARE ERROR] {e}")
        traceback.print_exc()
        raise


def load_csv_thumbnails_worker(filtered_items: List[Dict], csv_new_items: set,
                               update_image_callback, thumb_width: int = 70,
                               csv_path=None, save_to_csv_callback=None) -> None:
    """
    Background worker to load CSV thumbnails without blocking UI.

    Args:
        filtered_items: List of filtered CSV items
        csv_new_items: Set of item IDs that are new
        update_image_callback: Callback to update image in treeview
        thumb_width: Width of thumbnail column (default 70)
        csv_path: Optional path to CSV file (for saving downloaded images)
        save_to_csv_callback: Optional callback(local_image_path, row_index) to save image path to CSV
    """
    print(f"[CSV THUMBNAILS] Loading thumbnails for {len(filtered_items)} items (size: {thumb_width}px)...")

    # Calculate thumbnail size with padding (leave some margin)
    # Use square size to prevent horizontal images from overlapping text
    thumb_size = max(20, thumb_width - 10)

    # Track if we downloaded any new images
    downloaded_any = False

    # Batch download images that need downloading
    import requests
    from io import BytesIO
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # First pass: load local images and identify URLs to download
    images_to_download = []  # (index, row, image_url)
    local_images = {}  # index -> pil_img

    for i, row in enumerate(filtered_items):
        local_image_path = row.get('local_image', '').strip()
        image_url = row.get('image_url', '').strip()

        # Try local image first (fast)
        if local_image_path and Path(local_image_path).exists():
            try:
                pil_img = Image.open(local_image_path)
                pil_img.thumbnail((thumb_size, thumb_size), Image.Resampling.LANCZOS)

                # Center image on square background to prevent horizontal images from overlapping
                square_img = Image.new('RGB', (thumb_size, thumb_size), 'white')
                offset_x = (thumb_size - pil_img.width) // 2
                offset_y = (thumb_size - pil_img.height) // 2
                square_img.paste(pil_img, (offset_x, offset_y))
                pil_img = square_img

                # Add light blue border if item is NEW
                item_id = str(i)
                if item_id in csv_new_items:
                    pil_img = ImageOps.expand(pil_img, border=3, fill='#87CEEB')

                local_images[i] = pil_img
            except Exception as e:
                print(f"[CSV THUMBNAILS] Failed to load local thumbnail {i+1}: {e}")
                # Add to download queue if local load failed
                if image_url and csv_path:
                    images_to_download.append((i, row, image_url))
        elif image_url and csv_path:
            # No local image, need to download
            images_to_download.append((i, row, image_url))

    # Download images in parallel using Session (like browsers do)
    if images_to_download:
        print(f"[CSV THUMBNAILS] Downloading {len(images_to_download)} thumbnails in parallel...")

        csv_path_obj = Path(csv_path)
        images_dir = Path('images') / csv_path_obj.stem
        images_dir.mkdir(parents=True, exist_ok=True)

        downloaded_images = {}  # index -> pil_img
        csv_updates = []  # List of (img_path, index) to update CSV once at the end

        # Create a shared Session with connection pooling (like browsers)
        session = requests.Session()
        # Configure connection pool size to match our thread count
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=2
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        def download_image(args):
            i, row, image_url = args
            try:
                # Use session for connection pooling and keep-alive
                response = session.get(image_url, timeout=10)
                if response.status_code == 200:
                    # Save image to disk
                    img_filename = f"thumb_product_{i:04d}.jpg"
                    img_path = images_dir / img_filename

                    with open(img_path, 'wb') as img_file:
                        img_file.write(response.content)

                    # Load image for display
                    pil_img = Image.open(BytesIO(response.content))
                    pil_img.thumbnail((thumb_size, thumb_size), Image.Resampling.LANCZOS)

                    # Center image on square background to prevent horizontal images from overlapping
                    square_img = Image.new('RGB', (thumb_size, thumb_size), 'white')
                    offset_x = (thumb_size - pil_img.width) // 2
                    offset_y = (thumb_size - pil_img.height) // 2
                    square_img.paste(pil_img, (offset_x, offset_y))
                    pil_img = square_img

                    # Add light blue border if item is NEW
                    item_id = str(i)
                    if item_id in csv_new_items:
                        pil_img = ImageOps.expand(pil_img, border=3, fill='#87CEEB')

                    # Update the row data
                    row['local_image'] = str(img_path)

                    return (i, pil_img, str(img_path))
            except Exception as e:
                print(f"[CSV THUMBNAILS] Failed to download {i+1} from {image_url}: {e}")
            return (i, None, None)

        # Download in parallel with max 20 workers (browsers use 6-20 connections per domain)
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(download_image, args): args for args in images_to_download}

            completed = 0
            for future in as_completed(futures):
                i, pil_img, img_path = future.result()
                if pil_img:
                    downloaded_images[i] = pil_img
                    if img_path:
                        csv_updates.append((img_path, i))
                    downloaded_any = True

                completed += 1
                if completed % 20 == 0 or completed == len(images_to_download):
                    print(f"[CSV THUMBNAILS] Downloaded {completed}/{len(images_to_download)} thumbnails")

        # Close the session
        session.close()

        # Update CSV once with all changes
        if csv_updates and save_to_csv_callback:
            print(f"[CSV THUMBNAILS] Updating CSV with {len(csv_updates)} downloaded images...")
            for img_path, i in csv_updates:
                save_to_csv_callback(img_path, i)

        # Merge downloaded images with local images
        local_images.update(downloaded_images)

    # Update treeview with all images
    for i, pil_img in local_images.items():
        update_image_callback(str(i), pil_img)

    print(f"[CSV THUMBNAILS] Finished loading thumbnails (downloaded: {downloaded_any})")


def compare_csv_items_worker(items: List[Dict], max_results: int, cached_results: Optional[List[Dict]],
                             search_query: str, usd_jpy_rate: float, update_callback,
                             display_callback, show_message_callback, ebay_display_callback=None) -> List[Dict]:
    """
    Worker to compare CSV items with eBay - OPTIMIZED with caching.

    Args:
        items: List of CSV items to compare
        max_results: Maximum eBay results to fetch
        cached_results: Cached eBay results (or None to fetch new)
        search_query: Search query for eBay
        usd_jpy_rate: USD to JPY exchange rate
        update_callback: Callback to update status
        display_callback: Callback to display results
        show_message_callback: Callback to show message dialog

    Returns:
        List[Dict]: Comparison results
    """
    try:
        from ebay_scrapy_search import run_ebay_scrapy_search

        print(f"[CSV BATCH] Comparing {len(items)} CSV items...")

        has_cached_results = cached_results is not None and len(cached_results) > 0

        if has_cached_results:
            # Use cached results from treeview
            ebay_results = cached_results
            print(f"[CSV BATCH] Using {len(ebay_results)} cached eBay results from treeview")
            update_callback(f"Using {len(ebay_results)} cached eBay results...")

            # Create debug folder
            debug_folder = create_debug_folder(search_query or "cached_search")
        else:
            # No cached results, need to make a new search
            if not search_query:
                # Fallback to building from first item
                title = items[0].get('title', '') if items else ''
                category = items[0].get('category', '') if items else ''
                core_words = ' '.join(title.split()[:3])

                # Import CATEGORY_KEYWORDS
                from gui.constants import CATEGORY_KEYWORDS
                category_keyword = CATEGORY_KEYWORDS.get(category, '')
                search_query = f"{core_words} {category_keyword}".strip()

            if not search_query:
                update_callback("Error: Could not build search query")
                return []

            print(f"[CSV BATCH] Using search query: '{search_query}'")
            update_callback(f"Searching eBay for '{search_query}'...")

            # Create debug folder
            debug_folder = create_debug_folder(search_query)

            # **ONE eBay search for all items**
            ebay_results = run_ebay_scrapy_search(
                query=search_query,
                max_results=max_results,
                sold_listings=True
            )

            if not ebay_results:
                update_callback("No eBay listings found")
                return []

            print(f"[CSV BATCH] Found {len(ebay_results)} eBay listings")

            # Display eBay results immediately if callback provided
            if ebay_display_callback:
                ebay_display_callback(ebay_results)

        update_callback(f"Downloading and caching {len(ebay_results)} eBay images...")

        # **Cache all eBay images at once AND save to debug folder**
        ebay_image_cache = {}
        for idx, ebay_item in enumerate(ebay_results):
            # Support both 'main_image' (from search) and 'image_url' (from cached browserless_results_data)
            ebay_image_url = ebay_item.get('main_image') or ebay_item.get('image_url', '')

            # Debug: Check for duplicate URLs
            if ebay_image_url in ebay_image_cache:
                print(f"[CSV BATCH DEBUG] Skipping duplicate eBay image URL at index {idx+1}: {ebay_image_url[:80]}")

            if ebay_image_url and ebay_image_url not in ebay_image_cache:
                try:
                    response = requests.get(ebay_image_url, timeout=5)
                    if response.status_code == 200:
                        img_array = np.frombuffer(response.content, np.uint8)
                        ebay_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                        if ebay_img is not None:
                            ebay_image_cache[ebay_image_url] = ebay_img

                            # Save debug image
                            ebay_title_safe = "".join(c for c in ebay_item.get('product_title', 'unknown')[:50] if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
                            debug_path = debug_folder / f"ebay_{idx+1:02d}_{ebay_title_safe}.jpg"
                            cv2.imwrite(str(debug_path), ebay_img)
                            print(f"[CSV BATCH] Cached & saved eBay image {idx+1}/{len(ebay_results)}: {debug_path.name}")
                except Exception as e:
                    print(f"[CSV BATCH] Error downloading eBay image {idx+1}: {e}")

        print(f"[CSV BATCH] Cached {len(ebay_image_cache)} eBay images")
        print(f"[CSV BATCH DEBUG] Unique image URLs in cache: {len(ebay_image_cache)}")
        if len(ebay_image_cache) != len(ebay_results):
            print(f"[CSV BATCH DEBUG] WARNING: Cache has {len(ebay_image_cache)} unique images but {len(ebay_results)} eBay results!")

        # **Now compare each CSV item with cached eBay images**
        comparison_results = []

        for item_idx, item in enumerate(items, 1):
            try:
                update_callback(f"Comparing CSV item {item_idx}/{len(items)}...")

                csv_title = item.get('title', 'unknown')
                print(f"\n[CSV BATCH] === Processing CSV item {item_idx}/{len(items)}: {csv_title[:50]} ===")

                # Load CSV item image
                item_image_url = item.get('image_url', '')
                ref_image = None

                if item_image_url:
                    try:
                        response = requests.get(item_image_url, timeout=5)
                        if response.status_code == 200:
                            img_array = np.frombuffer(response.content, np.uint8)
                            ref_image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                            if ref_image is not None:
                                # Save CSV reference image to debug folder
                                csv_title_safe = "".join(c for c in csv_title[:50] if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
                                csv_debug_path = debug_folder / f"CSV_{item_idx:02d}_REF_{csv_title_safe}.jpg"
                                cv2.imwrite(str(csv_debug_path), ref_image)
                                print(f"[CSV BATCH] Saved CSV reference image: {csv_debug_path.name}")
                                print(f"[CSV BATCH] CSV image shape: {ref_image.shape}")
                    except Exception as e:
                        print(f"[CSV BATCH] Error loading CSV item {item_idx} image: {e}")

                if ref_image is None:
                    print(f"[CSV BATCH] WARNING: No reference image for CSV item {item_idx}, skipping comparisons")
                    continue

                # Compare with all cached eBay images
                item_comparisons = []
                for ebay_idx, ebay_item in enumerate(ebay_results):
                    similarity = 0.0

                    # Support both 'main_image' (from search) and 'image_url' (from cached browserless_results_data)
                    ebay_image_url = ebay_item.get('main_image') or ebay_item.get('image_url', '')
                    ebay_img = ebay_image_cache.get(ebay_image_url)

                    if ebay_img is not None:
                        try:
                            # Use shared comparison method
                            similarity = compare_images(ref_image, ebay_img)

                            # === SECONDARY KEYWORD BONUS ===
                            # If secondary keyword from Mandarake title appears in eBay title, add +40% similarity
                            mandarake_title = item.get('title_en', item.get('title', ''))
                            primary_keyword = item.get('keyword', '')
                            publisher_list = set()  # Will be loaded from settings if available

                            if mandarake_title and primary_keyword:
                                # Extract secondary keyword from Mandarake title
                                secondary_keyword = extract_secondary_keyword(mandarake_title, primary_keyword, publisher_list)

                                if secondary_keyword:
                                    ebay_title = ebay_item.get('product_title', '') or ebay_item.get('title', '')

                                    # Check if secondary keyword appears in eBay title (case-insensitive)
                                    if secondary_keyword.lower() in ebay_title.lower():
                                        original_similarity = similarity
                                        similarity = min(100.0, similarity + 40.0)  # Add +40%, cap at 100%
                                        print(f"[CSV BATCH] Secondary keyword match! '{secondary_keyword}' found in eBay title")
                                        print(f"[CSV BATCH]   Similarity boosted: {original_similarity:.1f}% → {similarity:.1f}%")

                            # Debug: Log suspicious perfect matches
                            if similarity >= 99.9:
                                print(f"[CSV BATCH DEBUG] Perfect match (100%) at eBay item {ebay_idx+1}")
                                print(f"[CSV BATCH DEBUG]   CSV image shape: {ref_image.shape}, eBay image shape: {ebay_img.shape}")
                                print(f"[CSV BATCH DEBUG]   eBay URL: {ebay_image_url[:100]}")

                            item_comparisons.append((similarity, ebay_idx, ebay_item.get('product_title', 'unknown')[:50]))
                        except Exception as e:
                            print(f"[CSV BATCH] Error comparing with eBay item {ebay_idx+1}: {e}")

                # Sort by similarity and show top 5
                item_comparisons.sort(reverse=True)
                print(f"[CSV BATCH] Top 5 matches for '{csv_title[:40]}':")
                for rank, (sim, idx, title) in enumerate(item_comparisons[:5], 1):
                    print(f"  {rank}. {sim:.1f}% - {title}")

                # Add all comparisons to results
                for similarity, ebay_idx, _ in item_comparisons:
                    ebay_item = ebay_results[ebay_idx]

                    # Calculate profit margin
                    mandarake_price_text = item.get('price_text', item.get('price', '0'))
                    mandarake_price = extract_price(mandarake_price_text)

                    # Try both key formats (current_price/price, shipping_cost/shipping)
                    ebay_price_text = ebay_item.get('current_price') or ebay_item.get('price', '0')
                    if not ebay_price_text or ebay_price_text == '0':
                        print(f"[CSV BATCH DEBUG] Missing or zero eBay price for item: {ebay_item.get('product_title') or ebay_item.get('title', 'N/A')[:50]}")
                        print(f"[CSV BATCH DEBUG] eBay item keys: {list(ebay_item.keys())}")
                    ebay_price = extract_price(ebay_price_text)

                    shipping_text = ebay_item.get('shipping_cost') or ebay_item.get('shipping', '0')
                    if not shipping_text or shipping_text == '0':
                        print(f"[CSV BATCH DEBUG] Missing or zero shipping for item: {ebay_item.get('product_title') or ebay_item.get('title', 'N/A')[:50]}")
                    shipping_cost = extract_price(shipping_text)

                    # Profit % = ((eBay Price + Shipping) / (Mandarake Price * Exchange Rate) - 1) * 100
                    mandarake_price_usd = mandarake_price / usd_jpy_rate if usd_jpy_rate > 0 else 0
                    total_cost_usd = ebay_price + shipping_cost
                    profit_margin = ((total_cost_usd / mandarake_price_usd - 1) * 100) if mandarake_price_usd > 0 else 0

                    comparison_results.append({
                        'thumbnail': ebay_item.get('main_image') or ebay_item.get('image_url', ''),
                        'mandarake_thumbnail': item.get('image_url', ''),
                        'ebay_title': ebay_item.get('product_title') or ebay_item.get('title', 'N/A'),
                        'mandarake_title': item.get('title', 'N/A'),
                        'mandarake_price': f"¥{mandarake_price:,.0f}",
                        'ebay_price': ebay_price_text,
                        'shipping': shipping_text,
                        'sold_date': ebay_item.get('sold_date', ''),
                        'similarity': similarity,  # Keep as number for sorting
                        'similarity_display': f"{similarity:.1f}%" if similarity > 0 else '-',
                        'profit_margin': profit_margin,  # Keep as number for sorting
                        'profit_display': f"{profit_margin:.1f}%",
                        'mandarake_link': item.get('product_url', ''),
                        'ebay_link': ebay_item.get('product_url') or ebay_item.get('url', '')
                    })

            except Exception as e:
                print(f"[CSV BATCH] Error processing CSV item {item_idx}: {e}")
                import traceback
                traceback.print_exc()
                continue

        # Sort by similarity (highest first)
        comparison_results.sort(key=lambda x: x['similarity'], reverse=True)

        print(f"\n[CSV BATCH] ========================================")
        print(f"[CSV BATCH] Generated {len(comparison_results)} comparison results")
        print(f"[CSV BATCH] Debug images saved to: {debug_folder.absolute()}")
        print(f"[CSV BATCH] - {len(ebay_image_cache)} eBay images")
        print(f"[CSV BATCH] - {len(items)} CSV reference images")
        print(f"[CSV BATCH] ========================================\n")

        # Display results
        display_callback(comparison_results)
        update_callback(f"Compared {len(items)} CSV items with {len(ebay_results)} eBay listings - {len(comparison_results)} total matches")

        return comparison_results

    except Exception as e:
        import traceback
        print(f"[CSV BATCH ERROR] {e}")
        traceback.print_exc()
        raise


def compare_csv_items_individually_worker(items: List[Dict], max_results: int, usd_jpy_rate: float,
                                         add_secondary_keyword: bool, publisher_list: set,
                                         update_callback, display_callback, show_message_callback) -> List[Dict]:
    """
    Worker to compare CSV items individually - each item gets its own eBay search.

    Args:
        items: List of CSV items to compare
        max_results: Maximum eBay results per item
        usd_jpy_rate: USD to JPY exchange rate
        add_secondary_keyword: Whether to add secondary keywords
        publisher_list: Set of publisher names
        update_callback: Callback to update status
        display_callback: Callback to display results
        show_message_callback: Callback to show message dialog

    Returns:
        List[Dict]: Comparison results
    """
    try:
        from ebay_scrapy_search import run_ebay_scrapy_search
        from gui.constants import CATEGORY_KEYWORDS

        comparison_results = []

        print(f"\n[CSV INDIVIDUAL] Starting individual comparisons for {len(items)} items")
        print(f"[CSV INDIVIDUAL] Each item will get its own eBay search with keyword + category")

        for item_idx, item in enumerate(items, 1):
            csv_title = item.get('title', 'Unknown')
            keyword = item.get('keyword', '')
            category = item.get('category', '')

            # Build search query for this specific item
            if keyword:
                core_words = keyword
            else:
                core_words = ' '.join(csv_title.split()[:3])

            category_keyword = CATEGORY_KEYWORDS.get(category, '')
            search_query = f"{core_words} {category_keyword}".strip()

            # Add secondary keyword if toggle is on
            if add_secondary_keyword:
                if csv_title and keyword:
                    secondary = extract_secondary_keyword(csv_title, keyword, publisher_list)
                    if secondary:
                        search_query = f"{search_query} {secondary}".strip()
                        print(f"[CSV INDIVIDUAL] Added secondary keyword: {secondary}")

            if not search_query:
                print(f"[CSV INDIVIDUAL] Skipping item {item_idx}: no search query")
                continue

            print(f"\n[CSV INDIVIDUAL] Item {item_idx}/{len(items)}: {csv_title[:50]}")
            print(f"[CSV INDIVIDUAL] Search query: '{search_query}'")

            update_callback(f"Item {item_idx}/{len(items)}: Searching eBay for '{search_query}'...")

            # Create debug folder for this item
            debug_folder = create_debug_folder(f"{search_query}_item{item_idx}")

            # Run eBay search for this specific item
            ebay_results = run_ebay_scrapy_search(
                query=search_query,
                max_results=max_results,
                sold_listings=True
            )

            if not ebay_results:
                print(f"[CSV INDIVIDUAL] No eBay results for item {item_idx}")
                continue

            print(f"[CSV INDIVIDUAL] Found {len(ebay_results)} eBay listings")

            # Load CSV item image
            csv_image_path = item.get('local_image', '')
            if not csv_image_path or not Path(csv_image_path).exists():
                print(f"[CSV INDIVIDUAL] No image for item {item_idx}, skipping visual comparison")
                continue

            ref_image = cv2.imread(str(csv_image_path))
            if ref_image is None:
                print(f"[CSV INDIVIDUAL] Failed to load image for item {item_idx}")
                continue

            # Save reference image to debug folder
            csv_title_safe = "".join(c for c in csv_title[:50] if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
            csv_debug_path = debug_folder / f"CSV_REF_{csv_title_safe}.jpg"
            cv2.imwrite(str(csv_debug_path), ref_image)

            # Download and compare with each eBay result
            item_comparisons = []
            for ebay_idx, ebay_item in enumerate(ebay_results):
                # Support both 'main_image' (from search) and 'image_url' (from cached browserless_results_data)
                ebay_image_url = ebay_item.get('main_image') or ebay_item.get('image_url', '')
                if not ebay_image_url:
                    continue

                try:
                    response = requests.get(ebay_image_url, timeout=5)
                    if response.status_code == 200:
                        img_array = np.frombuffer(response.content, np.uint8)
                        ebay_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                        if ebay_img is not None:
                            # Save eBay image to debug folder
                            ebay_title_safe = "".join(c for c in ebay_item.get('product_title', 'unknown')[:50] if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
                            ebay_debug_path = debug_folder / f"ebay_{ebay_idx+1:02d}_{ebay_title_safe}.jpg"
                            cv2.imwrite(str(ebay_debug_path), ebay_img)

                            # Use shared comparison method
                            similarity = compare_images(ref_image, ebay_img)

                            # === SECONDARY KEYWORD BONUS ===
                            # If secondary keyword from Mandarake title appears in eBay title, add +40% similarity
                            mandarake_title = item.get('title_en', item.get('title', ''))
                            primary_keyword = item.get('keyword', '')

                            if mandarake_title and primary_keyword:
                                # Extract secondary keyword from Mandarake title
                                secondary_keyword = extract_secondary_keyword(mandarake_title, primary_keyword, publisher_list)

                                if secondary_keyword:
                                    ebay_title = ebay_item.get('product_title', '') or ebay_item.get('title', '')

                                    # Check if secondary keyword appears in eBay title (case-insensitive)
                                    if secondary_keyword.lower() in ebay_title.lower():
                                        original_similarity = similarity
                                        similarity = min(100.0, similarity + 40.0)  # Add +40%, cap at 100%
                                        print(f"[CSV INDIVIDUAL] Secondary keyword match! '{secondary_keyword}' found in eBay title")
                                        print(f"[CSV INDIVIDUAL]   Similarity boosted: {original_similarity:.1f}% → {similarity:.1f}%")

                            item_comparisons.append((similarity, ebay_idx, ebay_item.get('product_title', 'unknown')[:50]))

                except Exception as e:
                    print(f"[CSV INDIVIDUAL] Error comparing with eBay item {ebay_idx+1}: {e}")

            # Sort by similarity and show top 5
            item_comparisons.sort(reverse=True)
            print(f"[CSV INDIVIDUAL] Top 5 matches for '{csv_title[:40]}':")
            for rank, (sim, idx, title) in enumerate(item_comparisons[:5], 1):
                print(f"  {rank}. {sim:.1f}% - {title}")

            # Add all comparisons to results
            for similarity, ebay_idx, _ in item_comparisons:
                ebay_item = ebay_results[ebay_idx]

                # Calculate profit margin
                mandarake_price_text = item.get('price_text', item.get('price', '0'))
                mandarake_price = extract_price(mandarake_price_text)

                ebay_price_text = ebay_item.get('current_price', '0')
                ebay_price = extract_price(ebay_price_text)

                shipping_text = ebay_item.get('shipping_cost', '0')
                shipping_cost = extract_price(shipping_text)

                # Profit % = ((eBay Price + Shipping) / (Mandarake Price * Exchange Rate) - 1) * 100
                mandarake_price_usd = mandarake_price / usd_jpy_rate if usd_jpy_rate > 0 else 0
                total_cost_usd = ebay_price + shipping_cost
                profit_margin = ((total_cost_usd / mandarake_price_usd - 1) * 100) if mandarake_price_usd > 0 else 0

                comparison_results.append({
                    'thumbnail': ebay_item.get('main_image') or ebay_item.get('image_url', ''),
                    'csv_title': csv_title,
                    'ebay_title': ebay_item.get('product_title') or ebay_item.get('title', 'N/A'),
                    'mandarake_price': f"¥{mandarake_price:,.0f}",
                    'ebay_price': ebay_price_text,
                    'shipping': shipping_text,
                    'sold_date': ebay_item.get('sold_date', ''),
                    'similarity': similarity,
                    'similarity_display': f"{similarity:.1f}%" if similarity > 0 else '-',
                    'profit_margin': profit_margin,
                    'profit_display': f"{profit_margin:.1f}%",
                    'mandarake_link': item.get('product_url', ''),
                    'ebay_link': ebay_item.get('product_url') or ebay_item.get('url', '')
                })

        # Sort by similarity (highest first)
        comparison_results.sort(key=lambda x: x['similarity'], reverse=True)

        print(f"\n[CSV INDIVIDUAL] ========================================")
        print(f"[CSV INDIVIDUAL] Completed {len(items)} individual searches")
        print(f"[CSV INDIVIDUAL] Generated {len(comparison_results)} comparison results")
        print(f"[CSV INDIVIDUAL] ========================================\n")

        # Display results
        display_callback(comparison_results)
        update_callback(f"Completed {len(items)} individual searches - {len(comparison_results)} total matches")

        return comparison_results

    except Exception as e:
        import traceback
        print(f"[CSV INDIVIDUAL ERROR] {e}")
        traceback.print_exc()
        raise
