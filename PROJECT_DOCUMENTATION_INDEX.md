# Mandarake Scraper - Documentation Index

## Overview
This document serves as a comprehensive index to all documentation files in the Mandarake Scraper project. It provides a roadmap for understanding the project structure, features, and implementation details.

**Last Updated**: October 4, 2025
**Status**: Active Development

---

## 📚 Essential Documentation

### Getting Started
1. **[README.md](README.md)** - Main project documentation, setup instructions, and basic usage
2. **[setup_guide.md](setup_guide.md)** - Detailed installation and configuration guide
3. **[MANDARAKE_CODES.md](MANDARAKE_CODES.md)** - Complete reference for Mandarake store and category codes

### Development Guide
- **[CLAUDE.md](CLAUDE.md)** - Comprehensive development guide for AI assistants and developers

---

## 🏗️ Architecture & Implementation

### Core Architecture
- **[GUI_MODULARIZATION_COMPLETE.md](GUI_MODULARIZATION_COMPLETE.md)** - Complete GUI modularization documentation
  - Architecture overview
  - Module dependencies
  - Refactoring phases (1-7)
  - Metrics: 63% code reduction (4000+ → 1473 lines)
  - 20+ modules created
  - All improvements and lessons learned

### Module Structure
```
gui_config.py (1473 lines)
├── gui/mandarake_tab.py      - Store/category/config UI
├── gui/ebay_tab.py            - eBay search and CSV comparison
├── gui/advanced_tab.py        - Advanced settings
├── gui/alert_tab.py           - Review/Alerts workflow
├── gui/window_manager.py      - Window geometry management
├── gui/menu_manager.py        - Menu bar and dialogs
├── gui/configuration_manager.py
├── gui/tree_manager.py
├── gui/csv_comparison_manager.py
├── gui/ebay_search_manager.py
├── gui/alert_manager.py
└── gui/utils.py               - Shared utilities
```

---

## 🚀 Feature Documentation

### Alert System
- **[ALERT_TAB_COMPLETE.md](ALERT_TAB_COMPLETE.md)** - Complete documentation for the Review/Alerts workflow
  - State machine: Pending → Yay → Purchased → Shipped → Received → Posted → Sold
  - Bulk operations
  - Threshold filtering
  - JSON persistence

### eBay Integration
- **[EBAY_IMAGE_COMPARISON_GUIDE.md](EBAY_IMAGE_COMPARISON_GUIDE.md)** - User guide for eBay image comparison
  - Multi-metric computer vision
  - Template matching, ORB features, SSIM, histogram
  - RANSAC geometric verification
  - Debug output system

- **[SOLD_LISTING_MATCHER.md](SOLD_LISTING_MATCHER.md)** - Sold listing matching system documentation
  - Playwright-based image matching
  - Requests-based headless matching
  - Performance optimizations

---

## 🛠️ API & Integration

### eBay API
- **[api_setup_guide.md](api_setup_guide.md)** - API configuration and setup guide
- **[EBAY_ENDPOINT_SETUP.md](EBAY_ENDPOINT_SETUP.md)** - eBay API endpoint configuration
- **[ebay_exemption_request.md](ebay_exemption_request.md)** - eBay API exemption documentation

---

## 🗂️ File Organization

### Main Directories
```
mandarake_scraper/
├── README.md                    # Main project documentation
├── CLAUDE.md                    # Development guide
├── gui_config.py                # Main GUI application (1473 lines)
├── mandarake_scraper.py         # Core scraper
├── gui/                         # Modular GUI components (20+ modules)
│   ├── *_tab.py                # Tab modules (Mandarake, eBay, Advanced, Alert)
│   ├── *_manager.py            # Manager classes
│   ├── alert_*.py              # Alert system modules
│   ├── workers.py              # Background workers
│   ├── utils.py                # Shared utilities
│   └── constants.py            # Shared constants
├── configs/                     # Configuration files
├── results/                     # Output CSV files
├── images/                      # Downloaded images
└── debug_comparison/            # Image comparison debug output
```

### Key Configuration Files
- `user_settings.json` - User preferences and settings
- `alerts.json` - Alert system data
- `schedules.json` - Scheduled task configurations
- `publishers.txt` - Publisher list for keyword extraction

---

## 🚀 Quick Start Guide

### For New Users
1. Read **[README.md](README.md)** for basic setup and usage
2. Check **[setup_guide.md](setup_guide.md)** for installation
3. Reference **[MANDARAKE_CODES.md](MANDARAKE_CODES.md)** for store/category codes
4. Review **[EBAY_IMAGE_COMPARISON_GUIDE.md](EBAY_IMAGE_COMPARISON_GUIDE.md)** for price comparison

### For Developers
1. Start with **[CLAUDE.md](CLAUDE.md)** for development context
2. Review **[GUI_MODULARIZATION_COMPLETE.md](GUI_MODULARIZATION_COMPLETE.md)** for architecture
3. Study the module structure in `gui/` directory
4. Follow the refactoring patterns and best practices

### For Feature Development
1. Review existing manager patterns in `gui/*_manager.py`
2. Follow separation of concerns principle
3. Use queue-based threading for background operations
4. Implement proper state management with flags

---

## 🔍 Core Features

### Main Workflows
1. **Scraping**: Configure → Search → Export results
2. **Price Comparison**: Load CSV → Compare with eBay → Send to alerts
3. **Review Workflow**: Review → Approve → Purchase → Track → Sold

### Key Technologies
- **Python 3.10+** - Main programming language
- **Tkinter** - GUI framework
- **Requests** - HTTP client with session management
- **BeautifulSoup4** - HTML parsing
- **OpenCV** - Image comparison and computer vision
- **Scrapy** - eBay scraping
- **Google APIs** - Sheets and Drive integration

### Configuration System
- **Auto-naming**: `{keyword}_{category}_{shop}.json`
- **Auto-save**: Debounced (50ms) config persistence
- **CSV/Images**: Same naming scheme as configs
- **Settings**: User preferences in `user_settings.json`

---

## 📝 Code Quality

### Recent Improvements (Phase 7)
- ✅ Fixed 6+ broken attribute references
- ✅ Removed 7 dead methods (~90 lines)
- ✅ Removed 9 unused imports
- ✅ Fixed duplicate protocol bindings
- ✅ 131 lines of dead code removed (8.2% reduction)

### Best Practices
1. **Thread Safety**: Use `self.after()` for UI updates from threads
2. **Queue Communication**: Workers use `run_queue` for status updates
3. **Manager Delegation**: Delegate to managers, not inline logic
4. **State Flags**: Use flags to prevent recursive updates

---

## 🧪 Testing

### Manual Testing Coverage
- ✅ GUI launches without errors
- ✅ All tabs load correctly
- ✅ Mandarake scraping works
- ✅ eBay search and comparison works
- ✅ CSV loading and filtering works
- ✅ Alert workflow functions
- ✅ Settings persistence works
- ✅ Window positions restore correctly

---

## 🔮 Future Enhancements

### Planned Improvements
1. Remove wrapper methods (call utils directly)
2. Extract complex methods (`run_now()`, `_poll_queue()`)
3. Add type hints for better IDE support
4. Create unit tests for manager classes
5. Replace print statements with proper logging
6. Consider event-driven architecture

---

## 📋 Documentation Standards

### File Naming Conventions
- `FEATURE_COMPLETE.md` - Feature documentation
- `COMPONENT_COMPLETE.md` - Completed component documentation
- `*_GUIDE.md` - User guides and tutorials

### Documentation Structure
Each markdown file should include:
- Clear title and overview
- Implementation details
- Usage examples
- Testing results (if applicable)
- Related documentation links

---

## 📊 Project Metrics

### Current State
- **Main GUI**: 1473 lines (down from 4000+)
- **Modules Created**: 20+
- **Code Reduction**: 63%
- **Documentation Files**: 12 core documents
- **Active Development**: Yes

### Module Count
- **Tab Modules**: 4 (Mandarake, eBay, Advanced, Alert)
- **Manager Modules**: 8+
- **Worker Modules**: 2
- **Utility Modules**: 3
- **Alert System**: 3 modules

---

## 🔗 Related Documentation

### External References
- [Python Tkinter Documentation](https://docs.python.org/3/library/tkinter.html)
- [OpenCV Python Tutorials](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)
- [eBay API Documentation](https://developer.ebay.com/)
- [Scrapy Documentation](https://docs.scrapy.org/)

---

**Maintainer**: Development Team
**Status**: Active
**Version**: 1.0 (Modularized)
