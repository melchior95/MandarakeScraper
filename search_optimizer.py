#!/usr/bin/env python3
"""
Search Term Optimization Module for Better eBay Matching

This module provides "lazy search" functionality that optimizes and simplifies
search terms to improve matching with eBay sold listings.
"""

import re
import logging
from typing import List, Set, Dict, Tuple
from collections import Counter
from category_keyword_manager import get_keyword_manager


class SearchOptimizer:
    """Class for optimizing search terms for better eBay results"""

    def __init__(self):
        # Initialize category keyword manager
        self.keyword_manager = get_keyword_manager()

        # Common words to remove or deprioritize
        self.stop_words = {
            # English
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'over', 'after', 'new', 'used', 'rare',
            'limited', 'edition', 'special', 'original', 'authentic', 'genuine', 'official',

            # Japanese/Romanized
            'no', 'wo', 'ga', 'ni', 'de', 'wa', 'ka', 'to', 'ya', 'mo', 'kara', 'made',
            'desu', 'da', 'nan', 'nani', 'doko', 'itsu', 'dare', 'dou', 'naze'
        }

        # Product type keywords that help with matching
        self.product_keywords = {
            'photo', 'book', 'collection', 'album', 'gravure', 'idol', 'actress',
            'model', 'japanese', 'japan', 'jav', 'figure', 'poster', 'dvd', 'cd',
            'magazine', 'artbook', 'photobook', 'calendar', 'trading', 'card'
        }

        # Category combinations that should be prioritized
        self.category_combinations = {
            'photo book': ['photobook', 'photo book', 'gravure book'],
            'photobook': ['photo book', 'photobook', 'gravure book'],
            'gravure': ['gravure', 'photo book', 'idol book'],
            'figure': ['figure', 'anime figure', 'collectible figure'],
            'trading card': ['trading card', 'tcg', 'card game'],
            'artbook': ['artbook', 'art book', 'illustration book'],
            'magazine': ['magazine', 'photo magazine', 'idol magazine'],
            'calendar': ['calendar', 'photo calendar', 'idol calendar'],
            'poster': ['poster', 'photo poster', 'art poster']
        }

        # Name variations and romanization patterns
        self.name_patterns = {
            # Common romanization variations
            'ou': ['o', 'ou', 'oo'],
            'uu': ['u', 'uu'],
            'ei': ['ei', 'e'],
            'ai': ['ai', 'a'],
            'wo': ['wo', 'o'],
            'tsu': ['tsu', 'tu'],
            'chi': ['chi', 'ti'],
            'shi': ['shi', 'si'],
            'fu': ['fu', 'hu']
        }

    def optimize_search_term(self, original_term: str, lazy_mode: bool = True, category: str = None) -> Dict:
        """
        Optimize a search term for better eBay matching

        Args:
            original_term: The original search term
            lazy_mode: Whether to apply aggressive simplification
            category: Optional category for applying learned optimizations

        Returns:
            Dict containing optimized variations and strategies
        """
        try:
            result = {
                'original': original_term,
                'core_terms': [],
                'variations': [],
                'strategies': [],
                'confidence_order': []
            }

            if not original_term or not original_term.strip():
                return result

            # Step 1: Extract core terms
            core_terms = self._extract_core_terms(original_term)
            result['core_terms'] = core_terms

            if lazy_mode:
                # Step 2: Generate simplified variations
                variations = self._generate_lazy_variations(original_term, core_terms)
                result['variations'] = variations

                # Step 2.5: Apply category-specific optimizations if available
                if category:
                    category_variations = self._apply_category_optimizations(original_term, category)
                    variations.extend(category_variations)
                    result['variations'] = list(dict.fromkeys(variations))  # Remove duplicates
                    result['category_applied'] = category

                # Step 3: Create search strategies
                strategies = self._create_search_strategies(core_terms, variations)
                result['strategies'] = strategies

                # Step 4: Order by confidence
                result['confidence_order'] = self._order_by_confidence(strategies)
            else:
                # Non-lazy mode: just clean up the original term
                clean_term = self._clean_term(original_term)
                result['variations'] = [clean_term] if clean_term != original_term else []
                result['strategies'] = [clean_term]
                result['confidence_order'] = [clean_term]

            logging.info(f"[SEARCH OPTIMIZER] Generated {len(result['confidence_order'])} search variations")
            return result

        except Exception as e:
            logging.error(f"Error optimizing search term '{original_term}': {e}")
            return {
                'original': original_term,
                'core_terms': [original_term],
                'variations': [],
                'strategies': [original_term],
                'confidence_order': [original_term]
            }

    def _extract_core_terms(self, text: str) -> List[str]:
        """Extract the most important terms from the text"""
        # Clean and normalize
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = text.split()

        # Remove stop words but keep product keywords
        core_words = []
        for word in words:
            if len(word) > 2:  # Skip very short words
                if word in self.product_keywords:
                    core_words.append(word)
                elif word not in self.stop_words:
                    core_words.append(word)

        return core_words

    def _generate_lazy_variations(self, original: str, core_terms: List[str]) -> List[str]:
        """Generate multiple variations for lazy search using category keyword system"""
        variations = []

        # Get name terms (exclude product keywords)
        name_terms = [term for term in core_terms if term not in self.product_keywords]

        if not name_terms:
            return [' '.join(core_terms)]

        # Get core name - first 2 words if multiple, otherwise full name
        core_name = ' '.join(name_terms[:2]) if len(name_terms) > 1 else ' '.join(name_terms)
        full_name = ' '.join(name_terms)

        # Strategy 1: Full name terms
        variations.append(full_name)

        # Strategy 2 & 3: Use category keyword manager for structured keywords
        # Get all categories and their keywords
        for category in self.keyword_manager.get_all_categories():
            keywords = self.keyword_manager.get_category_keywords(category)

            for i, keyword in enumerate(keywords):
                if i == 0:
                    # Primary keyword - use core name for conciseness
                    variation = f"{core_name} {keyword}"
                    if variation not in variations:
                        variations.insert(1, variation)  # High priority
                else:
                    # Secondary keywords - use core name
                    variation = f"{core_name} {keyword}"
                    if variation not in variations:
                        variations.append(variation)  # Lower priority

        # Additional variation: Core name only (for broad search)
        if core_name not in variations:
            variations.append(core_name)

        # Additional variation: Core terms (including product keywords if any)
        core_terms_str = ' '.join(core_terms)
        if core_terms_str not in variations:
            variations.append(core_terms_str)

        return variations

    def _get_romanization_alternatives(self, term: str) -> List[str]:
        """Get romanization alternatives for a term"""
        alternatives = []
        term_lower = term.lower()

        for pattern, variants in self.name_patterns.items():
            if pattern in term_lower:
                for variant in variants:
                    if variant != pattern:
                        alt_term = term_lower.replace(pattern, variant)
                        if alt_term != term_lower:
                            alternatives.append(alt_term)

        return alternatives

    def _detect_categories(self, text: str) -> List[List[str]]:
        """Detect product categories in the text and return their variants"""
        detected = []

        # Check for exact matches and partial matches
        for category_key, variants in self.category_combinations.items():
            # Check for exact phrase match
            if category_key in text:
                detected.append(variants)
                continue

            # Check for individual words that might form a category
            category_words = category_key.split()
            if len(category_words) > 1:
                # Check if all words of the category appear in the text
                if all(word in text for word in category_words):
                    detected.append(variants)
                    continue

            # Check if any individual category word appears
            for word in category_words:
                if word in text and len(word) > 3:  # Only longer words to avoid false matches
                    detected.append(variants)
                    break

        # Also detect individual product keywords and suggest related categories
        found_keywords = [word for word in self.product_keywords if word in text]
        for keyword in found_keywords:
            # Map individual keywords to likely categories
            if keyword in ['photo', 'gravure'] and not any('photo book' in str(d) for d in detected):
                detected.append(['photo book', 'photobook', 'gravure book'])
            elif keyword == 'book' and not any('book' in str(d) for d in detected):
                detected.append(['photo book', 'art book', 'photobook'])
            elif keyword == 'figure' and not any('figure' in str(d) for d in detected):
                detected.append(['figure', 'anime figure', 'collectible figure'])
            elif keyword in ['trading', 'card'] and not any('trading card' in str(d) for d in detected):
                detected.append(['trading card', 'tcg', 'card game'])

        # If no categories detected and this looks like a character/person name, suggest common categories
        if not detected and self._looks_like_character_name(text):
            # For character names without explicit product type, suggest common Japanese collectible categories
            detected.append(['photobook', 'photo book', 'gravure book'])
            detected.append(['figure', 'anime figure', 'collectible figure'])

        return detected

    def _looks_like_character_name(self, text: str) -> bool:
        """Determine if text looks like a character or person name"""
        # Check for patterns that suggest this is a character name
        words = text.split()

        # If it has 2-4 words and no obvious product keywords, likely a character name
        if 2 <= len(words) <= 4:
            # Check if it contains obvious product keywords
            has_product_keywords = any(word in self.product_keywords for word in words)

            # Check for common character name patterns
            has_name_pattern = any([
                # Japanese name patterns
                any(word.endswith('ko') or word.endswith('ka') or word.endswith('mi')
                    or word.endswith('na') or word.endswith('ri') for word in words),
                # Common title words that suggest character names
                any(word in ['magical', 'girlfriend', 'angel', 'princess', 'chan', 'kun'] for word in words),
                # Capitalized words (likely proper names)
                any(word[0].isupper() if word else False for word in words)
            ])

            # If it has name patterns but no explicit product keywords, likely a character
            return has_name_pattern and not has_product_keywords

        return False

    def _create_search_strategies(self, core_terms: List[str], variations: List[str]) -> List[str]:
        """Create ordered search strategies using new category keyword system"""
        strategies = []

        # Get name terms (exclude product keywords)
        name_terms = [term for term in core_terms if term not in self.product_keywords]
        original_clean = self._clean_term(' '.join(core_terms))

        # Strategy 1: Exact match with quotes (if original has multiple words)
        if ' ' in original_clean:
            strategies.append(f'"{original_clean}"')

        # Get core name for strategies 2 & 3
        if name_terms:
            core_name = ' '.join(name_terms[:2]) if len(name_terms) > 1 else ' '.join(name_terms)

            # Strategy 2: Core name + primary keywords from detected categories first
            detected_categories = self._detect_categories(original_clean.lower())

            # Add detected category primary keywords first
            for category_variants in detected_categories:
                # Find which category this variant belongs to
                for category in self.keyword_manager.get_all_categories():
                    primary_keyword = self.keyword_manager.get_primary_keyword(category)
                    if primary_keyword and primary_keyword in category_variants:
                        strategy = f"{core_name} {primary_keyword}"
                        if strategy not in strategies:
                            strategies.append(strategy)
                        break

            # Then add other category primary keywords
            for category in self.keyword_manager.get_all_categories():
                primary_keyword = self.keyword_manager.get_primary_keyword(category)
                if primary_keyword:
                    strategy = f"{core_name} {primary_keyword}"
                    if strategy not in strategies:
                        strategies.append(strategy)

            # Strategy 3: Core name + secondary keywords (detected categories first)
            for category_variants in detected_categories:
                for category in self.keyword_manager.get_all_categories():
                    secondary_keywords = self.keyword_manager.get_secondary_keywords(category)
                    for secondary in secondary_keywords:
                        if secondary in category_variants:
                            strategy = f"{core_name} {secondary}"
                            if strategy not in strategies:
                                strategies.append(strategy)

            # Then other secondary keywords
            for category in self.keyword_manager.get_all_categories():
                secondary_keywords = self.keyword_manager.get_secondary_keywords(category)
                for keyword in secondary_keywords:
                    strategy = f"{core_name} {keyword}"
                    if strategy not in strategies:
                        strategies.append(strategy)

            # Strategy 4: Core name only
            core_name_only = ' '.join(name_terms[:2]) if len(name_terms) > 1 else ' '.join(name_terms)
            if core_name_only not in strategies:
                strategies.append(core_name_only)

        # Strategy 5: Original term as-is (fallback)
        if original_clean not in strategies:
            strategies.append(original_clean)

        return strategies

    def _order_by_confidence(self, strategies: List[str]) -> List[str]:
        """Order strategies by expected matching confidence"""
        def confidence_score(strategy: str) -> Tuple[int, int, int]:
            # Score based on: (has_quotes, word_count, length)
            has_quotes = 1 if strategy.startswith('"') and strategy.endswith('"') else 0
            word_count = len(strategy.replace('"', '').split())
            length = len(strategy)

            # Prefer: quoted phrases, 2-3 words, moderate length
            word_score = 3 if word_count in [2, 3] else (2 if word_count == 1 else 1)

            return (has_quotes, word_score, -length)  # Negative length for shorter preferred

        return sorted(strategies, key=confidence_score, reverse=True)

    def _clean_term(self, term: str) -> str:
        """Clean and normalize a search term"""
        if not term:
            return ""

        # Remove extra quotes, normalize spacing
        term = re.sub(r'["""''`]', '"', term)
        term = re.sub(r'\s+', ' ', term.strip())

        return term

    def _apply_category_optimizations(self, original_term: str, category: str) -> List[str]:
        """Apply learned category-specific optimizations"""
        try:
            from category_optimizer import CategoryOptimizer
            optimizer = CategoryOptimizer()
            return optimizer.apply_optimization_profile(original_term, category)
        except Exception as e:
            logging.warning(f"Could not apply category optimizations for {category}: {e}")
            return []

    def generate_progressive_searches(self, original_term: str, max_searches: int = 5) -> List[str]:
        """
        Generate a progressive list of search terms from most specific to most general
        """
        optimization = self.optimize_search_term(original_term, lazy_mode=True)

        # Get the ordered strategies, limited to max_searches
        progressive_searches = optimization['confidence_order'][:max_searches]

        # Ensure we have at least the original term
        if not progressive_searches:
            progressive_searches = [original_term]
        elif original_term not in progressive_searches:
            progressive_searches.insert(0, original_term)

        return progressive_searches[:max_searches]

    def generate_strategic_csv_searches(self, csv_title: str, category: str = None) -> List[str]:
        """
        Generate strategic search terms for CSV-based searches with fallback strategies

        Strategy 1: Full name from CSV title
        Strategy 2: Core name + category keyword 1
        Strategy 3: Core name + category keyword 2
        Strategy 4: Optimized name (meaningful but not too simple)

        Args:
            csv_title: The full title from the CSV
            category: Optional category for keyword selection

        Returns:
            List of search terms in strategy order (most specific to general)
        """
        strategies = []

        if not csv_title or not csv_title.strip():
            return strategies

        # Strategy 1: Full name from CSV title (cleaned)
        full_name = self._clean_csv_title(csv_title)
        if full_name:
            strategies.append(full_name)
            logging.debug(f"Strategy 1 (Full CSV title): '{full_name}'")

        # Extract core name for other strategies
        core_name = self._extract_core_name_from_csv(csv_title)
        if not core_name:
            return strategies  # Can't do other strategies without core name

        # Strategy 2 & 3: Core name + category keywords
        category_keywords = self._get_category_keywords_for_csv(csv_title, category)

        for i, keyword in enumerate(category_keywords[:2], 2):  # Max 2 category keywords
            strategy = f"{core_name} {keyword}".strip()
            if strategy and strategy not in strategies:
                strategies.append(strategy)
                logging.debug(f"Strategy {i} (Core + category {i-1}): '{strategy}'")

        # Strategy 4: Optimized name (remove redundant words but keep meaningful)
        optimized_name = self._create_optimized_csv_name(csv_title, core_name)
        if optimized_name and optimized_name not in strategies:
            strategies.append(optimized_name)
            logging.debug(f"Strategy 4 (Optimized): '{optimized_name}'")

        return strategies

    def _clean_csv_title(self, title: str) -> str:
        """Clean CSV title for Strategy 1"""
        if not title:
            return ""

        # Remove common CSV artifacts
        cleaned = title.strip()

        # Remove brackets and parentheses content that might be metadata
        cleaned = re.sub(r'\[.*?\]', '', cleaned)
        cleaned = re.sub(r'\(.*?\)', '', cleaned)

        # Remove multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # Don't make it too short after cleaning
        if len(cleaned.split()) < 2:
            # If cleaned version is too short, use original but still remove obvious metadata
            cleaned = title.strip()
            cleaned = re.sub(r'\(20\d{2}.*?\)', '', cleaned)  # Remove year info
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        return cleaned

    def _extract_core_name_from_csv(self, csv_title: str) -> str:
        """Extract core name (person/main subject) from CSV title"""
        if not csv_title:
            return ""

        # Remove product keywords to get the core name
        words = csv_title.lower().split()
        core_words = []

        # Take the first few non-product words as core name
        for word in words:
            if word not in self.product_keywords and word not in self.stop_words:
                core_words.append(word)
                # Don't make core name too long
                if len(core_words) >= 2:
                    break

        # Ensure core name isn't too short/generic
        core_name = ' '.join(core_words)
        if len(core_name) < 3:  # Too short like "yu"
            # Try to get one more word
            for word in words:
                if word not in core_words and word not in self.stop_words:
                    core_words.append(word)
                    break

        return ' '.join(core_words)

    def _get_category_keywords_for_csv(self, csv_title: str, category: str = None) -> List[str]:
        """Get category keywords for CSV search strategies"""
        keywords = []

        # If category is provided, get its keywords first
        if category and self.keyword_manager:
            primary = self.keyword_manager.get_primary_keyword(category)
            if primary:
                keywords.append(primary)

            secondary = self.keyword_manager.get_secondary_keywords(category)
            if secondary:
                keywords.extend(secondary[:1])  # Add first secondary keyword

        # Auto-detect category from title if no category provided
        if not keywords:
            detected_categories = self._detect_categories(csv_title.lower())
            for category_variants in detected_categories[:2]:  # Max 2 categories
                for cat in self.keyword_manager.get_all_categories():
                    primary = self.keyword_manager.get_primary_keyword(cat)
                    if primary and primary in category_variants:
                        if primary not in keywords:
                            keywords.append(primary)
                        break

        # Fallback: Use common product keywords found in title
        if not keywords:
            title_lower = csv_title.lower()
            for keyword in ['photobook', 'figure', 'poster', 'dvd', 'magazine']:
                if keyword in title_lower and keyword not in keywords:
                    keywords.append(keyword)
                    if len(keywords) >= 2:
                        break

        return keywords[:2]  # Max 2 keywords

    def _create_optimized_csv_name(self, csv_title: str, core_name: str) -> str:
        """Create optimized name for Strategy 4 - meaningful but simplified"""
        if not csv_title or not core_name:
            return ""

        # Start with core name
        words = core_name.split()

        # Add one important product keyword if present
        title_lower = csv_title.lower()
        important_keywords = ['photobook', 'figure', 'poster', 'dvd', 'gravure']

        for keyword in important_keywords:
            if keyword in title_lower:
                words.append(keyword)
                break

        optimized = ' '.join(words)

        # Ensure it's not too simple (like just "yura")
        if len(optimized.split()) == 1 and len(optimized) < 4:
            # Add back some context from original
            original_words = csv_title.split()
            for word in original_words:
                if word.lower() not in words and word.lower() not in self.stop_words:
                    optimized = f"{optimized} {word.lower()}"
                    break

        return optimized


# Convenience functions
def optimize_for_ebay_search(search_term: str, lazy_mode: bool = True) -> Dict:
    """Optimize a search term for eBay searching"""
    optimizer = SearchOptimizer()
    return optimizer.optimize_search_term(search_term, lazy_mode)

def generate_csv_search_strategies(csv_title: str, category: str = None) -> List[str]:
    """
    Generate strategic search terms for CSV-based searches

    Returns list of search strategies in order:
    1. Full CSV title (cleaned)
    2. Core name + category keyword 1
    3. Core name + category keyword 2
    4. Optimized name (meaningful but simplified)

    Args:
        csv_title: The full title from CSV
        category: Optional category for keyword selection

    Returns:
        List of search terms to try in order (most specific first)
    """
    optimizer = SearchOptimizer()
    return optimizer.generate_strategic_csv_searches(csv_title, category)

def get_progressive_search_terms(search_term: str, max_terms: int = 5) -> List[str]:
    """Get progressive search terms from specific to general"""
    optimizer = SearchOptimizer()
    return optimizer.generate_progressive_searches(search_term, max_terms)


if __name__ == '__main__':
    # Example usage and testing
    import sys

    if len(sys.argv) > 1:
        test_term = sys.argv[1]
        lazy_mode = "--lazy" in sys.argv or len(sys.argv) == 2

        optimizer = SearchOptimizer()
        result = optimizer.optimize_search_term(test_term, lazy_mode)

        print(f"Original: {result['original']}")
        print(f"Core terms: {result['core_terms']}")
        print(f"Variations: {result['variations']}")
        print(f"Search strategies (ordered by confidence):")
        for i, strategy in enumerate(result['confidence_order'], 1):
            print(f"  {i}. {strategy}")

        print(f"\nProgressive search terms:")
        progressive = optimizer.generate_progressive_searches(test_term)
        for i, term in enumerate(progressive, 1):
            print(f"  {i}. {term}")
    else:
        print("Usage:")
        print("  python search_optimizer.py \"search term\" [--lazy]")
        print("\nExample:")
        print("  python search_optimizer.py \"Yura Kano photo book collection\"")