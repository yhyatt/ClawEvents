"""
Tests for xceed.py _parse_dt_xceed year-rollover logic.
Covers normal dates, December/January boundary, and past-date handling.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from datetime import datetime
from unittest.mock import patch


# Import the function under test
from clawevents.fetchers.xceed import _parse_dt_xceed


class TestXceedDateParsing:

    def test_full_date_with_year_no_rollover(self):
        """Dates with an explicit year should be parsed as-is."""
        result = _parse_dt_xceed("Mar 21, 2026 23:00")
        assert result is not None
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 21
        assert result.hour == 23

    def test_normal_future_date_current_year(self):
        """A date in a month ahead of 'now' should get current year."""
        with patch("clawevents.fetchers.xceed.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 15)  # Mid-March
            mock_dt.strptime = datetime.strptime
            # April is in the future → current year
            result = _parse_dt_xceed("Fri, 10 Apr")
        assert result is not None
        assert result.year == 2026
        assert result.month == 4
        assert result.day == 10

    def test_december_date_scraped_in_december_current_year(self):
        """Dec 25 scraped on Dec 10 — same month, future day → current year."""
        with patch("clawevents.fetchers.xceed.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 12, 10)
            mock_dt.strptime = datetime.strptime
            result = _parse_dt_xceed("Fri, 25 Dec")
        assert result is not None
        assert result.year == 2026
        assert result.month == 12
        assert result.day == 25

    def test_january_date_scraped_in_december_next_year(self):
        """Jan 5 scraped in December — past month boundary → next year (2027)."""
        with patch("clawevents.fetchers.xceed.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 12, 15)
            mock_dt.strptime = datetime.strptime
            result = _parse_dt_xceed("Mon, 05 Jan")
        assert result is not None
        assert result.year == 2027, (
            f"Jan scraped in Dec should be next year, got {result.year}"
        )
        assert result.month == 1
        assert result.day == 5

    def test_past_date_in_current_month_next_year(self):
        """Dec 3 scraped on Dec 15 (same month, past day) → next year."""
        with patch("clawevents.fetchers.xceed.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 12, 15)
            mock_dt.strptime = datetime.strptime
            result = _parse_dt_xceed("Thu, 03 Dec")
        assert result is not None
        assert result.year == 2027, (
            f"Dec 3 scraped Dec 15 should roll to next year, got {result.year}"
        )

    def test_same_month_same_day_current_year(self):
        """Exact same day today → current year (not past, not future)."""
        with patch("clawevents.fetchers.xceed.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 20)
            mock_dt.strptime = datetime.strptime
            result = _parse_dt_xceed("Sat, 20 Jun")
        assert result is not None
        assert result.year == 2026

    def test_invalid_date_returns_none(self):
        """Garbage input should return None without raising."""
        result = _parse_dt_xceed("not a date")
        assert result is None

    def test_empty_string_returns_none(self):
        """Empty string should return None."""
        result = _parse_dt_xceed("")
        assert result is None

    def test_format_with_full_year_and_time(self):
        """'Mar 21, 2026 23:00' format should work."""
        result = _parse_dt_xceed("Mar 21, 2026 23:00")
        assert result is not None
        assert result.year == 2026
        assert result.month == 3

    def test_format_day_month_year(self):
        """'21 Mar 2026' format should work."""
        result = _parse_dt_xceed("21 Mar 2026")
        assert result is not None
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 21

    def test_regression_old_bug_december_january(self):
        """
        Regression for the original bug:
        Old code: dt.replace(year=datetime.now().year) — in December this gives
        Jan 5, 2026 (past date) for a Jan 5 event.
        New code correctly assigns Jan 5, 2027.
        """
        with patch("clawevents.fetchers.xceed.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 12, 20)
            mock_dt.strptime = datetime.strptime
            result = _parse_dt_xceed("Tue, 05 Jan")

        assert result is not None
        # Old buggy behavior would give 2026 (past date)
        assert result.year != 2026, "Bug regression: old code would assign 2026 (past)"
        assert result.year == 2027
