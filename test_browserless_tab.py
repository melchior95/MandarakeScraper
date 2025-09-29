#!/usr/bin/env python3
"""
Test script for the new browserless search tab functionality
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.getcwd())

def test_imports():
    """Test that all required imports work"""
    try:
        print("Testing imports...")

        # Test GUI import
        from gui_config import ScraperGUI
        print("SUCCESS: GUI import successful")

        # Test sold listing matcher import
        from sold_listing_matcher import match_product_with_sold_listings, SoldListingMatcher
        print("SUCCESS: Sold listing matcher import successful")

        # Test asyncio
        import asyncio
        print("SUCCESS: Asyncio import successful")

        # Test OpenCV
        import cv2
        print("SUCCESS: OpenCV import successful")

        return True

    except ImportError as e:
        print(f"FAILED: Import error: {e}")
        return False
    except Exception as e:
        print(f"FAILED: Unexpected error: {e}")
        return False

def test_gui_creation():
    """Test GUI creation without showing window"""
    try:
        print("\nTesting GUI creation...")

        # Create GUI instance but don't show it
        import tkinter as tk
        from gui_config import ScraperGUI

        # This will test the widget creation without mainloop
        root = tk.Tk()
        root.withdraw()  # Hide the window

        # Create a minimal GUI test
        gui = ScraperGUI()
        gui.withdraw()  # Hide this window too

        # Check if browserless attributes exist
        if hasattr(gui, 'browserless_query_var'):
            print("SUCCESS: Browserless query variable created")
        else:
            print("FAILED: Browserless query variable missing")
            return False

        if hasattr(gui, 'browserless_tree'):
            print("SUCCESS: Browserless tree widget created")
        else:
            print("FAILED: Browserless tree widget missing")
            return False

        if hasattr(gui, 'select_browserless_image'):
            print("SUCCESS: Browserless image selection method exists")
        else:
            print("FAILED: Browserless image selection method missing")
            return False

        if hasattr(gui, 'run_browserless_search'):
            print("SUCCESS: Browserless search method exists")
        else:
            print("FAILED: Browserless search method missing")
            return False

        # Clean up
        gui.destroy()
        root.destroy()

        return True

    except Exception as e:
        print(f"FAILED: GUI creation error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_image_file_access():
    """Test if we can access some sample images"""
    try:
        print("\nTesting image file access...")

        # Look for any image files in the project
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp']
        image_dirs = ['images', 'debug_images', '.']

        found_images = []
        for dir_path in image_dirs:
            if os.path.exists(dir_path):
                for file in os.listdir(dir_path):
                    if any(file.lower().endswith(ext) for ext in image_extensions):
                        found_images.append(os.path.join(dir_path, file))
                        if len(found_images) >= 3:  # Just need a few for testing
                            break
                if len(found_images) >= 3:
                    break

        if found_images:
            print(f"SUCCESS: Found {len(found_images)} sample images:")
            for img in found_images[:3]:
                print(f"  - {img}")

                # Test if OpenCV can read it
                import cv2
                test_img = cv2.imread(img)
                if test_img is not None:
                    print(f"    SUCCESS: OpenCV can read {os.path.basename(img)}")
                else:
                    print(f"    FAILED: OpenCV cannot read {os.path.basename(img)}")
        else:
            print("WARNING: No sample images found - will need to provide image for testing")

        return True

    except Exception as e:
        print(f"FAILED: Image access error: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing Browserless Search Tab Integration")
    print("=" * 50)

    results = []

    # Run tests
    results.append(("Import Test", test_imports()))
    results.append(("GUI Creation Test", test_gui_creation()))
    results.append(("Image Access Test", test_image_file_access()))

    # Summary
    print("\nTest Results Summary")
    print("=" * 30)

    passed = 0
    for test_name, result in results:
        status = "SUCCESS: PASS" if result else "FAILED: FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("\nAll tests passed! The browserless search tab should be working.")
        print("\nUsage Instructions:")
        print("1. Run: python gui_config.py")
        print("2. Go to the 'eBay Text Search' tab")
        print("3. Enter a search query (e.g., 'pokemon card')")
        print("4. Select a reference image using 'Select Image...'")
        print("5. Choose max results (3, 5, 7, 10, or 15)")
        print("6. Click 'Search & Compare' to start the search")
        print("7. Results will show with similarity percentages")
        print("8. Double-click any result to open the eBay URL")
    else:
        print(f"\n{len(results) - passed} test(s) failed. Check the errors above.")

    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
