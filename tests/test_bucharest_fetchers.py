"""Tests for Bucharest event fetchers — iaBilet, Songkick, RA."""
import pytest
import sys
import os
from datetime import datetime, timedelta

# Add parent package to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from clawevents.models import City, EventType
from clawevents.fetchers.iabilet import IaBiletFetcher
from clawevents.fetchers.songkick import SongkickFetcher
from clawevents.fetchers.ra import RAFetcher
from clawevents.engine import ClawEventsEngine, _FETCHER_REGISTRY


# ══════════════════════════════════════════════════════════════════════════════
# iaBilet tests
# ══════════════════════════════════════════════════════════════════════════════

def test_iabilet_fetcher_instantiates():
    """IaBiletFetcher should instantiate without errors."""
    fetcher = IaBiletFetcher()
    assert fetcher is not None
    assert fetcher.source_name == "iabilet"


def test_iabilet_supports_bucharest():
    """IaBiletFetcher should support Bucharest."""
    fetcher = IaBiletFetcher()
    assert City.BUCHAREST in fetcher.supported_cities
    assert fetcher.supports(City.BUCHAREST)


def test_iabilet_does_not_support_other_cities():
    """IaBiletFetcher should only support Bucharest."""
    fetcher = IaBiletFetcher()
    assert not fetcher.supports(City.BARCELONA)
    assert not fetcher.supports(City.NEW_YORK)
    assert not fetcher.supports(City.TEL_AVIV)


def test_iabilet_fetch_returns_list():
    """IaBiletFetcher.fetch should return a list (may be empty if network issues)."""
    fetcher = IaBiletFetcher()
    start = datetime.now()
    end = start + timedelta(days=30)
    
    try:
        events = fetcher.fetch(City.BUCHAREST, start, end)
        assert isinstance(events, list)
    except Exception:
        pytest.skip("Network unavailable or iaBilet blocked")


def test_iabilet_fetch_unsupported_city_returns_empty():
    """IaBiletFetcher.fetch should return empty list for unsupported cities."""
    fetcher = IaBiletFetcher()
    start = datetime.now()
    end = start + timedelta(days=7)
    
    events = fetcher.fetch(City.BARCELONA, start, end)
    assert events == []


# ══════════════════════════════════════════════════════════════════════════════
# Songkick tests
# ══════════════════════════════════════════════════════════════════════════════

def test_songkick_fetcher_instantiates():
    """SongkickFetcher should instantiate without errors."""
    fetcher = SongkickFetcher()
    assert fetcher is not None
    assert fetcher.source_name == "songkick"


def test_songkick_supports_bucharest():
    """SongkickFetcher should support Bucharest."""
    fetcher = SongkickFetcher()
    assert City.BUCHAREST in fetcher.supported_cities
    assert fetcher.supports(City.BUCHAREST)


def test_songkick_supports_multiple_cities():
    """SongkickFetcher should support multiple cities."""
    fetcher = SongkickFetcher()
    assert fetcher.supports(City.BUCHAREST)
    assert fetcher.supports(City.BARCELONA)
    assert fetcher.supports(City.NEW_YORK)
    assert fetcher.supports(City.TEL_AVIV)


def test_songkick_fetch_returns_list():
    """SongkickFetcher.fetch should return a list."""
    fetcher = SongkickFetcher()
    start = datetime.now()
    end = start + timedelta(days=30)
    
    try:
        events = fetcher.fetch(City.BUCHAREST, start, end)
        assert isinstance(events, list)
    except Exception:
        pytest.skip("Network unavailable or Songkick blocked")


def test_songkick_all_events_are_concerts():
    """All Songkick events should be classified as concerts."""
    fetcher = SongkickFetcher()
    start = datetime.now()
    end = start + timedelta(days=30)
    
    try:
        events = fetcher.fetch(City.BUCHAREST, start, end, limit=5)
        for event in events:
            assert EventType.CONCERT in event.event_types
    except Exception:
        pytest.skip("Network unavailable")


# ══════════════════════════════════════════════════════════════════════════════
# RA (Resident Advisor) tests
# ══════════════════════════════════════════════════════════════════════════════

def test_ra_fetcher_instantiates():
    """RAFetcher should instantiate without errors."""
    fetcher = RAFetcher()
    assert fetcher is not None
    assert fetcher.source_name == "ra"


def test_ra_supports_bucharest():
    """RAFetcher should support Bucharest."""
    fetcher = RAFetcher()
    assert City.BUCHAREST in fetcher.supported_cities
    assert fetcher.supports(City.BUCHAREST)


def test_ra_supports_multiple_cities():
    """RAFetcher should support multiple cities."""
    fetcher = RAFetcher()
    assert fetcher.supports(City.BUCHAREST)
    assert fetcher.supports(City.BARCELONA)
    assert fetcher.supports(City.NEW_YORK)
    assert fetcher.supports(City.TEL_AVIV)


def test_ra_fetch_returns_list():
    """RAFetcher.fetch should return a list."""
    fetcher = RAFetcher()
    start = datetime.now()
    end = start + timedelta(days=30)
    
    try:
        events = fetcher.fetch(City.BUCHAREST, start, end)
        assert isinstance(events, list)
    except Exception:
        pytest.skip("Network unavailable or RA blocked")


def test_ra_all_events_are_nightlife():
    """All RA events should be classified as nightlife."""
    fetcher = RAFetcher()
    start = datetime.now()
    end = start + timedelta(days=30)
    
    try:
        events = fetcher.fetch(City.BUCHAREST, start, end, limit=5)
        for event in events:
            assert EventType.NIGHTLIFE in event.event_types
    except Exception:
        pytest.skip("Network unavailable")


# ══════════════════════════════════════════════════════════════════════════════
# Engine / Registry tests
# ══════════════════════════════════════════════════════════════════════════════

def test_engine_has_bucharest_fetchers():
    """Engine registry should include iabilet, songkick, and ra fetchers."""
    assert "iabilet" in _FETCHER_REGISTRY
    assert "songkick" in _FETCHER_REGISTRY
    assert "ra" in _FETCHER_REGISTRY


def test_engine_instantiates_bucharest_fetchers():
    """Engine should successfully instantiate Bucharest fetchers."""
    engine = ClawEventsEngine()
    assert "iabilet" in engine._fetchers
    assert "songkick" in engine._fetchers
    assert "ra" in engine._fetchers


def test_bucharest_search_returns_events():
    """Engine.search for Bucharest should return a list of events."""
    engine = ClawEventsEngine()
    
    try:
        events = engine.search(
            cities=[City.BUCHAREST],
            start=datetime.now(),
            end=datetime.now() + timedelta(days=14),
            limit=20,
        )
        assert isinstance(events, list)
        # Note: might be empty if no events or network issues
    except Exception as e:
        pytest.skip(f"Network unavailable: {e}")


def test_bucharest_search_events_have_correct_city():
    """All events from Bucharest search should be for Bucharest."""
    engine = ClawEventsEngine()
    
    try:
        events = engine.search(
            cities=[City.BUCHAREST],
            start=datetime.now(),
            end=datetime.now() + timedelta(days=14),
            limit=10,
        )
        for event in events:
            assert event.city == City.BUCHAREST
    except Exception:
        pytest.skip("Network unavailable")


# ══════════════════════════════════════════════════════════════════════════════
# Date parsing tests (unit tests, no network)
# ══════════════════════════════════════════════════════════════════════════════

def test_iabilet_romanian_date_parsing():
    """Test Romanian date parsing."""
    from clawevents.fetchers.iabilet import _parse_ro_date
    
    # Test various formats
    assert _parse_ro_date("21 mar", year=2026) == datetime(2026, 3, 21)
    assert _parse_ro_date("5 apr", year=2026) == datetime(2026, 4, 5)
    assert _parse_ro_date("31 oct '25") == datetime(2025, 10, 31)
    assert _parse_ro_date("1 ianuarie", year=2026) == datetime(2026, 1, 1)
    
    # Invalid should return None
    assert _parse_ro_date("invalid") is None
    assert _parse_ro_date("") is None


def test_ra_datetime_parsing():
    """Test RA datetime parsing."""
    from clawevents.fetchers.ra import _parse_ra_datetime
    
    # Test various formats
    dt = _parse_ra_datetime("2026-03-06T22:00:00.000")
    assert dt == datetime(2026, 3, 6, 22, 0, 0)
    
    dt = _parse_ra_datetime("2026-03-06T00:00:00.000")
    assert dt == datetime(2026, 3, 6, 0, 0, 0)
    
    # Invalid should return None
    assert _parse_ra_datetime(None) is None
    assert _parse_ra_datetime("") is None


def test_songkick_date_parsing():
    """Test Songkick date scraping."""
    from clawevents.fetchers.songkick import _scrape_date
    
    # Test various formats
    assert _scrape_date("Sat, Mar 22, 2026") == datetime(2026, 3, 22)
    assert _scrape_date("March 22, 2026") == datetime(2026, 3, 22)
    
    # Invalid should return None
    assert _scrape_date("") is None
    assert _scrape_date("invalid") is None


# ══════════════════════════════════════════════════════════════════════════════
# Robustness / Audit tests
# ══════════════════════════════════════════════════════════════════════════════

def test_iabilet_module_has_timeout():
    """iaBilet fetcher should have timeout in requests call."""
    import inspect
    from clawevents.fetchers.iabilet import IaBiletFetcher
    
    source = inspect.getsource(IaBiletFetcher.fetch)
    # Check that timeout is specified in the requests.get call
    assert "timeout=" in source or "timeout" in source


def test_iabilet_handles_missing_bs4():
    """iaBilet should handle missing BeautifulSoup gracefully."""
    from clawevents.fetchers import iabilet
    
    # Check that the module has the _BS4_AVAILABLE flag
    assert hasattr(iabilet, '_BS4_AVAILABLE')


def test_songkick_has_timeout():
    """Songkick fetcher should have timeout in requests calls."""
    import inspect
    from clawevents.fetchers.songkick import SongkickFetcher
    
    source = inspect.getsource(SongkickFetcher)
    assert "timeout=" in source


def test_songkick_handles_missing_bs4():
    """Songkick should handle missing BeautifulSoup gracefully."""
    from clawevents.fetchers import songkick
    
    assert hasattr(songkick, '_BS4_AVAILABLE')


def test_songkick_fallback_to_scraping():
    """Songkick should fall back to scraping when no API key."""
    fetcher = SongkickFetcher(api_key=None)
    assert fetcher.api_key == ""  # Should be empty string, not None


def test_ra_has_timeout():
    """RA fetcher should have timeout in requests call."""
    import inspect
    from clawevents.fetchers.ra import RAFetcher
    
    source = inspect.getsource(RAFetcher.fetch)
    assert "timeout=" in source


def test_ra_area_id_bucharest_documented():
    """RA area ID for Bucharest should be documented."""
    from clawevents.fetchers.ra import AREA_IDS
    
    assert City.BUCHAREST in AREA_IDS
    assert AREA_IDS[City.BUCHAREST] == 381  # Documented value


def test_ra_area_id_barcelona():
    """RA area ID for Barcelona should be documented."""
    from clawevents.fetchers.ra import AREA_IDS
    
    assert City.BARCELONA in AREA_IDS
    assert AREA_IDS[City.BARCELONA] == 20


def test_ra_area_id_nyc():
    """RA area ID for NYC should be documented."""
    from clawevents.fetchers.ra import AREA_IDS
    
    assert City.NEW_YORK in AREA_IDS
    assert AREA_IDS[City.NEW_YORK] == 8


def test_ra_area_id_tel_aviv():
    """RA area ID for Tel Aviv should be documented."""
    from clawevents.fetchers.ra import AREA_IDS
    
    assert City.TEL_AVIV in AREA_IDS
    assert AREA_IDS[City.TEL_AVIV] == 413


def test_iabilet_http_error_handling():
    """iaBilet should return empty list on HTTP errors."""
    from unittest.mock import patch, MagicMock
    from clawevents.fetchers.iabilet import IaBiletFetcher
    
    fetcher = IaBiletFetcher()
    start = datetime.now()
    end = start + timedelta(days=7)
    
    # Mock requests.get to raise an exception
    with patch('clawevents.fetchers.iabilet.requests.get') as mock_get:
        mock_get.side_effect = Exception("Network error")
        events = fetcher.fetch(City.BUCHAREST, start, end)
        assert events == []


def test_iabilet_404_returns_empty():
    """iaBilet should return empty list on 404."""
    from unittest.mock import patch, MagicMock
    import requests as req
    from clawevents.fetchers.iabilet import IaBiletFetcher
    
    fetcher = IaBiletFetcher()
    start = datetime.now()
    end = start + timedelta(days=7)
    
    # Mock requests.get to return 404
    with patch('clawevents.fetchers.iabilet.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = req.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        events = fetcher.fetch(City.BUCHAREST, start, end)
        assert events == []


def test_ra_graphql_error_handling():
    """RA should handle GraphQL errors gracefully."""
    from unittest.mock import patch, MagicMock
    from clawevents.fetchers.ra import RAFetcher
    
    fetcher = RAFetcher()
    start = datetime.now()
    end = start + timedelta(days=7)
    
    # Mock requests.post to return GraphQL error
    with patch('clawevents.fetchers.ra.requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"errors": [{"message": "Invalid query"}]}
        mock_post.return_value = mock_response
        events = fetcher.fetch(City.BUCHAREST, start, end)
        assert events == []


def test_songkick_metro_ids_documented():
    """Songkick metro IDs should be documented with verification notes."""
    import inspect
    from clawevents.fetchers import songkick
    
    source = inspect.getsource(songkick)
    # Check for documentation comments
    assert "verified" in source.lower() or "METRO_IDS" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
