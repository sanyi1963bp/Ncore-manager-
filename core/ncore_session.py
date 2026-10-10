"""
Scraper modul
=============
nCore e-book scraping requests + BeautifulSoup segítségével
"""

import re
import os
import time
import urllib.request
from typing import Optional, Dict, List, Callable, Generator
from bs4 import BeautifulSoup
import requests

from config import load_config, get, set as config_set
from database import save_book, get_latest_date, get_oldest_date, book_exists, count_books as db_count_books

# nCore URL-ek
BASE_URL = "https://ncore.pro"
LOGIN_URL = f"{BASE_URL}/login.php"
EBOOK_URL = f"{BASE_URL}/torrents.php?tipus=ebook_hun"


class NCoreSession:
    """nCore session kezelő."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
        })
        self.logged_in = False
    
    def login(self, username: str, password: str) -> bool:
        """Bejelentkezés az nCore-ra."""
        try:
            login_data = {
                "nev": username,
                "pass": password,
                "set_lang": "hu",
                "submitted": "1",
            }
            
            resp = self.session.post(LOGIN_URL, data=login_data, timeout=15, allow_redirects=True)
            
            if "login.php" not in resp.url:
                self.logged_in = True
                return True
            return False
            
        except requests.RequestException:
            return False
    
    def get(self, url: str) -> Optional[requests.Response]:
        """GET kérés a session-nel."""
        if not self.logged_in:
            return None
        try:
            return self.session.get(url, timeout=15)
        except requests.RequestException:
            return None


class NCoreSession:
    """nCore session kezelő."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
        })
        self.logged_in = False
    
    def login(self, username: str, password: str) -> bool:
        """Bejelentkezés az nCore-ra."""
        try:
            login_data = {
                "nev": username,
                "pass": password,
                "set_lang": "hu",
                "submitted": "1",
            }
            
            resp = self.session.post(LOGIN_URL, data=login_data, timeout=15, allow_redirects=True)
            
            if "login.php" not in resp.url:
                self.logged_in = True
                return True
            return False
            
        except requests.RequestException:
            return False
    
    def get(self, url: str) -> Optional[requests.Response]:
        """GET kérés a session-nel."""
        if not self.logged_in:
            return None
        try:
            return self.session.get(url, timeout=15)
        except requests.RequestException:
            return None


