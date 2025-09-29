#!/usr/bin/env python3
"""
Category-Specific Search Optimization Research Module

This module performs research on specific categories by analyzing successful eBay searches
and learning optimal keywords and patterns for different item types.
"""

import asyncio
import logging
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import Counter, defaultdict
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import statistics


class CategoryOptimizer:
    """Research and optimize search terms for specific categories"""

    def __init__(self):
        self.profiles_dir = Path("optimization_profiles")
        self.profiles_dir.mkdir(exist_ok=True)

        # Built-in category research terms
        self.research_categories = {
            "japanese_gravure": {
                "test_terms": ["japanese gravure", "photo book", "idol photobook", "gravure model"],
                "description": "Japanese gravure models and photo books"
            },
            "anime_figures": {
                "test_terms": ["anime figure", "scale figure", "pvc figure", "nendoroid"],
                "description": "Anime and manga figures"
            },
            "trading_cards": {
                "test_terms": ["trading card", "tcg", "pokemon card", "yugioh card"],
                "description": "Trading card games and collectibles"
            },
            "manga_books": {
                "test_terms": ["manga book", "japanese comic", "doujinshi", "artbook"],
                "description": "Manga, doujinshi, and art books"
            },
            "japanese_games": {
                "test_terms": ["japanese game", "import game", "nintendo japan", "playstation japan"],
                "description": "Japanese video games and imports"
            },
            "collectibles": {
                "test_terms": ["japanese collectible", "limited edition", "exclusive item", "rare item"],
                "description": "General Japanese collectibles"
            }
        }

    async def research_category_optimization(self, category: str, custom_terms: List[str] = None) -> Dict:
        """
        Research optimal search terms for a specific category by analyzing eBay results

        Args:
            category: Category name or 'custom' for custom terms
            custom_terms: Custom search terms if category is 'custom'

        Returns:
            Optimization profile with learned keywords and patterns
        """
        try:
            if category == "custom" and custom_terms:
                test_terms = custom_terms
                description = f"Custom category: {', '.join(custom_terms[:3])}"
            elif category in self.research_categories:
                test_terms = self.research_categories[category]["test_terms"]
                description = self.research_categories[category]["description"]
            else:
                raise ValueError(f"Unknown category: {category}")

            logging.info(f"[CATEGORY OPTIMIZER] Starting research for: {description}")

            research_result = {
                'category': category,
                'description': description,
                'test_terms': test_terms,
                'research_date': datetime.now().isoformat(),
                'learned_keywords': {},
                'price_patterns': {},
                'seller_patterns': {},
                'title_patterns': {},
                'optimization_rules': [],
                'performance_metrics': {}
            }

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                all_successful_titles = []
                all_prices = []
                seller_countries = Counter()
                keyword_effectiveness = {}

                # Test each term and analyze results
                for term in test_terms:
                    logging.info(f"[CATEGORY OPTIMIZER] Researching term: '{term}'")

                    term_results = await self._analyze_search_term(page, term)

                    if term_results['sold_count'] > 0:
                        all_successful_titles.extend(term_results['titles'])
                        all_prices.extend(term_results['prices'])
                        seller_countries.update(term_results['seller_countries'])

                        keyword_effectiveness[term] = {
                            'sold_count': term_results['sold_count'],
                            'avg_price': term_results['avg_price'],
                            'price_range': term_results['price_range'],
                            'top_keywords': term_results['extracted_keywords']
                        }

                await browser.close()

            # Analyze collected data to create optimization profile
            research_result.update(self._analyze_research_data(
                all_successful_titles, all_prices, seller_countries, keyword_effectiveness
            ))

            # Save the optimization profile
            self._save_optimization_profile(category, research_result)

            logging.info(f"[CATEGORY OPTIMIZER] Research complete for {category} - found {len(research_result['learned_keywords'])} key patterns")
            return research_result

        except Exception as e:
            logging.error(f"Error during category optimization research: {e}")
            return {
                'category': category,
                'error': str(e),
                'research_date': datetime.now().isoformat()
            }

    async def _analyze_search_term(self, page, search_term: str) -> Dict:
        """Analyze a specific search term on eBay"""
        try:
            # Search eBay sold listings
            search_url = f"https://www.ebay.com/sch/i.html?_nkw={search_term.replace(' ', '+')}&LH_Sold=1&_ipg=240"
            await page.goto(search_url, wait_until="networkidle")
            await page.wait_for_timeout(2000)

            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Extract sold listings data
            items = soup.select('div.s-item, li.s-item')

            titles = []
            prices = []
            seller_countries = []

            for item in items[:50]:  # Analyze first 50 items
                try:
                    # Extract title
                    title_elem = item.select_one('.s-item__title')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if title and len(title) > 10:  # Filter out short/empty titles
                            titles.append(title)

                    # Extract price
                    price_elem = item.select_one('.s-item__price .notranslate')
                    if not price_elem:
                        price_elem = item.select_one('.s-item__price')

                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        price_match = re.search(r'\$([0-9,]+\.?[0-9]*)', price_text)
                        if price_match:
                            price = float(price_match.group(1).replace(',', ''))
                            prices.append(price)

                    # Extract seller location
                    location_elem = item.select_one('.s-item__location')
                    if location_elem:
                        location = location_elem.get_text(strip=True)
                        if 'from' in location.lower():
                            country = location.split('from')[-1].strip()
                            seller_countries.append(country)

                except Exception as e:
                    continue

            # Extract keywords from successful titles
            extracted_keywords = self._extract_keywords_from_titles(titles)

            return {
                'search_term': search_term,
                'sold_count': len(titles),
                'titles': titles,
                'prices': prices,
                'avg_price': statistics.mean(prices) if prices else 0,
                'price_range': (min(prices), max(prices)) if prices else (0, 0),
                'seller_countries': seller_countries,
                'extracted_keywords': extracted_keywords
            }

        except Exception as e:
            logging.warning(f"Error analyzing search term '{search_term}': {e}")
            return {
                'search_term': search_term,
                'sold_count': 0,
                'titles': [],
                'prices': [],
                'avg_price': 0,
                'price_range': (0, 0),
                'seller_countries': [],
                'extracted_keywords': {}
            }

    def _extract_keywords_from_titles(self, titles: List[str]) -> Dict:
        """Extract and rank keywords from successful listing titles"""
        # Clean and tokenize titles
        all_words = []

        for title in titles:
            # Clean title
            clean_title = re.sub(r'[^\w\s]', ' ', title.lower())
            words = clean_title.split()

            # Filter meaningful words (3+ characters, not numbers only)
            meaningful_words = [
                word for word in words
                if len(word) >= 3 and not word.isdigit() and word.isalpha()
            ]
            all_words.extend(meaningful_words)

        # Count word frequency
        word_counts = Counter(all_words)

        # Remove common stop words
        stop_words = {
            'the', 'and', 'for', 'with', 'from', 'new', 'used', 'rare', 'item',
            'ebay', 'auction', 'buy', 'now', 'free', 'shipping', 'fast', 'good'
        }

        filtered_counts = {
            word: count for word, count in word_counts.items()
            if word not in stop_words and count >= 2  # Appear at least twice
        }

        # Return top keywords with their frequency and percentage
        total_meaningful_words = len(all_words)
        return {
            word: {
                'count': count,
                'percentage': round((count / total_meaningful_words) * 100, 2)
            }
            for word, count in sorted(filtered_counts.items(), key=lambda x: x[1], reverse=True)[:30]
        }

    def _analyze_research_data(self, titles: List[str], prices: List[float],
                             seller_countries: Counter, keyword_effectiveness: Dict) -> Dict:
        """Analyze collected research data to create optimization rules"""

        analysis = {}

        # Analyze learned keywords across all successful searches
        all_keywords = Counter()
        for term_data in keyword_effectiveness.values():
            for keyword, data in term_data['top_keywords'].items():
                all_keywords[keyword] += data['count']

        analysis['learned_keywords'] = dict(all_keywords.most_common(20))

        # Price pattern analysis
        if prices:
            analysis['price_patterns'] = {
                'median': round(statistics.median(prices), 2),
                'mean': round(statistics.mean(prices), 2),
                'std_dev': round(statistics.stdev(prices), 2) if len(prices) > 1 else 0,
                'ranges': {
                    'budget': [p for p in prices if p < 20],
                    'mid_range': [p for p in prices if 20 <= p < 100],
                    'premium': [p for p in prices if p >= 100]
                }
            }

        # Seller patterns
        analysis['seller_patterns'] = {
            'top_countries': dict(seller_countries.most_common(10)),
            'international_ratio': sum(1 for country in seller_countries if 'japan' in country.lower()) / max(len(seller_countries), 1)
        }

        # Title pattern analysis
        common_phrases = self._find_common_phrases(titles)
        analysis['title_patterns'] = {
            'common_phrases': common_phrases,
            'avg_title_length': statistics.mean([len(title) for title in titles]) if titles else 0,
            'common_formats': self._analyze_title_formats(titles)
        }

        # Generate optimization rules
        analysis['optimization_rules'] = self._generate_optimization_rules(analysis, keyword_effectiveness)

        # Performance metrics
        analysis['performance_metrics'] = {
            'total_items_analyzed': len(titles),
            'avg_sold_count_per_term': statistics.mean([data['sold_count'] for data in keyword_effectiveness.values()]) if keyword_effectiveness else 0,
            'most_effective_term': max(keyword_effectiveness.keys(), key=lambda k: keyword_effectiveness[k]['sold_count']) if keyword_effectiveness else None,
            'research_quality_score': self._calculate_research_quality_score(titles, prices, keyword_effectiveness)
        }

        return analysis

    def _find_common_phrases(self, titles: List[str]) -> List[Dict]:
        """Find commonly occurring phrases in titles"""
        phrase_counts = Counter()

        for title in titles:
            words = re.sub(r'[^\w\s]', ' ', title.lower()).split()

            # Extract 2-word and 3-word phrases
            for i in range(len(words) - 1):
                if i < len(words) - 2:
                    three_word = ' '.join(words[i:i+3])
                    if len(three_word) > 8:  # Skip very short phrases
                        phrase_counts[three_word] += 1

                two_word = ' '.join(words[i:i+2])
                if len(two_word) > 5:
                    phrase_counts[two_word] += 1

        # Return phrases that appear multiple times
        return [
            {'phrase': phrase, 'count': count}
            for phrase, count in phrase_counts.most_common(15)
            if count >= 2
        ]

    def _analyze_title_formats(self, titles: List[str]) -> Dict:
        """Analyze common title formatting patterns"""
        formats = {
            'has_brackets': sum(1 for title in titles if '[' in title or ']' in title),
            'has_parentheses': sum(1 for title in titles if '(' in title or ')' in title),
            'has_year': sum(1 for title in titles if re.search(r'\b(19|20)\d{2}\b', title)),
            'has_brand': sum(1 for title in titles if any(brand in title.lower() for brand in ['nintendo', 'sony', 'bandai', 'figma', 'nendoroid'])),
            'all_caps_words': sum(1 for title in titles if any(word.isupper() and len(word) > 2 for word in title.split()))
        }

        total = len(titles)
        return {k: round((v / total) * 100, 1) if total > 0 else 0 for k, v in formats.items()}

    def _generate_optimization_rules(self, analysis: Dict, keyword_effectiveness: Dict) -> List[Dict]:
        """Generate optimization rules based on research findings"""
        rules = []

        # Rule 1: High-value keywords
        if analysis.get('learned_keywords'):
            top_keywords = list(analysis['learned_keywords'].keys())[:5]
            rules.append({
                'type': 'keyword_boost',
                'rule': f"Prioritize these high-performing keywords: {', '.join(top_keywords)}",
                'keywords': top_keywords,
                'confidence': 'high'
            })

        # Rule 2: Price-based optimization
        if analysis.get('price_patterns'):
            median_price = analysis['price_patterns']['median']
            if median_price > 50:
                rules.append({
                    'type': 'price_filter',
                    'rule': f"This category typically sells for ${median_price:.2f}+ - filter low-value results",
                    'min_price_threshold': median_price * 0.5,
                    'confidence': 'medium'
                })

        # Rule 3: Effective search terms
        if keyword_effectiveness:
            best_term = max(keyword_effectiveness.keys(), key=lambda k: keyword_effectiveness[k]['sold_count'])
            rules.append({
                'type': 'primary_term',
                'rule': f"'{best_term}' is most effective - use as primary search term",
                'primary_term': best_term,
                'sold_count': keyword_effectiveness[best_term]['sold_count'],
                'confidence': 'high'
            })

        # Rule 4: Common phrase patterns
        if analysis.get('title_patterns', {}).get('common_phrases'):
            top_phrases = [p['phrase'] for p in analysis['title_patterns']['common_phrases'][:3]]
            rules.append({
                'type': 'phrase_matching',
                'rule': f"Look for these common phrases: {', '.join(top_phrases)}",
                'phrases': top_phrases,
                'confidence': 'medium'
            })

        return rules

    def _calculate_research_quality_score(self, titles: List[str], prices: List[float], keyword_effectiveness: Dict) -> int:
        """Calculate a quality score for the research (0-100)"""
        score = 0

        # Data volume score (0-30 points)
        data_points = len(titles)
        score += min(30, data_points * 0.3)

        # Price data quality (0-25 points)
        if prices and len(prices) > 5:
            score += 25
        elif prices:
            score += 15

        # Search term effectiveness (0-25 points)
        if keyword_effectiveness:
            avg_sold_count = statistics.mean([data['sold_count'] for data in keyword_effectiveness.values()])
            score += min(25, avg_sold_count * 2)

        # Keyword diversity (0-20 points)
        if keyword_effectiveness:
            unique_keywords = set()
            for data in keyword_effectiveness.values():
                unique_keywords.update(data['top_keywords'].keys())
            score += min(20, len(unique_keywords) * 0.5)

        return min(100, int(score))

    def _save_optimization_profile(self, category: str, profile: Dict):
        """Save optimization profile to file"""
        try:
            filename = f"{category}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = self.profiles_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)

            # Also save as latest profile for this category
            latest_filepath = self.profiles_dir / f"{category}_latest.json"
            with open(latest_filepath, 'w', encoding='utf-8') as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)

            logging.info(f"Optimization profile saved: {filepath}")

        except Exception as e:
            logging.error(f"Error saving optimization profile: {e}")

    def load_optimization_profile(self, category: str) -> Optional[Dict]:
        """Load the latest optimization profile for a category"""
        try:
            latest_filepath = self.profiles_dir / f"{category}_latest.json"
            if latest_filepath.exists():
                with open(latest_filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Error loading optimization profile for {category}: {e}")
        return None

    def get_available_categories(self) -> List[str]:
        """Get list of available research categories"""
        return list(self.research_categories.keys())

    def apply_optimization_profile(self, search_term: str, category: str) -> List[str]:
        """Apply learned optimization rules to improve a search term"""
        profile = self.load_optimization_profile(category)
        if not profile:
            return [search_term]  # Return original if no profile available

        optimized_terms = [search_term]

        try:
            # Apply learned keywords
            learned_keywords = profile.get('learned_keywords', {})
            top_keywords = list(learned_keywords.keys())[:3]

            for keyword in top_keywords:
                if keyword.lower() not in search_term.lower():
                    optimized_terms.append(f"{search_term} {keyword}")

            # Apply optimization rules
            rules = profile.get('optimization_rules', [])
            for rule in rules:
                if rule['type'] == 'primary_term' and rule['confidence'] == 'high':
                    primary_term = rule['primary_term']
                    if primary_term not in optimized_terms:
                        optimized_terms.insert(1, primary_term)  # High priority

                elif rule['type'] == 'phrase_matching':
                    for phrase in rule.get('phrases', [])[:2]:  # Top 2 phrases
                        combined_term = f"{phrase} {search_term}"
                        if combined_term not in optimized_terms:
                            optimized_terms.append(combined_term)

            return optimized_terms[:5]  # Return top 5 optimized terms

        except Exception as e:
            logging.error(f"Error applying optimization profile: {e}")
            return [search_term]


# Convenience functions
def research_category_sync(category: str, custom_terms: List[str] = None) -> Dict:
    """Synchronous wrapper for category research"""
    optimizer = CategoryOptimizer()
    return asyncio.run(optimizer.research_category_optimization(category, custom_terms))

def apply_category_optimization(search_term: str, category: str) -> List[str]:
    """Apply category optimization to a search term"""
    optimizer = CategoryOptimizer()
    return optimizer.apply_optimization_profile(search_term, category)


if __name__ == '__main__':
    # Example usage and testing
    import sys

    if len(sys.argv) > 1:
        category = sys.argv[1]

        if category == "list":
            optimizer = CategoryOptimizer()
            categories = optimizer.get_available_categories()
            print("Available research categories:")
            for cat in categories:
                desc = optimizer.research_categories[cat]["description"]
                print(f"  {cat}: {desc}")

        elif category == "custom":
            if len(sys.argv) < 3:
                print("Usage for custom: python category_optimizer.py custom \"term1,term2,term3\"")
                sys.exit(1)

            custom_terms = [term.strip() for term in sys.argv[2].split(',')]
            print(f"Researching custom terms: {custom_terms}")
            result = research_category_sync("custom", custom_terms)

            if result.get('error'):
                print(f"Error: {result['error']}")
            else:
                print(f"Research complete! Quality score: {result['performance_metrics']['research_quality_score']}/100")
                print(f"Top learned keywords: {list(result['learned_keywords'].keys())[:5]}")

        else:
            print(f"Researching category: {category}")
            result = research_category_sync(category)

            if result.get('error'):
                print(f"Error: {result['error']}")
            else:
                print(f"Research complete! Quality score: {result['performance_metrics']['research_quality_score']}/100")
                print(f"Top learned keywords: {list(result['learned_keywords'].keys())[:5]}")
                print(f"Optimization rules generated: {len(result['optimization_rules'])}")

    else:
        print("Usage:")
        print("  python category_optimizer.py <category>              # Research built-in category")
        print("  python category_optimizer.py custom \"term1,term2\"    # Research custom terms")
        print("  python category_optimizer.py list                    # List available categories")
        print("\nExample:")
        print("  python category_optimizer.py japanese_gravure")
        print("  python category_optimizer.py custom \"yura kano,photo book,gravure\"")