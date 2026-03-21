"""Songkick concert tracker — scrapes public pages or uses API if key available.

Songkick has metro area IDs for various cities.
Env var: SONGKICK_API_KEY (optional — falls back to scraping)
All events are concerts/music.
"""

from __future__ import annotations
import logging
import os
import re
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from ..models import AgeGroup, City, Event, EventType
from .base import BaseFetcher

log = logging.getLogger(__name__)

METRO_IDS = {
    City.BUCHAREST: 31841,
    City.TEL_AVIV: 29209,
    City.BARCELONA: 28714,
    City.NEW_YORK: 7644,
}

# Metro area URL slugs
METRO_SLUGS = {
    City.BUCHAREST: "romania-bucharest",
    City.TEL_AVIV: "israel-tel-aviv",
    City.BARCELONA: "spain-barcelona",
    City.NEW_YORK: "us/ny-metro-area",
}

API_BASE = "https://api.songkick.com/api/3.0"
WEB_BASE = "https://www.songkick.com"


def _parse_date(date_str: str) -> Optional[datetime]:
    """Parse Songkick date format YYYY-MM-DD."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None


def _scrape_date(date_text: str) -> Optional[datetime]:
    """Parse date from scraped HTML text like 'Sat, Mar 22, 2026'."""
    if not date_text:
        return None
    
    # Clean up text
    date_text = date_text.strip()
    
    # Pattern: "Mon, Mar 22, 2026" or "March 22, 2026"
    patterns = [
        r"[A-Za-z]{3},?\s*([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})",  # Mon, Mar 22, 2026
        r"([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})",  # March 22, 2026
    ]
    
    months = {
        "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
        "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
        "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
        "nov": 11, "november": 11, "dec": 12, "december": 12,
    }
    
    for pattern in patterns:
        match = re.search(pattern, date_text, re.I)
        if match:
            month_str = match.group(1).lower()
            day = int(match.group(2))
            year = int(match.group(3))
            month = months.get(month_str[:3])
            if month:
                try:
                    return datetime(year, month, day)
                except ValueError:
                    continue
    
    return None


class SongkickFetcher(BaseFetcher):
    """Fetches concert events from Songkick."""
    
    source_name = "songkick"
    supported_cities = list(METRO_IDS.keys())
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("SONGKICK_API_KEY", "")
    
    def fetch(
        self,
        city: City,
        start: datetime,
        end: datetime,
        event_types: Optional[list[EventType]] = None,
        limit: int = 50,
    ) -> list[Event]:
        if city not in METRO_IDS:
            return []
        
        # All Songkick events are concerts — check type filter
        if event_types and EventType.CONCERT not in event_types and EventType.JAZZ not in event_types:
            return []
        
        # Try API first if key available
        if self.api_key:
            events = self._fetch_api(city, start, end, limit)
            if events:
                return events
        
        # Fall back to scraping
        return self._fetch_scrape(city, start, end, limit)
    
    def _fetch_api(
        self,
        city: City,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[Event]:
        """Fetch via Songkick API (requires API key)."""
        metro_id = METRO_IDS[city]
        url = f"{API_BASE}/metro_areas/{metro_id}/calendar.json"
        
        params = {
            "apikey": self.api_key,
            "min_date": start.strftime("%Y-%m-%d"),
            "max_date": end.strftime("%Y-%m-%d"),
            "per_page": min(limit, 50),
        }
        
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            log.warning("Songkick API error: %s", exc)
            return []
        
        events: list[Event] = []
        results = data.get("resultsPage", {}).get("results", {}).get("event", [])
        
        for item in results:
            try:
                title = item.get("displayName", "")
                event_id = str(item.get("id", ""))
                event_url = item.get("uri", "")
                
                start_date = _parse_date(item.get("start", {}).get("date", ""))
                
                venue = item.get("venue", {})
                venue_name = venue.get("displayName", "")
                
                location = item.get("location", {})
                address = location.get("city", "")
                
                events.append(Event(
                    id=f"songkick_{event_id}",
                    source=self.source_name,
                    city=city,
                    title=title,
                    description="",
                    url=event_url,
                    image_url="",
                    event_types=[EventType.CONCERT],
                    age_groups=[AgeGroup.ADULTS],
                    start=start_date,
                    end=None,
                    venue_name=venue_name,
                    address=address,
                    is_free=False,
                    ticket_url=event_url,
                ))
                
                if len(events) >= limit:
                    break
                    
            except Exception as exc:
                log.debug("Songkick API parse error: %s", exc)
                continue
        
        return events
    
    def _fetch_scrape(
        self,
        city: City,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[Event]:
        """Scrape Songkick public pages."""
        slug = METRO_SLUGS.get(city)
        if not slug:
            return []
        
        metro_id = METRO_IDS[city]
        url = f"{WEB_BASE}/metro-areas/{metro_id}-{slug}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
        except Exception as exc:
            log.warning("Songkick scrape error: %s", exc)
            return []
        
        try:
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception as exc:
            log.warning("Songkick HTML parse error: %s", exc)
            return []
        
        events: list[Event] = []
        seen_urls = set()
        
        # Look for event listings - Songkick uses `event-listings-element` class
        event_items = soup.find_all("li", class_="event-listings-element")
        
        for item in event_items:
            try:
                # Find the datetime from <time> element
                time_elem = item.find("time")
                event_date = None
                if time_elem:
                    dt_attr = time_elem.get("datetime", "")
                    if dt_attr:
                        try:
                            # Handle formats like "2026-03-21" or "2026-03-21T21:00:00+0200"
                            if "T" in dt_attr:
                                # Normalise +HHMM → +HH:MM for fromisoformat
                                dt_attr_norm = re.sub(r"([+-])(\d{2})(\d{2})$", r"\1\2:\3", dt_attr)
                                event_date = datetime.fromisoformat(dt_attr_norm).replace(tzinfo=None)
                            else:
                                event_date = datetime.strptime(dt_attr, "%Y-%m-%d")
                        except ValueError:
                            pass
                
                # Fallback: try title attribute
                if not event_date:
                    title_attr = item.get("title", "")
                    event_date = _scrape_date(title_attr)
                
                # Filter by date range
                if event_date:
                    event_day = event_date.date()
                    start_day = start.date()
                    end_day = end.date()
                    if event_day < start_day or event_day > end_day:
                        continue
                
                # Find all concert links - there may be multiple, pick the one with text
                concert_links = item.find_all("a", href=re.compile(r"/concerts/|/festivals/"))
                if not concert_links:
                    continue
                
                # Find the link with actual text content (title)
                href = ""
                title = ""
                for cl in concert_links:
                    link_href = cl.get("href", "")
                    link_text = cl.get_text(strip=True)
                    if not href:
                        href = link_href  # Take first href
                    if link_text and len(link_text) > len(title):
                        title = link_text  # Take longest text
                
                if href in seen_urls:
                    continue
                seen_urls.add(href)
                
                if not title:
                    continue
                
                event_url = href if href.startswith("http") else f"{WEB_BASE}{href}"
                
                # Find venue link
                venue_link = item.find("a", href=re.compile(r"/venues/"))
                venue_name = venue_link.get_text(strip=True) if venue_link else ""
                
                # Extract ID from URL like /concerts/43076542-acid-arab-at-club-control
                id_match = re.search(r"/concerts/(\d+)", href)
                event_id = f"songkick_{id_match.group(1)}" if id_match else f"songkick_{hash(href) & 0xFFFFFFFF:08x}"
                
                events.append(Event(
                    id=event_id,
                    source=self.source_name,
                    city=city,
                    title=title[:200],
                    description="",
                    url=event_url,
                    image_url="",
                    event_types=[EventType.CONCERT],
                    age_groups=[AgeGroup.ADULTS],
                    start=event_date,
                    end=None,
                    venue_name=venue_name,
                    address="",
                    is_free=False,
                    ticket_url=event_url,
                ))
                
                if len(events) >= limit:
                    break
                    
            except Exception as exc:
                log.debug("Songkick scrape parse error: %s", exc)
                continue
        
        log.info("Songkick → %s: parsed %d events", city.value, len(events))
        return events
