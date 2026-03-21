"""Resident Advisor (RA) — electronic music / nightlife events.

Uses RA's public GraphQL API (no key required).
All events are nightlife, adults only.
"""

from __future__ import annotations
import logging
from datetime import datetime
from typing import Optional

import requests

from ..models import AgeGroup, City, Event, EventType
from .base import BaseFetcher

log = logging.getLogger(__name__)

RA_GRAPHQL_URL = "https://ra.co/graphql"

# RA area IDs (discovered via RA GraphQL introspection + URL patterns, verified 2026-03-21)
# To verify: check https://ra.co/events/{country}/{city} resolves
# Note: Area IDs can be discovered via RA's GraphQL areaSearch query
# If 0 results returned, log a warning — ID may have changed
AREA_IDS = {
    City.BUCHAREST: 381,    # Romania/Bucharest (verified via https://ra.co/events/ro/bucharest)
    City.BARCELONA: 20,     # Spain/Barcelona (verified via https://ra.co/events/es/barcelona)
    City.NEW_YORK: 8,       # USA/New York (verified via https://ra.co/events/us/newyork)
    City.TEL_AVIV: 413,     # Israel/Tel Aviv (verified via https://ra.co/events/il/telaviv)
}

# GraphQL query for event listings
# We filter by listingDate >= today to get events that were recently listed
# (which generally means upcoming events). Then filter by event date in code.
EVENT_QUERY = """
query EventListings($areaId: Int!, $listingDateStart: DateTime!, $limit: Int!) {
  eventListings(
    filters: {
      areas: {eq: $areaId}
      listingDate: {gte: $listingDateStart}
    }
    pageSize: $limit
  ) {
    data {
      id
      listingDate
      event {
        title
        date
        startTime
        contentUrl
        venue {
          name
          address
        }
        images {
          filename
        }
      }
    }
  }
}
"""


def _parse_ra_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse RA datetime format like '2026-03-06T22:00:00.000'."""
    if not dt_str:
        return None
    try:
        # Handle the .000 milliseconds
        dt_str = dt_str.replace(".000", "")
        dt = datetime.fromisoformat(dt_str)
        return dt.replace(tzinfo=None)  # strip tz for consistent naive datetimes
    except ValueError:
        try:
            # Try with just the date
            return datetime.fromisoformat(dt_str[:10])
        except ValueError:
            return None


class RAFetcher(BaseFetcher):
    """Fetches electronic music / nightlife events from Resident Advisor."""
    
    source_name = "ra"
    supported_cities = list(AREA_IDS.keys())
    
    def fetch(
        self,
        city: City,
        start: datetime,
        end: datetime,
        event_types: Optional[list[EventType]] = None,
        limit: int = 50,
    ) -> list[Event]:
        if city not in AREA_IDS:
            return []
        
        # RA is for nightlife — check type filter
        if event_types and EventType.NIGHTLIFE not in event_types and EventType.CONCERT not in event_types:
            return []
        
        area_id = AREA_IDS[city]
        
        # Format dates for GraphQL
        # We use listingDate to get recently listed events, then filter by event date in code
        # Use a start date 30 days ago to catch events listed recently
        from datetime import timedelta
        listing_start = (start - timedelta(days=30)).strftime("%Y-%m-%d")
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://ra.co/",
        }
        
        payload = {
            "query": EVENT_QUERY,
            "variables": {
                "areaId": area_id,
                "listingDateStart": listing_start,
                "limit": min(limit * 3, 200),  # Fetch more to allow for date filtering
            },
        }
        
        try:
            resp = requests.post(
                RA_GRAPHQL_URL,
                json=payload,
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            log.warning("RA GraphQL error: %s", exc)
            return []
        
        # Check for GraphQL errors
        if "errors" in data:
            log.warning("RA GraphQL errors: %s", data["errors"])
            return []
        
        events: list[Event] = []
        listings = data.get("data", {}).get("eventListings", {}).get("data", [])
        
        # Warn if no results — area ID may be wrong
        if not listings:
            log.warning("RA → %s: 0 results with area_id=%d. Area ID may have changed.", city.value, area_id)
        
        for listing in listings:
            try:
                listing_id = listing.get("id", "")
                event_data = listing.get("event", {})
                
                if not event_data:
                    continue
                
                title = event_data.get("title", "")
                if not title:
                    continue
                
                # Parse dates
                event_date = _parse_ra_datetime(event_data.get("date"))
                start_time = _parse_ra_datetime(event_data.get("startTime"))
                
                # Use startTime if available, otherwise event date
                event_start = start_time or event_date
                
                # Filter by actual event date
                if event_date:
                    if event_date < start or event_date > end:
                        continue
                
                # Venue info
                venue_data = event_data.get("venue") or {}
                venue_name = venue_data.get("name", "")
                address = venue_data.get("address", "") or ""
                
                # URL
                content_url = event_data.get("contentUrl", "")
                event_url = f"https://ra.co{content_url}" if content_url else ""
                
                # Image
                images = event_data.get("images") or []
                image_url = images[0].get("filename", "") if images else ""
                
                events.append(Event(
                    id=f"ra_{listing_id}",
                    source=self.source_name,
                    city=city,
                    title=title[:200],
                    description="",
                    url=event_url,
                    image_url=image_url,
                    event_types=[EventType.NIGHTLIFE],
                    age_groups=[AgeGroup.ADULTS],
                    start=event_start,
                    end=None,
                    venue_name=venue_name,
                    address=address,
                    is_free=False,
                    ticket_url=event_url,
                ))
                
                if len(events) >= limit:
                    break
                    
            except Exception as exc:
                log.debug("RA parse event error: %s", exc)
                continue
        
        log.info("RA → %s: fetched %d events", city.value, len(events))
        return events
