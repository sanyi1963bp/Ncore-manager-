"""Compatibility facade for the refactored scraper modules."""
from core.ncore_session import NCoreSession, BASE_URL, LOGIN_URL, EBOOK_URL
from core.scraper import Scraper

__all__ = ["NCoreSession", "Scraper", "BASE_URL", "LOGIN_URL", "EBOOK_URL"]
