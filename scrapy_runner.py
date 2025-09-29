#!/usr/bin/env python3
"""
Scrapy runner for eBay search integration with GUI
"""

import os
import sys
import json
import logging
import tempfile
import subprocess
from typing import List, Dict, Any
from multiprocessing import Process, Queue
import threading
import time

# Add scrapy_ebay to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scrapy_ebay'))


class ScrapyEbayRunner:
    """Runner class for eBay Scrapy spider"""

    def __init__(self):
        self.results = []
        self.is_running = False
        self.logger = logging.getLogger(__name__)

    def run_spider(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Run the eBay spider and return results using subprocess"""
        self.results = []
        self.is_running = True

        try:
            # Create temporary output file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
                output_file = f.name

            self.logger.info(f"Starting Scrapy spider for query: {query}")
            self.logger.info(f"Max results: {max_results}")

            # Use scrapy command line to avoid reactor conflicts
            cmd = [
                sys.executable, '-m', 'scrapy', 'crawl', 'ebay',
                '-a', f'query={query}',
                '-a', f'max_results={max_results}',
                '-o', output_file,
                '-s', 'LOG_LEVEL=INFO',
                '-s', 'ROBOTSTXT_OBEY=False',
                '-s', 'DOWNLOAD_DELAY=1'
            ]

            # Run subprocess
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
                cwd=os.path.dirname(__file__)
            )

            if result.returncode != 0:
                self.logger.error(f"Spider subprocess failed with return code {result.returncode}")
                self.logger.error(f"stderr: {result.stderr}")

            # Read results
            try:
                if os.path.exists(output_file):
                    with open(output_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            # Handle JSONL format (one JSON object per line)
                            results = []
                            for line in content.split('\n'):
                                line = line.strip()
                                if line:
                                    try:
                                        results.append(json.loads(line))
                                    except json.JSONDecodeError as e:
                                        self.logger.warning(f"Failed to parse JSON line: {e}")

                            self.results = results
                            self.logger.info(f"Loaded {len(self.results)} results from spider")
                        else:
                            self.logger.warning("Output file is empty")

                    # Clean up
                    os.unlink(output_file)

                else:
                    self.logger.error(f"Output file not found: {output_file}")

            except Exception as e:
                self.logger.error(f"Error reading spider results: {e}")

        except Exception as e:
            self.logger.error(f"Error running spider: {e}")
        finally:
            self.is_running = False

        return self.results


    def run_spider_async(self, query: str, max_results: int = 5, callback=None):
        """Run spider asynchronously in thread"""
        def worker():
            results = self.run_spider(query, max_results)
            if callback:
                callback(results)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return thread


def test_scrapy_runner():
    """Test the Scrapy runner"""
    logging.basicConfig(level=logging.INFO)

    runner = ScrapyEbayRunner()
    results = runner.run_spider("pokemon card pikachu", max_results=3)

    print(f"\nScrapy Spider Results ({len(results)} items):")
    print("=" * 50)

    for i, result in enumerate(results, 1):
        print(f"\nItem {i}:")
        print(f"Title: {result.get('title', 'N/A')}")
        print(f"Price: {result.get('price', 'N/A')}")
        print(f"Condition: {result.get('condition', 'N/A')}")
        print(f"Images: {len(result.get('image_urls', []))} found")
        print(f"URL: {result.get('item_url', 'N/A')}")

        if result.get('image_urls'):
            print("Image URLs:")
            for j, img_url in enumerate(result['image_urls'][:3], 1):
                print(f"  {j}. {img_url}")


if __name__ == "__main__":
    test_scrapy_runner()