#!/usr/bin/env python3
"""
Image Processing Module for Enhanced Search Results

This module provides image preprocessing and optimization functions to improve
the accuracy of image-based searches on eBay and Google Lens.
"""

import logging
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

# Try to import OpenCV for advanced processing, fallback if not available
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    logging.warning("OpenCV (cv2) not available - advanced image processing features will be disabled")
    CV2_AVAILABLE = False
    # Create dummy numpy for type hints
    class DummyNumpy:
        uint8 = int
        float64 = float
    np = DummyNumpy()


class ImageProcessor:
    """Class for preprocessing and optimizing images for search"""

    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "mandarake_image_processing"
        self.temp_dir.mkdir(exist_ok=True)

    def optimize_for_search(self, image_path: str, enhancement_level: str = "medium") -> str:
        """
        Optimize an image for better search results with multiple enhancements.

        Args:
            image_path: Path to the original image
            enhancement_level: "light", "medium", "aggressive"

        Returns:
            Path to the optimized image
        """
        try:
            original_path = Path(image_path)
            if not original_path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")

            # Load image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Apply enhancements based on level
                if enhancement_level == "light":
                    processed_img = self._light_enhancement(img)
                elif enhancement_level == "medium":
                    processed_img = self._medium_enhancement(img)
                elif enhancement_level == "aggressive":
                    processed_img = self._aggressive_enhancement(img)
                else:
                    processed_img = img

                # Save optimized image
                output_path = self.temp_dir / f"optimized_{original_path.stem}{original_path.suffix}"
                processed_img.save(output_path, quality=95, optimize=True)

                logging.info(f"Image optimized: {image_path} -> {output_path}")
                return str(output_path)

        except Exception as e:
            logging.error(f"Error optimizing image {image_path}: {e}")
            return image_path  # Return original path if optimization fails

    def _light_enhancement(self, img: Image.Image) -> Image.Image:
        """Apply light enhancements for better search results"""
        # Resize if too large (search engines often have size limits)
        img = self._resize_for_search(img)

        # Slight contrast enhancement
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.1)

        # Slight sharpening
        img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))

        return img

    def _medium_enhancement(self, img: Image.Image) -> Image.Image:
        """Apply medium enhancements for better search results"""
        # Resize if too large
        img = self._resize_for_search(img)

        # Color enhancement
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.2)

        # Contrast enhancement
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)

        # Brightness adjustment
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.05)

        # Sharpening
        img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

        return img

    def _aggressive_enhancement(self, img: Image.Image) -> Image.Image:
        """Apply aggressive enhancements for difficult images"""
        # Resize if too large
        img = self._resize_for_search(img)

        if CV2_AVAILABLE:
            try:
                # Convert to OpenCV format for advanced processing
                cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

                # Noise reduction
                cv_img = cv2.fastNlMeansDenoisingColored(cv_img, None, 10, 10, 7, 21)

                # Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
                lab = cv2.cvtColor(cv_img, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                l = clahe.apply(l)
                lab = cv2.merge([l, a, b])
                cv_img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

                # Convert back to PIL
                img = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))
            except Exception as e:
                logging.warning(f"OpenCV processing failed, using PIL fallback: {e}")
                # Fall through to PIL-only processing

        # PIL-based aggressive enhancement (fallback or additional)
        # More aggressive color enhancement
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.4)

        # Stronger contrast enhancement
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)

        # Brightness adjustment
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.1)

        # Strong sharpening
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.5)

        # Additional unsharp mask for more sharpening
        img = img.filter(ImageFilter.UnsharpMask(radius=3, percent=200, threshold=2))

        return img

    def _resize_for_search(self, img: Image.Image, max_size: int = 2048) -> Image.Image:
        """Resize image to optimal size for search engines"""
        width, height = img.size

        # If image is already small enough, return as is
        if width <= max_size and height <= max_size:
            return img

        # Calculate new dimensions maintaining aspect ratio
        if width > height:
            new_width = max_size
            new_height = int((height * max_size) / width)
        else:
            new_height = max_size
            new_width = int((width * max_size) / height)

        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def create_crop_variants(self, image_path: str, num_variants: int = 3) -> List[str]:
        """
        Create multiple cropped variants of an image for better search coverage.

        Returns:
            List of paths to cropped image variants
        """
        try:
            variants = []
            original_path = Path(image_path)

            with Image.open(image_path) as img:
                width, height = img.size

                # Center crop (1:1 ratio)
                if num_variants >= 1:
                    size = min(width, height)
                    left = (width - size) // 2
                    top = (height - size) // 2
                    cropped = img.crop((left, top, left + size, top + size))

                    variant_path = self.temp_dir / f"crop_center_{original_path.stem}{original_path.suffix}"
                    cropped.save(variant_path, quality=95)
                    variants.append(str(variant_path))

                # Top portion crop (for items with text at bottom)
                if num_variants >= 2:
                    crop_height = int(height * 0.7)
                    cropped = img.crop((0, 0, width, crop_height))

                    variant_path = self.temp_dir / f"crop_top_{original_path.stem}{original_path.suffix}"
                    cropped.save(variant_path, quality=95)
                    variants.append(str(variant_path))

                # Main subject crop (center 80%)
                if num_variants >= 3:
                    margin_w = int(width * 0.1)
                    margin_h = int(height * 0.1)
                    cropped = img.crop((margin_w, margin_h, width - margin_w, height - margin_h))

                    variant_path = self.temp_dir / f"crop_main_{original_path.stem}{original_path.suffix}"
                    cropped.save(variant_path, quality=95)
                    variants.append(str(variant_path))

            logging.info(f"Created {len(variants)} crop variants for {image_path}")
            return variants

        except Exception as e:
            logging.error(f"Error creating crop variants for {image_path}: {e}")
            return []

    def enhance_for_text_recognition(self, image_path: str) -> str:
        """
        Enhance image specifically for better text recognition (useful for product labels)
        """
        try:
            original_path = Path(image_path)

            with Image.open(image_path) as img:
                # Convert to grayscale for text recognition
                img = img.convert('L')

                if CV2_AVAILABLE:
                    try:
                        # Convert to OpenCV for advanced processing
                        cv_img = np.array(img)

                        # Apply Gaussian blur to reduce noise
                        cv_img = cv2.GaussianBlur(cv_img, (3, 3), 0)

                        # Apply threshold to get binary image
                        _, cv_img = cv2.threshold(cv_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                        # Morphological operations to clean up the image
                        kernel = np.ones((2, 2), np.uint8)
                        cv_img = cv2.morphologyEx(cv_img, cv2.MORPH_CLOSE, kernel)
                        cv_img = cv2.morphologyEx(cv_img, cv2.MORPH_OPEN, kernel)

                        # Convert back to PIL
                        img = Image.fromarray(cv_img)
                    except Exception as e:
                        logging.warning(f"OpenCV text enhancement failed, using PIL fallback: {e}")
                        # Fall through to PIL-only processing

                else:
                    # PIL-only text enhancement fallback
                    # Increase contrast for better text visibility
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(2.0)

                    # Sharpen for clearer text
                    enhancer = ImageEnhance.Sharpness(img)
                    img = enhancer.enhance(2.0)

                    # Apply a simple threshold by converting to 1-bit mode
                    # This creates a black and white image good for text
                    img = img.point(lambda x: 0 if x < 128 else 255, '1')
                    img = img.convert('L')  # Convert back to grayscale

                # Save processed image
                output_path = self.temp_dir / f"text_enhanced_{original_path.stem}{original_path.suffix}"
                img.save(output_path, quality=95)

                logging.info(f"Text enhancement applied: {image_path} -> {output_path}")
                return str(output_path)

        except Exception as e:
            logging.error(f"Error enhancing image for text recognition {image_path}: {e}")
            return image_path

    def remove_background(self, image_path: str) -> str:
        """
        Simple background removal to focus on the main subject
        """
        try:
            original_path = Path(image_path)

            with Image.open(image_path) as img:
                if CV2_AVAILABLE:
                    try:
                        # Convert to OpenCV
                        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

                        # Simple background removal using GrabCut algorithm
                        height, width = cv_img.shape[:2]
                        mask = np.zeros((height, width), np.uint8)

                        # Define rectangle around the center area (assumed to contain the subject)
                        rect_margin = 50
                        rect = (rect_margin, rect_margin, width - 2*rect_margin, height - 2*rect_margin)

                        bgd_model = np.zeros((1, 65), np.float64)
                        fgd_model = np.zeros((1, 65), np.float64)

                        # Apply GrabCut
                        cv2.grabCut(cv_img, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)

                        # Create final mask
                        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')

                        # Apply mask to original image
                        result = cv_img * mask2[:, :, np.newaxis]

                        # Convert back to PIL
                        img = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))

                    except Exception as e:
                        logging.warning(f"OpenCV background removal failed, using PIL fallback: {e}")
                        # Fall through to PIL-only processing

                else:
                    # PIL-only background removal fallback (simple edge-based cropping)
                    logging.info("Using PIL-only background removal fallback")

                    # Convert to grayscale for edge detection
                    gray = img.convert('L')

                    # Apply edge enhancement to find subject boundaries
                    edges = gray.filter(ImageFilter.FIND_EDGES)

                    # Enhance contrast of edges
                    enhancer = ImageEnhance.Contrast(edges)
                    edges = enhancer.enhance(3.0)

                    # Convert edges to binary
                    threshold = 30
                    edges = edges.point(lambda x: 255 if x > threshold else 0, mode='1')

                    # Find bounding box of non-zero pixels (edges)
                    bbox = edges.getbbox()

                    if bbox:
                        # Add some padding around the detected subject
                        width, height = img.size
                        left, top, right, bottom = bbox

                        padding = 20
                        left = max(0, left - padding)
                        top = max(0, top - padding)
                        right = min(width, right + padding)
                        bottom = min(height, bottom + padding)

                        # Crop to the detected subject area
                        img = img.crop((left, top, right, bottom))

                # Save processed image
                output_path = self.temp_dir / f"bg_removed_{original_path.stem}{original_path.suffix}"
                img.save(output_path, quality=95)

                logging.info(f"Background removal applied: {image_path} -> {output_path}")
                return str(output_path)

        except Exception as e:
            logging.error(f"Error removing background from {image_path}: {e}")
            return image_path

    def cleanup_temp_files(self):
        """Clean up temporary processed images"""
        try:
            for temp_file in self.temp_dir.glob("*"):
                if temp_file.is_file():
                    temp_file.unlink()
            logging.info("Temporary image files cleaned up")
        except Exception as e:
            logging.warning(f"Error cleaning up temp files: {e}")


# Convenience functions
def optimize_image_for_search(image_path: str, enhancement_level: str = "medium") -> str:
    """Optimize an image for search with specified enhancement level"""
    processor = ImageProcessor()
    return processor.optimize_for_search(image_path, enhancement_level)

def create_image_variants(image_path: str, num_variants: int = 3) -> List[str]:
    """Create multiple variants of an image for comprehensive searching"""
    processor = ImageProcessor()
    variants = [processor.optimize_for_search(image_path)]
    variants.extend(processor.create_crop_variants(image_path, num_variants))
    return variants

def enhance_for_text(image_path: str) -> str:
    """Enhance image for better text recognition"""
    processor = ImageProcessor()
    return processor.enhance_for_text_recognition(image_path)


if __name__ == '__main__':
    # Example usage:
    # python image_processor.py "path/to/image.jpg" [--variants] [--text] [--bg-remove]
    import sys

    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        processor = ImageProcessor()

        if "--variants" in sys.argv:
            print(f"Creating optimized variants of: {image_path}")
            variants = create_image_variants(image_path)
            print(f"Created {len(variants)} variants:")
            for i, variant in enumerate(variants, 1):
                print(f"  {i}. {variant}")

        elif "--text" in sys.argv:
            print(f"Enhancing for text recognition: {image_path}")
            result = enhance_for_text(image_path)
            print(f"Text-enhanced image: {result}")

        elif "--bg-remove" in sys.argv:
            print(f"Removing background from: {image_path}")
            result = processor.remove_background(image_path)
            print(f"Background-removed image: {result}")

        else:
            print(f"Optimizing image: {image_path}")
            result = optimize_image_for_search(image_path)
            print(f"Optimized image: {result}")

    else:
        print("Usage:")
        print("  python image_processor.py <image_path>             # Basic optimization")
        print("  python image_processor.py <image_path> --variants  # Create multiple variants")
        print("  python image_processor.py <image_path> --text      # Enhance for text recognition")
        print("  python image_processor.py <image_path> --bg-remove # Remove background")