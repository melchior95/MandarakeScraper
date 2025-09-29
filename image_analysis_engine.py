#!/usr/bin/env python3
"""
Comprehensive Image Analysis Engine

This module combines all image search functionality to provide detailed
market analysis and profit calculations for items identified from images.
"""

import logging
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import statistics

from image_processor import ImageProcessor, optimize_image_for_search, create_image_variants
from ebay_image_search import run_sold_listings_image_search
from google_lens_search import search_ebay_with_lens_sync, identify_product_sync


class ImageAnalysisEngine:
    """Comprehensive engine for image-based market analysis"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.image_processor = ImageProcessor()
        self.results_history = []

    def analyze_image_comprehensive(self, image_path: str,
                                  methods: List[str] = None,
                                  enhancement_levels: List[str] = None,
                                  days_back: int = 90,
                                  lazy_search: bool = True) -> Dict:
        """
        Run comprehensive analysis using multiple methods and enhancements.

        Args:
            image_path: Path to the image to analyze
            methods: List of methods to try ['direct', 'lens', 'hybrid']
            enhancement_levels: List of enhancement levels ['light', 'medium', 'aggressive']
            days_back: Number of days to look back for sold listings
            lazy_search: Whether to use intelligent search optimization

        Returns:
            Comprehensive analysis results
        """
        if methods is None:
            methods = ['direct', 'lens']
        if enhancement_levels is None:
            enhancement_levels = ['medium']

        start_time = datetime.now()
        analysis_id = start_time.strftime("%Y%m%d_%H%M%S")

        logging.info(f"[ANALYSIS ENGINE] Starting comprehensive analysis: {analysis_id}")
        logging.info(f"  Image: {image_path}")
        logging.info(f"  Methods: {methods}")
        logging.info(f"  Enhancement levels: {enhancement_levels}")

        results = {
            'analysis_id': analysis_id,
            'image_path': image_path,
            'start_time': start_time.isoformat(),
            'methods_attempted': [],
            'best_result': None,
            'all_results': [],
            'processing_info': {
                'image_variants_created': 0,
                'searches_performed': 0,
                'total_sold_items_found': 0
            },
            'profit_scenarios': [],
            'recommendations': []
        }

        best_sold_count = 0
        best_result = None

        # Step 1: Create optimized image variants
        try:
            image_variants = []
            for enhancement in enhancement_levels:
                optimized_path = optimize_image_for_search(image_path, enhancement)
                image_variants.append({
                    'path': optimized_path,
                    'enhancement': enhancement,
                    'type': 'optimized'
                })

            # Create crop variants from the best optimized image
            if enhancement_levels:
                crop_variants = create_image_variants(
                    optimize_image_for_search(image_path, enhancement_levels[0]),
                    num_variants=2
                )
                for i, crop_path in enumerate(crop_variants[1:], 1):  # Skip first (original optimized)
                    image_variants.append({
                        'path': crop_path,
                        'enhancement': enhancement_levels[0],
                        'type': f'crop_variant_{i}'
                    })

            results['processing_info']['image_variants_created'] = len(image_variants)

        except Exception as e:
            logging.error(f"Error creating image variants: {e}")
            image_variants = [{'path': image_path, 'enhancement': 'none', 'type': 'original'}]

        # Step 2: Try each method with each image variant
        for method in methods:
            method_results = []

            for variant in image_variants:
                try:
                    logging.info(f"[ANALYSIS ENGINE] Trying {method} method with {variant['type']} enhancement")

                    if method == 'direct':
                        search_result = run_sold_listings_image_search(variant['path'], days_back, lazy_search)
                    elif method == 'lens':
                        search_result = search_ebay_with_lens_sync(variant['path'], days_back, headless=True, lazy_search=lazy_search)
                    elif method == 'hybrid':
                        # Try both methods and combine results
                        direct_result = run_sold_listings_image_search(variant['path'], days_back, lazy_search)
                        lens_result = search_ebay_with_lens_sync(variant['path'], days_back, headless=True, lazy_search=lazy_search)
                        search_result = self._combine_search_results(direct_result, lens_result)
                    else:
                        continue

                    if search_result and search_result.get('sold_count', 0) > 0:
                        search_result['method'] = method
                        search_result['image_variant'] = variant
                        method_results.append(search_result)

                        results['processing_info']['searches_performed'] += 1
                        results['processing_info']['total_sold_items_found'] += search_result['sold_count']

                        # Track best result
                        if search_result['sold_count'] > best_sold_count:
                            best_sold_count = search_result['sold_count']
                            best_result = search_result

                except Exception as e:
                    logging.warning(f"Error with {method} method on {variant['type']}: {e}")
                    continue

            results['methods_attempted'].append({
                'method': method,
                'results_found': len(method_results),
                'best_sold_count': max([r['sold_count'] for r in method_results]) if method_results else 0
            })

            results['all_results'].extend(method_results)

        # Step 3: Set best result and generate profit scenarios
        if best_result:
            results['best_result'] = best_result
            results['profit_scenarios'] = self._generate_profit_scenarios(best_result)
            results['recommendations'] = self._generate_recommendations(best_result, results['all_results'])

        # Step 4: Calculate completion time
        end_time = datetime.now()
        results['end_time'] = end_time.isoformat()
        results['processing_time_seconds'] = (end_time - start_time).total_seconds()

        # Step 5: Save to history
        self.results_history.append(results)

        logging.info(f"[ANALYSIS ENGINE] Analysis complete: {analysis_id}")
        logging.info(f"  Processing time: {results['processing_time_seconds']:.1f}s")
        logging.info(f"  Best result: {best_sold_count} sold items found")

        return results

    def _combine_search_results(self, direct_result: Dict, lens_result: Dict) -> Dict:
        """Combine results from direct and lens searches"""
        if not direct_result.get('sold_count') and not lens_result.get('sold_count'):
            return {'sold_count': 0, 'median_price': 0, 'prices': []}

        # Use the result with more sold items
        if direct_result.get('sold_count', 0) >= lens_result.get('sold_count', 0):
            primary = direct_result
            secondary = lens_result
        else:
            primary = lens_result
            secondary = direct_result

        # Combine unique information
        combined = primary.copy()
        combined['method'] = 'hybrid'
        combined['secondary_method_result'] = secondary

        return combined

    def _generate_profit_scenarios(self, search_result: Dict) -> List[Dict]:
        """Generate profit scenarios based on search results"""
        scenarios = []

        # Configuration for profit calculations
        usd_to_jpy = self.config.get('usd_jpy_rate', 150)
        ebay_fees_percent = 0.13  # eBay + PayPal fees
        shipping_cost = 5.0  # Estimated shipping cost

        median_price = search_result['median_price']
        avg_price = search_result['avg_price']

        # Scenario 1: Conservative (buy at 30% of eBay price)
        conservative_cost_jpy = median_price * usd_to_jpy * 0.3
        conservative_profit = median_price - (median_price * ebay_fees_percent) - shipping_cost - (conservative_cost_jpy / usd_to_jpy)
        conservative_margin = (conservative_profit / median_price) * 100 if median_price > 0 else 0

        scenarios.append({
            'scenario': 'Conservative',
            'description': 'Buy at 30% of eBay median price',
            'purchase_cost_jpy': conservative_cost_jpy,
            'purchase_cost_usd': conservative_cost_jpy / usd_to_jpy,
            'sell_price_usd': median_price,
            'estimated_fees': median_price * ebay_fees_percent + shipping_cost,
            'net_profit_usd': conservative_profit,
            'profit_margin_percent': conservative_margin,
            'risk_level': 'Low'
        })

        # Scenario 2: Moderate (buy at 50% of eBay price)
        moderate_cost_jpy = median_price * usd_to_jpy * 0.5
        moderate_profit = median_price - (median_price * ebay_fees_percent) - shipping_cost - (moderate_cost_jpy / usd_to_jpy)
        moderate_margin = (moderate_profit / median_price) * 100 if median_price > 0 else 0

        scenarios.append({
            'scenario': 'Moderate',
            'description': 'Buy at 50% of eBay median price',
            'purchase_cost_jpy': moderate_cost_jpy,
            'purchase_cost_usd': moderate_cost_jpy / usd_to_jpy,
            'sell_price_usd': median_price,
            'estimated_fees': median_price * ebay_fees_percent + shipping_cost,
            'net_profit_usd': moderate_profit,
            'profit_margin_percent': moderate_margin,
            'risk_level': 'Medium'
        })

        # Scenario 3: Aggressive (buy at 70% of eBay price)
        aggressive_cost_jpy = median_price * usd_to_jpy * 0.7
        aggressive_profit = median_price - (median_price * ebay_fees_percent) - shipping_cost - (aggressive_cost_jpy / usd_to_jpy)
        aggressive_margin = (aggressive_profit / median_price) * 100 if median_price > 0 else 0

        scenarios.append({
            'scenario': 'Aggressive',
            'description': 'Buy at 70% of eBay median price',
            'purchase_cost_jpy': aggressive_cost_jpy,
            'purchase_cost_usd': aggressive_cost_jpy / usd_to_jpy,
            'sell_price_usd': median_price,
            'estimated_fees': median_price * ebay_fees_percent + shipping_cost,
            'net_profit_usd': aggressive_profit,
            'profit_margin_percent': aggressive_margin,
            'risk_level': 'High'
        })

        return scenarios

    def _generate_recommendations(self, best_result: Dict, all_results: List[Dict]) -> List[str]:
        """Generate recommendations based on analysis results"""
        recommendations = []

        sold_count = best_result['sold_count']
        median_price = best_result['median_price']
        price_range = best_result['max_price'] - best_result['min_price']

        # Recommendation based on sold count
        if sold_count >= 20:
            recommendations.append("High market demand - Strong resale potential")
        elif sold_count >= 10:
            recommendations.append("Moderate market demand - Good resale potential")
        elif sold_count >= 5:
            recommendations.append("Limited market demand - Consider carefully")
        else:
            recommendations.append("Very limited market data - High risk")

        # Recommendation based on price stability
        if price_range / median_price < 0.3:  # Less than 30% variation
            recommendations.append("Stable pricing - Predictable market value")
        elif price_range / median_price < 0.6:
            recommendations.append("Moderate price variation - Research condition factors")
        else:
            recommendations.append("High price variation - Condition and rarity greatly affect price")

        # Recommendation based on search method success
        method_success = {}
        for result in all_results:
            method = result.get('method', 'unknown')
            if method not in method_success:
                method_success[method] = []
            method_success[method].append(result['sold_count'])

        if len(method_success) > 1:
            best_method = max(method_success.keys(), key=lambda m: max(method_success[m]))
            recommendations.append(f"Best search method: {best_method}")

        # Price-based recommendations
        if median_price > 100:
            recommendations.append("High-value item - Consider authentication and detailed photos")
        elif median_price < 20:
            recommendations.append("Low-value item - Factor in shipping costs carefully")

        return recommendations

    def save_analysis_report(self, analysis_result: Dict, output_path: Optional[str] = None) -> str:
        """Save comprehensive analysis report to file"""
        if output_path is None:
            output_dir = Path("analysis_reports")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"analysis_{analysis_result['analysis_id']}.json"

        try:
            # Create a JSON-serializable copy
            report_data = analysis_result.copy()

            # Convert datetime objects to strings
            if 'start_time' in report_data:
                report_data['start_time'] = str(report_data['start_time'])
            if 'end_time' in report_data:
                report_data['end_time'] = str(report_data['end_time'])

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            logging.info(f"Analysis report saved: {output_path}")
            return str(output_path)

        except Exception as e:
            logging.error(f"Error saving analysis report: {e}")
            return ""

    def export_profit_scenarios_csv(self, analysis_result: Dict, output_path: Optional[str] = None) -> str:
        """Export profit scenarios to CSV format"""
        if output_path is None:
            output_dir = Path("analysis_reports")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"profit_scenarios_{analysis_result['analysis_id']}.csv"

        try:
            scenarios = analysis_result.get('profit_scenarios', [])
            if not scenarios:
                return ""

            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=scenarios[0].keys())
                writer.writeheader()
                writer.writerows(scenarios)

            logging.info(f"Profit scenarios CSV saved: {output_path}")
            return str(output_path)

        except Exception as e:
            logging.error(f"Error saving profit scenarios CSV: {e}")
            return ""

    def get_analysis_summary(self, analysis_result: Dict) -> str:
        """Get a human-readable summary of the analysis"""
        best_result = analysis_result.get('best_result')
        if not best_result:
            return "No usable results found from image analysis."

        summary_lines = [
            f"📊 Analysis Summary (ID: {analysis_result['analysis_id']})",
            "=" * 50,
            f"🖼️  Image: {Path(analysis_result['image_path']).name}",
            f"⏱️  Processing time: {analysis_result.get('processing_time_seconds', 0):.1f} seconds",
            "",
            "🔍 Search Results:",
            f"   • Method used: {best_result.get('method', 'unknown')}",
            f"   • Sold listings found: {best_result['sold_count']}",
            f"   • Price range: ${best_result['min_price']:.2f} - ${best_result['max_price']:.2f}",
            f"   • Median price: ${best_result['median_price']:.2f}",
            "",
            "💰 Profit Scenarios:"
        ]

        scenarios = analysis_result.get('profit_scenarios', [])
        for scenario in scenarios:
            summary_lines.extend([
                f"   {scenario['scenario']} ({scenario['risk_level']} Risk):",
                f"      - Buy at: ¥{scenario['purchase_cost_jpy']:,.0f} (${scenario['purchase_cost_usd']:.2f})",
                f"      - Net profit: ${scenario['net_profit_usd']:.2f} ({scenario['profit_margin_percent']:.1f}% margin)",
                ""
            ])

        recommendations = analysis_result.get('recommendations', [])
        if recommendations:
            summary_lines.extend([
                "💡 Recommendations:",
                *[f"   • {rec}" for rec in recommendations]
            ])

        return "\n".join(summary_lines)


# Convenience functions
def analyze_image_quick(image_path: str, days_back: int = 90) -> Dict:
    """Quick analysis using default settings"""
    engine = ImageAnalysisEngine()
    return engine.analyze_image_comprehensive(image_path, methods=['direct'], days_back=days_back)

def analyze_image_thorough(image_path: str, days_back: int = 90) -> Dict:
    """Thorough analysis using multiple methods and enhancements"""
    engine = ImageAnalysisEngine()
    return engine.analyze_image_comprehensive(
        image_path,
        methods=['direct', 'lens'],
        enhancement_levels=['light', 'medium', 'aggressive'],
        days_back=days_back
    )


if __name__ == '__main__':
    # Example usage:
    # python image_analysis_engine.py "path/to/image.jpg" [--thorough] [--days=90]
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Comprehensive Image Analysis for eBay Market Research')
    parser.add_argument('image_path', help='Path to the image to analyze')
    parser.add_argument('--thorough', action='store_true', help='Use thorough analysis (multiple methods)')
    parser.add_argument('--days', type=int, default=90, help='Days back to search for sold listings')
    parser.add_argument('--save-report', action='store_true', help='Save detailed report to file')

    args = parser.parse_args()

    print(f"🔍 Analyzing image: {args.image_path}")
    print("=" * 50)

    if args.thorough:
        print("📋 Running thorough analysis (this may take longer)...")
        result = analyze_image_thorough(args.image_path, args.days)
    else:
        print("⚡ Running quick analysis...")
        result = analyze_image_quick(args.image_path, args.days)

    # Print summary
    engine = ImageAnalysisEngine()
    summary = engine.get_analysis_summary(result)
    print(summary)

    # Save report if requested
    if args.save_report:
        report_path = engine.save_analysis_report(result)
        csv_path = engine.export_profit_scenarios_csv(result)
        print(f"\n📄 Reports saved:")
        if report_path:
            print(f"   JSON: {report_path}")
        if csv_path:
            print(f"   CSV:  {csv_path}")