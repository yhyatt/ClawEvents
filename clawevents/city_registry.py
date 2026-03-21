"""
City Registry — Declarative city configuration for ClawEvents.
==============================================================
Adding a new city is a data change, not a code change.

Usage:
    from .city_registry import CITIES, get_city, list_cities, cities_for_country

    # Look up by slug or alias
    cfg = get_city("tlv")  # → CityConfig for Tel Aviv
    cfg = get_city("barcelona")  # → CityConfig for Barcelona

    # List all registered cities
    all_slugs = list_cities()  # → ["tel-aviv", "barcelona", ...]

    # Get cities by country
    israel_cities = cities_for_country("IL")  # → [CityConfig, ...]
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class CityConfig:
    """Configuration for a single city."""

    # Identity
    name: str                       # canonical display name
    slug: str                       # URL-safe, used as dict key
    aliases: list[str]              # CLI aliases (e.g. ["tlv", "tel-aviv"])
    country: str                    # ISO 2-letter
    timezone: str                   # IANA tz string

    # Events
    event_fetchers: list[str]       # ordered list of fetcher names for ClawEvents

    # Reservations
    reservation_platforms: list[str]  # ordered list of platform names

    # Recommendation sources
    michelin_slug: str | None       # Michelin Algolia city_slug, None if not indexed
    timeout_path: str | None        # path suffix for timeout.com, None if not available
    cnt_paths: list[str]            # Condé Nast Traveler paths

    # Curated restaurant list
    curated_list_file: str | None   # filename in reservation/curated/ dir, None if none

    # Flags
    michelin_indexed: bool          # False = Romania, Israel, etc.
    notes: str = ""                 # human-readable notes


# ══════════════════════════════════════════════════════════════════════════════
# City Definitions
# ══════════════════════════════════════════════════════════════════════════════

CITIES: dict[str, CityConfig] = {
    "tel-aviv": CityConfig(
        name="Tel Aviv",
        slug="tel-aviv",
        aliases=["tlv", "tel-aviv", "telaviv", "tel aviv"],
        country="IL",
        timezone="Asia/Jerusalem",
        event_fetchers=["tlv_municipality", "eventbrite", "lev_cinema", "timeout_il"],
        reservation_platforms=["ontopo", "tabit"],
        michelin_slug=None,
        michelin_indexed=False,
        timeout_path="israel/restaurants",
        cnt_paths=[],
        curated_list_file="tel_aviv.json",
    ),
    "barcelona": CityConfig(
        name="Barcelona",
        slug="barcelona",
        aliases=["barcelona", "bcn"],
        country="ES",
        timezone="Europe/Madrid",
        event_fetchers=["ticketmaster", "eventbrite", "fever", "xceed"],
        reservation_platforms=["thefork"],
        michelin_slug="barcelona",
        michelin_indexed=True,
        timeout_path="barcelona/en/restaurants/best-restaurants-in-barcelona",
        cnt_paths=["/gallery/best-restaurants-in-barcelona"],
        curated_list_file="barcelona.json",
    ),
    "new-york": CityConfig(
        name="New York",
        slug="new-york",
        aliases=["nyc", "new-york", "newyork", "new york"],
        country="US",
        timezone="America/New_York",
        event_fetchers=["ticketmaster", "eventbrite", "nyc_open_data", "fever"],
        reservation_platforms=["resy", "opentable"],
        michelin_slug="new-york",
        michelin_indexed=True,
        timeout_path="newyork/restaurants/100-best-new-york-restaurants",
        cnt_paths=["/gallery/best-new-restaurants-nyc"],
        curated_list_file="new_york.json",
    ),
    "bucharest": CityConfig(
        name="Bucharest",
        slug="bucharest",
        aliases=["bucharest", "buc", "bucuresti"],
        country="RO",
        timezone="Europe/Bucharest",
        event_fetchers=["iabilet", "songkick", "eventbrite", "ra"],
        reservation_platforms=["bookingham", "thefork"],
        michelin_slug=None,
        michelin_indexed=False,
        timeout_path=None,
        cnt_paths=[],
        curated_list_file="bucharest.json",
        notes="Bookingham.ro is the primary local reservation platform. iaBilet.ro is the main ticketing platform.",
    ),
    "marseille": CityConfig(
        name="Marseille",
        slug="marseille",
        aliases=["marseille"],
        country="FR",
        timezone="Europe/Paris",
        event_fetchers=["eventbrite"],
        reservation_platforms=["thefork"],
        michelin_slug="marseille",
        michelin_indexed=True,
        timeout_path="marseille/en/restaurants/best-restaurants-in-marseille",
        cnt_paths=["/story/best-restaurants-marseille"],
        curated_list_file="marseille.json",
    ),
    "messina": CityConfig(
        name="Messina",
        slug="messina",
        aliases=["messina"],
        country="IT",
        timezone="Europe/Rome",
        event_fetchers=["eventbrite"],
        reservation_platforms=["thefork"],
        michelin_slug="messina",
        michelin_indexed=True,
        timeout_path=None,
        cnt_paths=[],
        curated_list_file="messina.json",
    ),
    "valletta": CityConfig(
        name="Valletta",
        slug="valletta",
        aliases=["valletta", "malta"],
        country="MT",
        timezone="Europe/Malta",
        event_fetchers=["eventbrite"],
        reservation_platforms=["thefork"],
        michelin_slug="valletta",
        michelin_indexed=True,
        timeout_path=None,
        cnt_paths=[],
        curated_list_file="valletta.json",
    ),
}


# ══════════════════════════════════════════════════════════════════════════════
# Lookup Helpers
# ══════════════════════════════════════════════════════════════════════════════

# Build alias → slug lookup table once
_ALIAS_TO_SLUG: dict[str, str] = {}
for _cfg in CITIES.values():
    for _alias in _cfg.aliases:
        _ALIAS_TO_SLUG[_alias.lower()] = _cfg.slug


def get_city(name: str) -> CityConfig | None:
    """
    Look up a city by slug or any alias.

    Args:
        name: city slug or alias (case-insensitive)

    Returns:
        CityConfig if found, None otherwise
    """
    key = name.lower().strip()
    # Direct slug lookup
    if key in CITIES:
        return CITIES[key]
    # Alias lookup
    slug = _ALIAS_TO_SLUG.get(key)
    if slug:
        return CITIES[slug]
    return None


def list_cities() -> list[str]:
    """Return all registered city slugs."""
    return list(CITIES.keys())


def cities_for_country(country_code: str) -> list[CityConfig]:
    """
    Return all cities for a given ISO 2-letter country code.

    Args:
        country_code: ISO 2-letter country code (e.g., "IL", "US")

    Returns:
        List of CityConfig objects for that country
    """
    code = country_code.upper()
    return [cfg for cfg in CITIES.values() if cfg.country == code]
