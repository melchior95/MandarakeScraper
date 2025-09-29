#!/usr/bin/env python3
"""
Category Keyword Manager

Manages category keywords for lazy search optimization.
Allows users to define and update category-specific keywords through research.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

class CategoryKeywordManager:
    """Manages category keywords for search optimization"""

    def __init__(self, keywords_file: str = "category_keywords.json"):
        self.keywords_file = Path(keywords_file)
        self.categories = {}
        self.load_keywords()

    def load_keywords(self) -> Dict[str, Any]:
        """Load category keywords from JSON file"""
        try:
            if self.keywords_file.exists():
                with open(self.keywords_file, 'r', encoding='utf-8') as f:
                    self.categories = json.load(f)
                logging.info(f"Loaded {len(self.categories)} categories from {self.keywords_file}")
            else:
                logging.warning(f"Keywords file not found: {self.keywords_file}")
                self.categories = {}
        except Exception as e:
            logging.error(f"Error loading category keywords: {e}")
            self.categories = {}

        return self.categories

    def save_keywords(self) -> bool:
        """Save category keywords to JSON file"""
        try:
            with open(self.keywords_file, 'w', encoding='utf-8') as f:
                json.dump(self.categories, f, indent=2, ensure_ascii=False)
            logging.info(f"Saved category keywords to {self.keywords_file}")
            return True
        except Exception as e:
            logging.error(f"Error saving category keywords: {e}")
            return False

    def get_category_keywords(self, category: str) -> List[str]:
        """Get all keywords for a category (primary + secondary)"""
        if category not in self.categories:
            return []

        keywords = []
        category_data = self.categories[category]

        # Add primary keyword first
        primary = category_data.get('primary_keyword')
        if primary:
            keywords.append(primary)

        # Add secondary keywords (up to 2 more for max 3 total)
        secondary = category_data.get('secondary_keywords', [])
        keywords.extend(secondary[:2])  # Limit to 2 secondary keywords

        return keywords

    def get_primary_keyword(self, category: str) -> Optional[str]:
        """Get the primary keyword for a category"""
        if category not in self.categories:
            return None
        return self.categories[category].get('primary_keyword')

    def get_secondary_keywords(self, category: str) -> List[str]:
        """Get secondary keywords for a category"""
        if category not in self.categories:
            return []
        return self.categories[category].get('secondary_keywords', [])

    def update_category_keywords(self, category: str, primary_keyword: str,
                                secondary_keywords: List[str] = None,
                                description: str = None) -> bool:
        """Update keywords for a category"""
        try:
            if category not in self.categories:
                self.categories[category] = {
                    "primary_keyword": "",
                    "secondary_keywords": [],
                    "description": "",
                    "last_updated": None,
                    "research_data": {
                        "effectiveness_score": None,
                        "common_variants": [],
                        "best_performing": None
                    }
                }

            # Update the keywords
            self.categories[category]['primary_keyword'] = primary_keyword

            if secondary_keywords is not None:
                # Limit to 2 secondary keywords for max 3 total
                self.categories[category]['secondary_keywords'] = secondary_keywords[:2]

            if description is not None:
                self.categories[category]['description'] = description

            self.categories[category]['last_updated'] = datetime.now().isoformat()

            return self.save_keywords()

        except Exception as e:
            logging.error(f"Error updating category {category}: {e}")
            return False

    def update_research_data(self, category: str, effectiveness_score: float = None,
                           common_variants: List[str] = None,
                           best_performing: str = None) -> bool:
        """Update research data for a category"""
        try:
            if category not in self.categories:
                return False

            research_data = self.categories[category].get('research_data', {})

            if effectiveness_score is not None:
                research_data['effectiveness_score'] = effectiveness_score

            if common_variants is not None:
                research_data['common_variants'] = common_variants

            if best_performing is not None:
                research_data['best_performing'] = best_performing

            self.categories[category]['research_data'] = research_data
            self.categories[category]['last_updated'] = datetime.now().isoformat()

            return self.save_keywords()

        except Exception as e:
            logging.error(f"Error updating research data for {category}: {e}")
            return False

    def detect_category_from_text(self, text: str) -> Optional[str]:
        """Detect which category a text belongs to based on keywords"""
        text_lower = text.lower()

        # Check each category's keywords
        for category, data in self.categories.items():
            # Check primary keyword
            primary = data.get('primary_keyword', '').lower()
            if primary and primary in text_lower:
                return category

            # Check secondary keywords
            secondary_keywords = data.get('secondary_keywords', [])
            for keyword in secondary_keywords:
                if keyword.lower() in text_lower:
                    return category

        return None

    def get_all_categories(self) -> List[str]:
        """Get list of all available categories"""
        return list(self.categories.keys())

    def get_category_info(self, category: str) -> Optional[Dict]:
        """Get complete information about a category"""
        return self.categories.get(category)

    def add_new_category(self, category: str, primary_keyword: str,
                        secondary_keywords: List[str] = None,
                        description: str = "") -> bool:
        """Add a new category"""
        if category in self.categories:
            logging.warning(f"Category '{category}' already exists")
            return False

        return self.update_category_keywords(
            category=category,
            primary_keyword=primary_keyword,
            secondary_keywords=secondary_keywords or [],
            description=description
        )

    def remove_category(self, category: str) -> bool:
        """Remove a category"""
        try:
            if category in self.categories:
                del self.categories[category]
                return self.save_keywords()
            return False
        except Exception as e:
            logging.error(f"Error removing category {category}: {e}")
            return False

    def get_search_strategies_for_name(self, name: str) -> List[str]:
        """
        Generate search strategies for a character/product name using category keywords

        Strategy:
        1. Exact match with quotes
        2. Core name + primary keyword for each category
        3. Core name + secondary keywords (if available)
        """
        strategies = []

        # Strategy 1: Exact match with quotes
        strategies.append(f'"{name}"')

        # Get core name (first 2 words if multiple)
        name_words = name.split()
        core_name = ' '.join(name_words[:2]) if len(name_words) > 1 else name

        # Strategy 2 & 3: Add category combinations
        for category in self.categories:
            keywords = self.get_category_keywords(category)

            for i, keyword in enumerate(keywords):
                if i == 0:
                    # Primary keyword - higher priority
                    strategies.insert(2, f"{core_name} {keyword}")
                else:
                    # Secondary keywords - lower priority
                    strategies.append(f"{core_name} {keyword}")

        return strategies

    def export_keywords(self, export_path: str) -> bool:
        """Export keywords to a file"""
        try:
            export_file = Path(export_path)
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(self.categories, f, indent=2, ensure_ascii=False)
            logging.info(f"Keywords exported to {export_path}")
            return True
        except Exception as e:
            logging.error(f"Error exporting keywords: {e}")
            return False

    def import_keywords(self, import_path: str) -> bool:
        """Import keywords from a file"""
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                raise FileNotFoundError(f"Import file not found: {import_path}")

            with open(import_file, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)

            self.categories.update(imported_data)
            success = self.save_keywords()

            if success:
                logging.info(f"Keywords imported from {import_path}")

            return success

        except Exception as e:
            logging.error(f"Error importing keywords: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the keyword database"""
        total_categories = len(self.categories)
        categories_with_research = sum(1 for cat in self.categories.values()
                                     if cat.get('research_data', {}).get('effectiveness_score') is not None)

        avg_keywords_per_category = sum(len(self.get_category_keywords(cat))
                                       for cat in self.categories) / max(total_categories, 1)

        return {
            'total_categories': total_categories,
            'categories_with_research_data': categories_with_research,
            'average_keywords_per_category': round(avg_keywords_per_category, 1),
            'categories': list(self.categories.keys())
        }


# Global instance
_keyword_manager = None

def get_keyword_manager() -> CategoryKeywordManager:
    """Get the global keyword manager instance"""
    global _keyword_manager
    if _keyword_manager is None:
        _keyword_manager = CategoryKeywordManager()
    return _keyword_manager


if __name__ == '__main__':
    # Example usage and testing
    import sys

    manager = CategoryKeywordManager()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "list":
            print("=== CATEGORY KEYWORDS ===")
            for category in manager.get_all_categories():
                keywords = manager.get_category_keywords(category)
                info = manager.get_category_info(category)
                print(f"\n{category.upper()}:")
                print(f"  Keywords: {keywords}")
                print(f"  Description: {info.get('description', 'No description')}")
                print(f"  Last Updated: {info.get('last_updated', 'Never')}")

        elif command == "test" and len(sys.argv) > 2:
            test_name = ' '.join(sys.argv[2:])
            print(f"=== SEARCH STRATEGIES FOR: {test_name} ===")
            strategies = manager.get_search_strategies_for_name(test_name)
            for i, strategy in enumerate(strategies, 1):
                print(f"{i:2d}. {strategy}")

        elif command == "stats":
            stats = manager.get_stats()
            print("=== KEYWORD DATABASE STATISTICS ===")
            for key, value in stats.items():
                print(f"{key.replace('_', ' ').title()}: {value}")

        else:
            print("Unknown command")

    else:
        print("Category Keyword Manager")
        print("\nCommands:")
        print("  python category_keyword_manager.py list                    # List all categories")
        print("  python category_keyword_manager.py test <name>             # Test search strategies")
        print("  python category_keyword_manager.py stats                   # Show statistics")
        print("\nExample:")
        print("  python category_keyword_manager.py test 'Yura Kano'       # Test strategies for Yura Kano")