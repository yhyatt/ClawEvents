"""Tests for city_registry module."""
import pytest
import sys
import os

# Add parent package to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from clawevents.city_registry import CITIES, get_city, list_cities, cities_for_country
from clawevents.models import City


def test_bucharest_in_registry():
    """Bucharest should be in the registry."""
    assert "bucharest" in CITIES
    cfg = CITIES["bucharest"]
    assert cfg.name == "Bucharest"
    assert cfg.country == "RO"
    assert cfg.timezone == "Europe/Bucharest"
    assert "iabilet" in cfg.event_fetchers
    assert "bookingham" in cfg.reservation_platforms


def test_all_city_aliases_resolve():
    """All aliases should resolve to their parent city."""
    for slug, cfg in CITIES.items():
        for alias in cfg.aliases:
            resolved = get_city(alias)
            assert resolved is not None, f"Alias '{alias}' did not resolve"
            assert resolved.slug == slug, f"Alias '{alias}' resolved to wrong city"


def test_city_fetchers_derived_from_registry():
    """Engine's _CITY_FETCHERS should match registry."""
    from clawevents.engine import _CITY_FETCHERS
    
    # Tel Aviv should have the expected fetchers
    assert City.TEL_AVIV in _CITY_FETCHERS
    assert _CITY_FETCHERS[City.TEL_AVIV] == ["tlv_municipality", "eventbrite", "lev_cinema", "timeout_il"]
    
    # Barcelona should have the expected fetchers
    assert City.BARCELONA in _CITY_FETCHERS
    assert "ticketmaster" in _CITY_FETCHERS[City.BARCELONA]
    assert "fever" in _CITY_FETCHERS[City.BARCELONA]


def test_tel_aviv_fetchers():
    """Tel Aviv should have the correct fetchers."""
    cfg = get_city("tel-aviv")
    assert cfg is not None
    assert cfg.event_fetchers == ["tlv_municipality", "eventbrite", "lev_cinema", "timeout_il"]
    
    # Also test alias
    cfg2 = get_city("tlv")
    assert cfg2 is not None
    assert cfg2.slug == "tel-aviv"
    assert cfg2.event_fetchers == cfg.event_fetchers


def test_get_city_by_alias():
    """get_city should resolve various alias formats."""
    # TLV variations
    assert get_city("tlv") is not None
    assert get_city("TLV") is not None
    assert get_city("tel-aviv") is not None
    assert get_city("telaviv") is not None
    assert get_city("tel aviv") is not None
    
    # Barcelona variations
    assert get_city("barcelona") is not None
    assert get_city("BCN") is not None
    assert get_city("bcn") is not None
    
    # NYC variations
    assert get_city("nyc") is not None
    assert get_city("new-york") is not None
    assert get_city("new york") is not None
    assert get_city("newyork") is not None
    
    # Bucharest variations
    assert get_city("bucharest") is not None
    assert get_city("buc") is not None
    assert get_city("bucuresti") is not None
    
    # Unknown should return None
    assert get_city("unknown-city") is None


def test_list_cities():
    """list_cities should return all city slugs."""
    slugs = list_cities()
    assert "tel-aviv" in slugs
    assert "barcelona" in slugs
    assert "new-york" in slugs
    assert "bucharest" in slugs
    assert len(slugs) >= 7  # We have at least 7 cities


def test_cities_for_country():
    """cities_for_country should return correct cities."""
    israel = cities_for_country("IL")
    assert any(c.slug == "tel-aviv" for c in israel)
    
    romania = cities_for_country("RO")
    assert any(c.slug == "bucharest" for c in romania)
    assert len(romania) == 1  # Only Bucharest
    
    italy = cities_for_country("IT")
    assert any(c.slug == "messina" for c in italy)


def test_bucharest_michelin_not_indexed():
    """Bucharest should not be in Michelin index."""
    cfg = get_city("bucharest")
    assert cfg is not None
    assert cfg.michelin_indexed is False
    assert cfg.michelin_slug is None


def test_barcelona_michelin_indexed():
    """Barcelona should be in Michelin index."""
    cfg = get_city("barcelona")
    assert cfg is not None
    assert cfg.michelin_indexed is True
    assert cfg.michelin_slug == "barcelona"


def test_cli_aliases_derived():
    """CLI should derive aliases from registry."""
    from clawevents.cli import _CITY_ALIASES
    
    # Should contain all registry aliases
    assert "tlv" in _CITY_ALIASES
    assert "bcn" in _CITY_ALIASES
    assert "nyc" in _CITY_ALIASES
    
    # Bucharest aliases should be present (if Bucharest is in City enum)
    if City.BUCHAREST:
        assert "bucharest" in _CITY_ALIASES or "buc" in _CITY_ALIASES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
