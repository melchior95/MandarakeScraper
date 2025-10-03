# Mandarake Scraper - Documentation Index

## Overview
This document serves as a comprehensive index to all documentation files in the Mandarake Scraper project. It provides a roadmap for understanding the project structure, features, and implementation details.

## 📚 Core Documentation

### User-Facing Guides
- **[README.md](README.md)** - Main project documentation, setup instructions, and basic usage
- **[CLAUDE.md](CLAUDE.md)** - Comprehensive development guide for Claude AI and developers
- **[MANDARAKE_CODES.md](MANDARAKE_CODES.md)** - Complete reference for Mandarake store and category codes

### Feature Documentation
- **[NEW_FEATURES.md](NEW_FEATURES.md)** - Recent GUI improvements (New Config button, Space key fix)
- **[LATEST_FEATURES.md](LATEST_FEATURES.md)** - Quality-of-life features (Deselect on empty click, Auto-load CSV, Auto-rename configs)
- **[EBAY_IMAGE_COMPARISON_GUIDE.md](EBAY_IMAGE_COMPARISON_GUIDE.md)** - User guide for eBay image comparison feature
- **[ALERT_TAB_COMPLETE.md](ALERT_TAB_COMPLETE.md)** - Complete documentation for the Review/Alerts workflow system

## 🏗️ Architecture & Implementation

### Development Phases
- **[PHASE1_INFRASTRUCTURE_COMPLETE.md](PHASE1_INFRASTRUCTURE_COMPLETE.md)** - Base infrastructure for modular marketplace tabs
- **[PHASE2_SURUGAYA_COMPLETE.md](PHASE2_SURUGAYA_COMPLETE.md)** - Suruga-ya marketplace implementation
- **[PHASE3_DEJAPAN_PLAN.md](PHASE3_DEJAPAN_PLAN.md)** - Planning for DejaJapan integration

### Refactoring & Planning
- **[REFACTORING_PLAN.md](REFACTORING_PLAN.md)** - GUI refactoring strategy and modularization plan
- **[MODULARIZATION_TODO.md](MODULARIZATION_TODO.md)** - Tasks for breaking down monolithic GUI
- **[MODULAR_TABS_PLAN.md](MODULAR_TABS_PLAN.md)** - Detailed plan for modular tab architecture

### Integration Summaries
- **[INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md)** - Overview of system integrations
- **[UNIFIED_STORES_PLAN.md](UNIFIED_STORES_PLAN.md)** - Plan for unified store management
- **[UNIFIED_STORES_INTEGRATION_COMPLETE.md](UNIFIED_STORES_INTEGRATION_COMPLETE.md)** - Completed unified stores system

## 🛠️ Technical Documentation

### API & Endpoints
- **[api_setup_guide.md](api_setup_guide.md)** - API configuration and setup guide
- **[EBAY_ENDPOINT_SETUP.md](EBAY_ENDPOINT_SETUP.md)** - eBay API endpoint configuration
- **[ebay_exemption_request.md](ebay_exemption_request.md)** - eBay API exemption documentation

### eBay Integration
- **[EBAY_SCRAPER_FIXES.md](EBAY_SCRAPER_FIXES.md)** - eBay scraper fixes and improvements
- **[SOLD_LISTING_MATCHER.md](SOLD_LISTING_MATCHER.md)** - Sold listing matching system documentation

### Marketplaces
- **[SURUGAYA_INTEGRATION_PLAN.md](SURUGAYA_INTEGRATION_PLAN.md)** - Suruga-ya integration planning
- **[SURUGAYA_ADVANCED_SEARCH_COMPLETE.md](SURUGAYA_ADVANCED_SEARCH_COMPLETE.md)** - Advanced search implementation
- **[SURUGAYA_CATEGORIES_COMPLETE.md](SURUGAYA_CATEGORIES_COMPLETE.md)** - Category system completion

## 🐛 Bug Fixes & Issues

### Bug Fix Documentation
- **[BUGFIX_SHOP_CATEGORY_MATCHING.md](BUGFIX_SHOP_CATEGORY_MATCHING.md)** - Shop and category matching fixes
- **[CATEGORY_SELECTION_FIX.md](CATEGORY_SELECTION_FIX.md)** - Category selection issues and solutions
- **[CRITICAL_SPACE_KEY_FIX.md](CRITICAL_SPACE_KEY_FIX.md)** - Space key input fix
- **[SPACE_KEY_FIX.md](SPACE_KEY_FIX.md)** - Space key handling improvements
- **[SPACE_KEY_FINAL_FIX.md](SPACE_KEY_FINAL_FIX.md)** - Final space key fix implementation
- **[DYNAMIC_TREE_UPDATE_FIX.md](DYNAMIC_TREE_UPDATE_FIX.md)** - Tree view update fixes
- **[MINIMAL_STORE_INTEGRATION.md](MINIMAL_STORE_INTEGRATION.md)** - Minimal store integration fixes

## 📋 Session & Development Records

### Session Summaries
- **[SESSION_SUMMARY.md](SESSION_SUMMARY.md)** - General development session summary
- **[COMPLETE_SESSION_SUMMARY.md](COMPLETE_SESSION_SUMMARY.md)** - Complete session documentation
- **[FINAL_SESSION_SUMMARY.md](FINAL_SESSION_SUMMARY.md)** - Final session summary

### Development Logs
- **[setup_guide.md](setup_guide.md)** - Initial setup guide
- **[REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)** - Refactoring completion summary

## 🗂️ File Organization

### Main Directories
```
mandarake_scraper/
├── README.md                    # Main project documentation
├── CLAUDE.md                    # Development guide
├── *.md                         # Various feature and fix documentation
├── gui/                         # Modular GUI components
│   ├── alert_*.py              # Alert system modules
│   ├── base_*.py               # Base classes
│   ├── *_tab.py                # Marketplace tabs
│   └── utils.py                # Shared utilities
├── scrapers/                    # Modular scraper classes
│   ├── base_scraper.py         # Base scraper class
│   └── surugaya_scraper.py     # Suruga-ya scraper
├── configs/                     # Configuration files
├── results/                     # Output files
└── images/                      # Downloaded images
```

### Key Configuration Files
- `user_settings.json` - User preferences and settings
- `alerts.json` - Alert system data
- `category_keywords.json` - Category keyword mappings
- `schedules.json` - Scheduled task configurations

## 🚀 Getting Started

### For New Users
1. Read **[README.md](README.md)** for basic setup and usage
2. Check **[MANDARAKE_CODES.md](MANDARAKE_CODES.md)** for store/category references
3. Review **[EBAY_IMAGE_COMPARISON_GUIDE.md](EBAY_IMAGE_COMPARISON_GUIDE.md)** for price comparison features

### For Developers
1. Start with **[CLAUDE.md](CLAUDE.md)** for comprehensive development context
2. Review **[PHASE1_INFRASTRUCTURE_COMPLETE.md](PHASE1_INFRASTRUCTURE_COMPLETE.md)** for architecture understanding
3. Check **[REFACTORING_PLAN.md](REFACTORING_PLAN.md)** for code organization

### For Adding New Marketplaces
1. Study **[PHASE2_SURUGAYA_COMPLETE.md](PHASE2_SURUGAYA_COMPLETE.md)** as a reference implementation
2. Review **[PHASE1_INFRASTRUCTURE_COMPLETE.md](PHASE1_INFRASTRUCTURE_COMPLETE.md)** for base classes
3. Check **[PHASE3_DEJAPAN_PLAN.md](PHASE3_DEJAPAN_PLAN.md)** for planning approach

## 🔍 Quick Reference

### Core Features
- **Mandarake Scraping**: Primary marketplace scraping with anti-detection
- **eBay Integration**: Price comparison and image matching
- **Alert System**: Complete reselling workflow management
- **GUI Application**: Tkinter-based interface with 4 main tabs
- **Multi-Marketplace**: Modular architecture supporting multiple marketplaces

### Key Technologies
- **Python 3.10+** - Main programming language
- **Tkinter** - GUI framework
- **Requests** - HTTP client with session management
- **BeautifulSoup4** - HTML parsing
- **OpenCV** - Image comparison and computer vision
- **Playwright** - Browser automation for eBay
- **Google APIs** - Sheets and Drive integration

### Main Workflows
1. **Scraping**: Configure → Search → Export results
2. **Price Comparison**: Load CSV → Compare with eBay → Send to alerts
3. **Review Workflow**: Review → Approve → Purchase → Track → Sold
4. **Multi-Marketplace**: Enable marketplaces → Search across all → Compare results

## 📝 Documentation Standards

### File Naming Conventions
- `FEATURE_NAME.md` - Feature documentation
- `BUGFIX_DESCRIPTION.md` - Bug fix documentation
- `PHASE_NUMBER_DESCRIPTION.md` - Development phase documentation
- `COMPONENT_COMPLETE.md` - Completed component documentation

### Documentation Structure
Each markdown file should include:
- Clear title and overview
- Problem statement (for bug fixes)
- Implementation details
- Usage examples
- Testing results
- File change summary

### Maintenance
- Keep documentation updated with code changes
- Use consistent formatting and structure
- Include relevant code examples
- Cross-reference related documentation

---

**Last Updated**: October 3, 2025
**Project Version**: Multi-marketplace scraper with modular GUI
**Documentation Files**: 40+ markdown files covering all aspects of the project
