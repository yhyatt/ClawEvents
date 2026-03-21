"""iaBilet.ro scraper — Romanian ticketing platform.

Scrapes Bucharest events from iaBilet's city page.
No API available — uses HTML parsing.
"""

from __future__ import annotations
import logging
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ..models import AgeGroup, City, Event, EventType
from .base import BaseFetcher

log = logging.getLogger(__name__)

BASE_URL = "https://www.iabilet.ro"

CITY_URLS = {
    City.BUCHAREST: "https://www.iabilet.ro/bilete-in-bucuresti/",
}

# Romanian month names → month number
_RO_MONTHS = {
    "ian": 1, "ianuarie": 1,
    "feb": 2, "februarie": 2,
    "mar": 3, "martie": 3,
    "apr": 4, "aprilie": 4,
    "mai": 5,
    "iun": 6, "iunie": 6,
    "iul": 7, "iulie": 7,
    "aug": 8, "august": 8,
    "sep": 9, "septembrie": 9,
    "oct": 10, "octombrie": 10,
    "nov": 11, "noiembrie": 11,
    "dec": 12, "decembrie": 12,
}

_TYPE_KEYWORDS: dict[EventType, list[str]] = {
    EventType.JAZZ:      ["jazz"],
    EventType.CONCERT:   ["concert", "live", "muzica", "rock", "pop", "hip-hop", "electronic"],
    EventType.THEATRE:   ["teatru", "theatre", "theater", "spectacol", "piesa"],
    EventType.COMEDY:    ["comedy", "stand-up", "stand up", "comedie", "ras"],
    EventType.ART:       ["expozitie", "exhibition", "arta", "galerie", "muzeu"],
    EventType.FESTIVAL:  ["festival"],
    EventType.FAMILY:    ["copii", "familie", "kids", "family", "pentru copii", "interactiv"],
    EventType.CINEMA:    ["film", "cinema", "proiectie"],
    EventType.NIGHTLIFE: ["club", "party", "dj"],
}


def _classify_types(title: str, desc: str = "") -> list[EventType]:
    """Classify event types based on keywords."""
    text = (title + " " + desc).lower()
    found = [t for t, kws in _TYPE_KEYWORDS.items() if any(k in text for k in kws)]
    return found or [EventType.OTHER]


def _classify_age(title: str, desc: str = "") -> list[AgeGroup]:
    """Classify age group based on keywords."""
    text = (title + " " + desc).lower()
    if any(k in text for k in ["copii", "familie", "kids", "family", "interactiv pentru copii"]):
        return [AgeGroup.FAMILY]
    if any(k in text for k in ["18+", "adult", "club", "party", "nightlife"]):
        return [AgeGroup.ADULTS]
    return [AgeGroup.FAMILY]  # Default to family-friendly


def _parse_ro_date(date_str: str, year: Optional[int] = None) -> Optional[datetime]:
    """Parse Romanian date format like '21 mar' or '5 apr' or '31 oct '25'."""
    if not date_str:
        return None
    
    date_str = date_str.lower().strip()
    
    # Try to extract day, month, and optional year
    # Pattern: "21 mar" or "31 oct '25" or "5 apr"
    match = re.match(r"(\d{1,2})\s+([a-zăâîșț]+)(?:\s+['\"]?(\d{2,4}))?", date_str)
    if not match:
        return None
    
    day = int(match.group(1))
    month_str = match.group(2)
    year_str = match.group(3)
    
    month = _RO_MONTHS.get(month_str)
    if not month:
        return None
    
    if year_str:
        y = int(year_str)
        if y < 100:
            y += 2000
        year = y
    elif year is None:
        year = datetime.now().year
        # If month is before current month, assume next year
        if month < datetime.now().month:
            year += 1
    
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


class IaBiletFetcher(BaseFetcher):
    """Fetches events from iaBilet.ro by scraping HTML."""
    
    source_name = "iabilet"
    supported_cities = [City.BUCHAREST]
    
    def fetch(
        self,
        city: City,
        start: datetime,
        end: datetime,
        event_types: Optional[list[EventType]] = None,
        limit: int = 50,
    ) -> list[Event]:
        if city not in CITY_URLS:
            return []
        
        url = CITY_URLS[city]
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5,ro;q=0.3",
        }
        
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
        except Exception as exc:
            log.warning("iaBilet fetch error: %s", exc)
            return []
        
        try:
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception as exc:
            log.warning("iaBilet HTML parse error: %s", exc)
            return []
        
        events: list[Event] = []
        
        # iaBilet structure: Event URLs follow pattern /bilete-EVENTNAME-ID/
        # where ID is 5+ digits. We filter out venue links (-venue-) and city links (in-)
        event_pattern = re.compile(r"^/bilete-(?!in-)(?!.*-venue-)[^/]+-(\d{5,})/")
        event_links = soup.find_all("a", href=event_pattern)
        
        # Group links by URL to find the best title for each event
        from collections import defaultdict
        by_href: dict[str, list] = defaultdict(list)
        for link in event_links:
            href = link.get("href", "").split("?")[0]  # Remove query params
            by_href[href].append(link)
        
        for href, links in by_href.items():
            try:
                # Find the best title from all links to this event
                best_title = ""
                for link in links:
                    text = link.get_text(strip=True)
                    # Skip utility text
                    if text and text.lower() not in ["ia bilet", "vezi mai mult", "bilete", "cumpara", ""]:
                        if len(text) > len(best_title):
                            best_title = text
                
                if not best_title or len(best_title) < 3:
                    continue
                
                title = best_title
                event_url = urljoin(BASE_URL, href)
                
                # Try to find date info nearby
                # Look in parent/sibling elements for date patterns
                date_text = ""
                for link in links:
                    parent = link.parent
                    for _ in range(5):  # Check up to 5 parent levels
                        if parent:
                            text = parent.get_text(" ", strip=True)
                            # Look for date patterns like "21 mar" or "5 apr '25"
                            date_match = re.search(
                                r"(\d{1,2})\s+(ian|feb|mar|apr|mai|iun|iul|aug|sep|oct|nov|dec)(?:\s+['\"]?(\d{2,4}))?",
                                text, re.I
                            )
                            if date_match:
                                date_text = date_match.group(0)
                                break
                            parent = parent.parent
                    if date_text:
                        break
                
                event_date = _parse_ro_date(date_text) if date_text else None
                
                # Filter by date range (if we have a date)
                # Compare dates only, not times, since events may be parsed as midnight
                if event_date:
                    event_day = event_date.date()
                    start_day = start.date()
                    end_day = end.date()
                    if event_day < start_day or event_day > end_day:
                        continue
                
                types = _classify_types(title)
                
                # Filter by event types if specified
                if event_types and not any(t in types for t in event_types):
                    continue
                
                age_groups = _classify_age(title)
                
                # Extract event ID from URL
                id_match = re.search(r"-(\d{5,})/", href)
                event_id = f"iabilet_{id_match.group(1)}" if id_match else f"iabilet_{hash(href) & 0xFFFFFFFF:08x}"
                
                events.append(Event(
                    id=event_id,
                    source=self.source_name,
                    city=city,
                    title=title[:200],
                    description="",
                    url=event_url,
                    image_url="",
                    event_types=types,
                    age_groups=age_groups,
                    start=event_date,
                    end=None,
                    venue_name="",
                    address="",
                    is_free=False,
                    currency="RON",
                    ticket_url=event_url,
                ))
                
                if len(events) >= limit:
                    break
                    
            except Exception as exc:
                log.debug("iaBilet parse event error: %s", exc)
                continue
        
        log.info("iaBilet → %s: parsed %d events", city.value, len(events))
        return events
