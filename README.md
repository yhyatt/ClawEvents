# ClawEvents 🎉

Multi-city event discovery for [OpenClaw](https://openclaw.ai) agents.

**Cities:** Tel Aviv · Barcelona · New York

**Sources:** Ticketmaster · Eventbrite · TLV Municipality · Lev Cinema · Time Out IL · Fever · Xceed · NYC Open Data

---

## Install

```bash
pip install clawevents

# For browser-based scrapers (Time Out IL, Fever, Xceed):
pip install clawevents[browser]
playwright install chromium
```

## Quick Start

```bash
# Jazz in Tel Aviv this week
clawevents search --city tel-aviv --type jazz --days 7

# Cinema tonight
clawevents search --city tel-aviv --type cinema --days 1

# Multi-city weekend
clawevents search --city barcelona new-york --days 3

# Free family events, afternoon
clawevents search --city tel-aviv --type family --age family --time afternoon --free

# Evening concerts, adults only
clawevents search --city tel-aviv barcelona --type concert --age adults --time evening

# JSON output
clawevents search --city new-york --type jazz --format json --limit 10
```

## API Keys (free)

| Key | Signup | Enables |
|-----|--------|---------|
| `TICKETMASTER_API_KEY` | [developer.ticketmaster.com](https://developer.ticketmaster.com) | Barcelona + NYC concerts, theatre, sports |
| `EVENTBRITE_TOKEN` | [eventbrite.com/platform/api](https://www.eventbrite.com/platform/api) | All 3 cities — community + cultural events |
| `TLV_API_KEY` | [apiportal.tel-aviv.gov.il](https://apiportal.tel-aviv.gov.il) | Official TLV city events (optional — free scrape fallback) |

```bash
export TICKETMASTER_API_KEY="..."
export EVENTBRITE_TOKEN="..."
export TLV_API_KEY="..."   # optional
```

## Filters

| Flag | Values |
|------|--------|
| `--city` | `tel-aviv` / `tlv`, `barcelona` / `bcn`, `new-york` / `nyc` |
| `--type` | `jazz`, `concert`, `cinema`, `theatre`, `nightlife`, `family`, `comedy`, `art`, `sport`, `festival` |
| `--age` | `kids`, `family`, `adults` |
| `--time` | `morning`, `afternoon`, `evening`, `late-night` |
| `--from` / `--to` | `YYYY-MM-DD` |
| `--days` | days from today (default 7) |
| `--free` | free events only |
| `--limit` | max results (default 20) |
| `--format` | `text` or `json` |

## Sources per City

### Tel Aviv 🇮🇱
| Source | Type | Key needed |
|--------|------|-----------|
| TLV Municipality API | Official city events (DigiTel) | Optional (`TLV_API_KEY`) |
| Eventbrite | Tech, culture, community | `EVENTBRITE_TOKEN` |
| Lev Cinema | Boutique cinema (Dizengoff) | None |
| Time Out IL | Jazz, nightlife, theatre picks | None (Playwright) |

### Barcelona 🇪🇸
| Source | Type | Key needed |
|--------|------|-----------|
| Ticketmaster | Concerts, theatre, sports | `TICKETMASTER_API_KEY` |
| Eventbrite | Community + cultural | `EVENTBRITE_TOKEN` |
| Fever | Experiences, immersive, concerts | None (Playwright) |
| Xceed | Clubs, nightlife (Pacha, Razzmatazz, Apolo) | None (Playwright) |

### New York 🗽
| Source | Type | Key needed |
|--------|------|-----------|
| Ticketmaster | Concerts, Broadway, sports | `TICKETMASTER_API_KEY` |
| Eventbrite | Community + cultural | `EVENTBRITE_TOKEN` |
| NYC Open Data | Free parks/city events | None |
| Fever | Experiences, immersive | None (Playwright) |

## Use in Python

```python
from clawevents import ClawEventsEngine, City, EventType, AgeGroup, TimeOfDay
from datetime import datetime, timedelta

engine = ClawEventsEngine()
events = engine.search(
    cities=[City.TEL_AVIV],
    event_types=[EventType.JAZZ],
    start=datetime.now(),
    end=datetime.now() + timedelta(days=7),
    age_groups=[AgeGroup.ADULTS],
    time_of_day=[TimeOfDay.EVENING],
    limit=10,
)
for e in events:
    print(e.title, e.start, e.venue_name)
```

## Architecture

```
ClawEventsEngine
├── Parallel fetchers (per city, ThreadPoolExecutor)
│   ├── API-based:  Ticketmaster, Eventbrite, TLV Municipality, NYC Open Data
│   └── Browser:    Time Out IL, Fever, Xceed  (requires playwright)
├── Filter   — city, type, age, time-of-day, date range, free
├── Dedup    — same title + time across sources
└── Rank     — chronological (no-time events last)
```

## Extending

```python
# Add a new fetcher
from clawevents.fetchers.base import BaseFetcher
from clawevents.models import City, Event, EventType

class MyFetcher(BaseFetcher):
    source_name = "my_source"
    supported_cities = [City.TEL_AVIV]

    def fetch(self, city, start, end, event_types=None, limit=50):
        # ... return List[Event]
        pass
```

Then register in `engine.py`:
```python
_FETCHER_REGISTRY["my_source"] = MyFetcher
_CITY_FETCHERS[City.TEL_AVIV].append("my_source")
```

## License

MIT
