"""
Yahoo Auction Browser - GUI tool for browsing auctions and sellers
"""
import sys
import requests
import json
import re
import webbrowser
from pathlib import Path
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLineEdit, QPushButton, QLabel,
                             QTextEdit, QListWidget, QSplitter, QMessageBox,
                             QListWidgetItem, QTextBrowser)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QFont

class FetchThread(QThread):
    """Background thread for fetching data"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url, fetch_type='item'):
        super().__init__()
        self.url = url
        self.fetch_type = fetch_type

    def run(self):
        try:
            if self.fetch_type == 'item':
                data = self.fetch_item_data()
            elif self.fetch_type == 'seller':
                data = self.fetch_seller_items()
            else:
                data = {}
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))

    def fetch_item_data(self):
        """Fetch individual auction data"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        }

        response = requests.get(self.url, headers=headers, timeout=30)
        response.encoding = 'utf-8'

        soup = BeautifulSoup(response.text, 'html.parser')
        next_data_script = soup.find('script', {'id': '__NEXT_DATA__', 'type': 'application/json'})

        if next_data_script:
            next_data = json.loads(next_data_script.string)
            item_data = next_data.get('props', {}).get('pageProps', {}).get('initialState', {}).get('item', {}).get('detail', {}).get('item', {})
            return {
                'type': 'item',
                'data': item_data,
                'url': self.url
            }
        return {}

    def fetch_seller_items(self):
        """Fetch seller's auction listings"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        }

        response = requests.get(self.url, headers=headers, timeout=30)
        response.encoding = 'utf-8'

        soup = BeautifulSoup(response.text, 'html.parser')
        items = []

        # Parse HTML for product items
        product_items = soup.find_all('li', class_=lambda x: x and 'Product' in x if x else False)

        for product in product_items:
            item = {}

            # Extract auction ID
            link = product.find('a', href=re.compile(r'/auction/'))
            if link:
                href = link.get('href', '')
                id_match = re.search(r'/auction/([a-z0-9]+)', href)
                if id_match:
                    item['AuctionID'] = id_match.group(1)

            # Extract title
            title_elem = product.find(['h3', 'div'], class_=lambda x: x and ('title' in x.lower() or 'Title' in x) if x else False)
            if title_elem:
                item['Title'] = title_elem.get_text(strip=True)

            # Extract price
            price_elem = product.find(['div', 'span'], class_=lambda x: x and ('price' in x.lower() or 'Price' in x) if x else False)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r'[\d,]+', price_text.replace(',', ''))
                if price_match:
                    item['Price'] = int(price_match.group().replace(',', ''))

            # Extract image
            img = product.find('img')
            if img:
                item['Image'] = img.get('src', '')

            if item.get('AuctionID'):
                items.append(item)

        return {
            'type': 'seller',
            'items': items,
            'url': self.url
        }


class YahooAuctionBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_item = None
        self.current_seller_url = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Yahoo Auction Browser')
        self.setGeometry(100, 100, 1200, 800)

        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # URL input section
        url_layout = QHBoxLayout()
        url_label = QLabel('Auction URL:')
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('https://auctions.yahoo.co.jp/jp/auction/...')
        self.url_input.returnPressed.connect(self.load_auction)

        self.load_btn = QPushButton('Load Auction')
        self.load_btn.clicked.connect(self.load_auction)

        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.load_btn)
        layout.addLayout(url_layout)

        # Splitter for main content
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - Item details
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Item info - use QTextBrowser to render HTML with images
        self.item_info = QTextBrowser()
        self.item_info.setOpenExternalLinks(True)
        left_layout.addWidget(self.item_info)

        # Buttons
        button_layout = QHBoxLayout()
        self.view_browser_btn = QPushButton('View in Browser')
        self.view_browser_btn.clicked.connect(self.view_in_browser)
        self.view_browser_btn.setEnabled(False)

        self.view_seller_btn = QPushButton('View Seller Items')
        self.view_seller_btn.clicked.connect(self.view_seller_items)
        self.view_seller_btn.setEnabled(False)

        button_layout.addWidget(self.view_browser_btn)
        button_layout.addWidget(self.view_seller_btn)
        left_layout.addLayout(button_layout)

        # Right panel - Seller items list
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.seller_label = QLabel('Seller Items')
        self.seller_label.setFont(QFont('Arial', 10, QFont.Bold))
        right_layout.addWidget(self.seller_label)

        self.seller_list = QListWidget()
        self.seller_list.itemDoubleClicked.connect(self.load_seller_item)
        right_layout.addWidget(self.seller_list)

        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 600])

        layout.addWidget(splitter)

        # Status bar
        self.statusBar().showMessage('Ready')

    def load_auction(self):
        url = self.url_input.text().strip()
        if not url:
            return

        # Validate URL
        if 'auctions.yahoo.co.jp' not in url or '/auction/' not in url:
            QMessageBox.warning(self, 'Invalid URL', 'Please enter a valid Yahoo Auction item URL')
            return

        self.statusBar().showMessage('Loading auction...')
        self.load_btn.setEnabled(False)

        # Fetch data in background
        self.fetch_thread = FetchThread(url, 'item')
        self.fetch_thread.finished.connect(self.display_item)
        self.fetch_thread.error.connect(self.handle_error)
        self.fetch_thread.start()

    def display_item(self, result):
        if result.get('type') == 'item':
            item_data = result.get('data', {})
            self.current_item = item_data

            # Generate full HTML view
            auction_id = item_data.get('auctionId', '')
            auction_url = f"https://auctions.yahoo.co.jp/jp/auction/{auction_id}"
            html = self.render_item_html_inline(item_data, auction_url)

            self.item_info.setHtml(html)

            # Store seller URL
            seller = item_data.get('seller', {})
            seller_id = seller.get('aucUserId', '')
            seller_name = seller.get('displayName', 'Unknown')

            if seller_id:
                self.current_seller_url = f"https://auctions.yahoo.co.jp/seller/{seller_id}"
                self.seller_label.setText(f"Seller Items - {seller_name}")
                self.view_seller_btn.setEnabled(True)

            self.view_browser_btn.setEnabled(True)

            title = item_data.get('title', 'No Title')
            self.statusBar().showMessage(f'Loaded: {title[:50]}...')

        self.load_btn.setEnabled(True)

    def view_in_browser(self):
        if not self.current_item:
            return

        # Render HTML and open
        auction_id = self.current_item.get('auctionId', '')
        auction_url = f"https://auctions.yahoo.co.jp/jp/auction/{auction_id}"

        html = self.render_item_html(self.current_item, auction_url)

        output_file = Path("yahoo_auction_view.html")
        output_file.write_text(html, encoding='utf-8')

        webbrowser.open(output_file.absolute().as_uri())
        self.statusBar().showMessage('Opened in browser')

    def view_seller_items(self):
        if not self.current_seller_url:
            return

        self.statusBar().showMessage('Loading seller items...')
        self.view_seller_btn.setEnabled(False)

        # Fetch seller items
        self.seller_thread = FetchThread(self.current_seller_url, 'seller')
        self.seller_thread.finished.connect(self.display_seller_items)
        self.seller_thread.error.connect(self.handle_error)
        self.seller_thread.start()

    def display_seller_items(self, result):
        if result.get('type') == 'seller':
            items = result.get('items', [])

            self.seller_list.clear()

            for item in items:
                title = item.get('Title', 'No Title')
                price = item.get('Price', 0)
                auction_id = item.get('AuctionID', '')

                item_widget = QListWidgetItem(f"{title}\n¥{price:,}")
                item_widget.setData(Qt.UserRole, auction_id)
                self.seller_list.addItem(item_widget)

            self.statusBar().showMessage(f'Found {len(items)} items from seller')

        self.view_seller_btn.setEnabled(True)

    def load_seller_item(self, item):
        auction_id = item.data(Qt.UserRole)
        url = f"https://auctions.yahoo.co.jp/jp/auction/{auction_id}"
        self.url_input.setText(url)
        self.load_auction()

    def render_item_html_inline(self, item_data, auction_url):
        """Render item as inline HTML for QTextBrowser"""
        title = item_data.get('title', 'No Title')
        price = item_data.get('price', 0)
        bids = item_data.get('bids', 0)
        condition = item_data.get('conditionName', 'N/A')
        end_time = item_data.get('formattedEndTime', 'N/A')
        description_html = item_data.get('descriptionHtml', '')

        seller = item_data.get('seller', {})
        seller_name = seller.get('displayName', 'Unknown')
        seller_rating = seller.get('rating', {}).get('goodRating', 'N/A')
        seller_location = seller.get('location', {}).get('prefecture', 'N/A')

        images = item_data.get('img', [])
        category = item_data.get('category', {})
        category_path = category.get('path', [])
        category_str = ' > '.join([c['name'] for c in category_path])

        html = f"""
<div style="font-family: Arial, sans-serif; padding: 10px;">
    <h2 style="color: #333; margin-bottom: 5px;">{title}</h2>
    <p style="color: #666; font-size: 12px; margin-bottom: 15px;">{category_str}</p>

    <div style="background: #fff3cd; border: 2px solid #ffc107; padding: 15px; margin-bottom: 20px;">
        <div style="font-size: 14px; margin-bottom: 5px;">Current Price</div>
        <div style="font-size: 32px; font-weight: bold; color: #ff0033;">¥{price:,}</div>
        <div style="margin-top: 10px;">Bids: {bids}</div>
    </div>

    <div style="margin-bottom: 15px;">
        <img src="{images[0]['image'] if images else ''}" style="max-width: 100%; border: 1px solid #e0e0e0;">
    </div>

    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
        <tr style="border-bottom: 1px solid #e0e0e0;">
            <td style="padding: 10px 0; font-weight: bold; width: 120px;">Condition:</td>
            <td style="padding: 10px 0;">{condition}</td>
        </tr>
        <tr style="border-bottom: 1px solid #e0e0e0;">
            <td style="padding: 10px 0; font-weight: bold;">Auction Ends:</td>
            <td style="padding: 10px 0;">{end_time}</td>
        </tr>
        <tr style="border-bottom: 1px solid #e0e0e0;">
            <td style="padding: 10px 0; font-weight: bold;">Seller:</td>
            <td style="padding: 10px 0;">{seller_name}<br>Rating: {seller_rating}<br>Location: {seller_location}</td>
        </tr>
    </table>

    <div style="background: #f8f9fa; padding: 15px; margin-bottom: 20px;">
        <h3 style="margin-bottom: 10px;">Description</h3>
        {description_html[:500] if description_html else 'No description'}
    </div>

    <p style="margin-top: 20px;">
        <a href="{auction_url}" style="display: inline-block; padding: 10px 20px; background: #ff0033; color: white; text-decoration: none; border-radius: 4px;">View Original Auction</a>
    </p>
</div>
"""
        return html

    def render_item_html(self, item_data, auction_url):
        """Render item as HTML"""
        title = item_data.get('title', 'No Title')
        price = item_data.get('price', 0)
        bids = item_data.get('bids', 0)
        condition = item_data.get('conditionName', 'N/A')
        end_time = item_data.get('formattedEndTime', 'N/A')
        description_html = item_data.get('descriptionHtml', '')

        seller = item_data.get('seller', {})
        seller_name = seller.get('displayName', 'Unknown')
        seller_rating = seller.get('rating', {}).get('goodRating', 'N/A')
        seller_location = seller.get('location', {}).get('prefecture', 'N/A')

        images = item_data.get('img', [])

        category = item_data.get('category', {})
        category_path = category.get('path', [])
        category_str = ' > '.join([c['name'] for c in category_path])

        html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .banner {{ background: #ff0033; color: white; padding: 10px; text-align: center; font-weight: bold; }}
        .container {{ max-width: 1200px; margin: 20px auto; background: white; padding: 20px; }}
        .title {{ font-size: 24px; font-weight: bold; margin-bottom: 10px; }}
        .category {{ color: #666; font-size: 14px; margin-bottom: 20px; }}
        .content {{ display: flex; gap: 20px; }}
        .images {{ flex: 1; }}
        .main-image {{ width: 100%; border: 1px solid #e0e0e0; margin-bottom: 10px; }}
        .thumbnails {{ display: flex; gap: 5px; flex-wrap: wrap; }}
        .thumbnail {{ width: 80px; height: 80px; object-fit: cover; border: 1px solid #e0e0e0; cursor: pointer; }}
        .info {{ flex: 1; max-width: 400px; }}
        .price-box {{ background: #fff3cd; border: 2px solid #ffc107; padding: 15px; margin-bottom: 20px; }}
        .price {{ font-size: 32px; font-weight: bold; color: #ff0033; }}
        .info-item {{ padding: 10px 0; border-bottom: 1px solid #e0e0e0; }}
        .description {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #e0e0e0; }}
    </style>
</head>
<body>
    <div class="banner">Yahoo Auction Browser - Rendered View</div>
    <div class="container">
        <div class="title">{title}</div>
        <div class="category">{category_str}</div>
        <div class="content">
            <div class="images">
                <img src="{images[0]['image'] if images else ''}" class="main-image" id="mainImage">
                <div class="thumbnails">
"""

        for img in images:
            html += f'                    <img src="{img["thumbnail"]}" class="thumbnail" onclick="document.getElementById(\'mainImage\').src=\'{img["image"]}\'">\n'

        html += f"""                </div>
            </div>
            <div class="info">
                <div class="price-box">
                    <div>Current Price</div>
                    <div class="price">¥{price:,}</div>
                    <div style="margin-top: 10px;">Bids: {bids}</div>
                </div>
                <div class="info-item"><b>Condition:</b> {condition}</div>
                <div class="info-item"><b>Auction Ends:</b> {end_time}</div>
                <div class="info-item"><b>Seller:</b> {seller_name}<br>Rating: {seller_rating}<br>Location: {seller_location}</div>
                <div style="margin-top: 20px;">
                    <a href="{auction_url}" target="_blank" style="display: inline-block; padding: 12px 24px; background: #ff0033; color: white; text-decoration: none; border-radius: 4px;">View Original</a>
                </div>
            </div>
        </div>
        <div class="description">
            <h3>Description</h3>
            {description_html}
        </div>
    </div>
</body>
</html>
"""
        return html

    def handle_error(self, error_msg):
        QMessageBox.critical(self, 'Error', f'Failed to load data:\n{error_msg}')
        self.statusBar().showMessage('Error occurred')
        self.load_btn.setEnabled(True)
        self.view_seller_btn.setEnabled(True)


def main():
    app = QApplication(sys.argv)
    browser = YahooAuctionBrowser()
    browser.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
