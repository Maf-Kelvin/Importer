# app/services/scraper_service.py
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from app.core.config import settings, PRICING_SOURCES
from app.models.item import Item
from app.core.database import SessionLocal
import time
import random


class ScraperService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': settings.SCRAPING_USER_AGENT
        })
    
    def scrape_prices(self, item_id: int, source: str) -> List[Dict[str, Any]]:
        """Scrape prices for an item from a specific source."""
        if not settings.SCRAPING_ENABLED:
            return []
        
        db = SessionLocal()
        try:
            item = db.query(Item).filter(Item.id == item_id).first()
            if not item:
                return []
            
            scraper_method = getattr(self, f'_scrape_{source}', None)
            if scraper_method:
                return scraper_method(item)
            
        except Exception as e:
            print(f"Error scraping {source}: {e}")
        finally:
            db.close()
        
        return []
    
    def _scrape_jiji(self, item: Item) -> List[Dict[str, Any]]:
        """Scrape prices from Jiji.ng."""
        try:
            # Build search query
            search_term = f"{item.name} {item.category.value}".replace(" ", "+")
            url = f"https://jiji.ng/search?query={search_term}"
            
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            prices = []
            # This is a simplified example - real scraping would need more robust selectors
            price_elements = soup.find_all('div', class_='price')[:5]  # Limit to 5 results
            
            for element in price_elements:
                price_text = element.get_text().strip()
                # Extract numerical price (simplified)
                price_value = self._extract_price(price_text)
                if price_value:
                    prices.append({
                        'price': price_value,
                        'currency': 'NGN',
                        'url': url,
                        'confidence': 0.7,
                        'raw_data': price_text
                    })
            
            return prices
            
        except Exception as e:
            print(f"Error scraping Jiji: {e}")
            return []
    
    def _scrape_ebay(self, item: Item) -> List[Dict[str, Any]]:
        """Scrape prices from eBay."""
        try:
            # Build search query
            search_term = f"{item.name} {item.category.value}".replace(" ", "+")
            url = f"https://www.ebay.com/sch/i.html?_nkw={search_term}"
            
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            prices = []
            # Simplified eBay scraping
            price_elements = soup.find_all('span', class_='s-item__price')[:5]
            
            for element in price_elements:
                price_text = element.get_text().strip()
                price_value = self._extract_price(price_text)
                if price_value:
                    prices.append({
                        'price': price_value,
                        'currency': 'USD',
                        'url': url,
                        'confidence': 0.8,
                        'raw_data': price_text
                    })
            
            return prices
            
        except Exception as e:
            print(f"Error scraping eBay: {e}")
            return []
    
    def _extract_price(self, price_text: str) -> Optional[float]:
        """Extract numerical price from text."""
        import re
        
        # Remove currency symbols and extract numbers
        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
        if price_match:
            try:
                return float(price_match.group())
            except ValueError:
                pass
        
        return None
    
    def _add_delay(self):
        """Add random delay to avoid being blocked."""
        time.sleep(random.uniform(1, 3))