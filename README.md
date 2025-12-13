# play-store-scraper-ng

[![Tests](https://github.com/RankoR/google-play-scraper/actions/workflows/tests.yml/badge.svg?branch=master)](https://github.com/RankoR/google-play-scraper/actions/workflows/tests.yml)
[![PyPI version](https://img.shields.io/pypi/v/play-store-scraper-ng.svg)](https://pypi.org/project/play-store-scraper-ng/)

Modern, typed Google Play Store scraper client for Python. Fetch app details, search results, top lists, reviews, and search suggestions with a clean API and Pydantic models.

Based on and inspired by the original work at https://github.com/facundoolano/google-play-scraper, reworked with type hints, Pydantic models, and a simpler client API.


## Features

- Simple high-level client: `GooglePlayClient`
- Typed data models for responses via Pydantic: `AppDetails`, `AppOverview`, `Review`
- Search apps, fetch app details, list collections, reviews with pagination, and query suggestions
- Locale and country support (e.g., `hl=en`, `gl=us`)
- Optional throttling, proxy support, and SSL verification control
- Python 3.11+


## Installation

Install from PyPI:

```
pip install play-store-scraper-ng
```

Requires Python 3.11 or newer.


## Quickstart

```python
from google_play_scraper import GooglePlayClient

client = GooglePlayClient(country="us", lang="en")

# Fetch app details by ID
details = client.app("com.whatsapp")
print(details.title, details.score, details.installs)

# Search apps
results = client.search("todo list", num=10)
for app in results:
    print(app.title, app.score)
```


## Async Usage

The client also supports `async` usage with `httpx`. Async methods are prefixed with 'a' (e.g., `app` -> `aapp`). All synchronous methods have an asynchronous equivalent.

```python
import asyncio
from google_play_scraper import GooglePlayClient, Sort, Collection, Category

async def main():
    client = GooglePlayClient()

    # Async app details
    details = await client.aapp("com.whatsapp")
    print(f"App: {details.title}, Score: {details.score}")

    # Async search
    results = await client.asearch("photo editor", num=5)
    for app in results:
        print(f"Search result: {app.title}")

    # Async list
    top_free_games = await client.alist(
        collection=Collection.TOP_FREE,
        category=Category.GAME,
        num=10
    )
    for app in top_free_games:
        print(f"Top game: {app.title}")

    # Async reviews
    reviews, _ = await client.areviews("com.burbn.instagram", sort=Sort.NEWEST, num=5)
    for r in reviews:
        print(f"Review by {r.user_name}: {r.text[:50]}...")

    # Async suggestions
    suggestions = await client.asuggest("video")
    print(f"Suggestions for 'video': {suggestions}")


if __name__ == "__main__":
    asyncio.run(main())
```


## Usage

### Client initialization

```python
from google_play_scraper import GooglePlayClient

client = GooglePlayClient(
    country="us",                 # default country code for requests
    lang="en",                    # default language for responses
    proxies={"https": "http://host:port"},  # optional proxies for requests.Session
    throttle_requests_per_second=2,            # optional rate limit
    verify_ssl=True               # set to False to skip SSL verification (not recommended)
)
```

Parameters may be overridden per-call where supported (see below).


### Get app details

```python
from google_play_scraper import GooglePlayClient

client = GooglePlayClient()
app = client.app("com.spotify.music", lang="en", country="us")

print(app.title)
print(app.score, app.score_text)
print(app.price, app.currency)
print(app.developer, app.developer_email)
print(app.installs, app.min_installs, app.max_installs)
print(app.updated)
print(app.screenshots[:3])
```

Returns an `AppDetails` model (extends `AppOverview`).


### Search

```python
from google_play_scraper import GooglePlayClient

client = GooglePlayClient()
apps = client.search("timer", num=20, price="all", lang="en", country="us")
for a in apps:
    # a is AppOverview
    print(a.app_id, a.title, a.score)
```

`price` can be one of: `"all"` (default), `"free"`, `"paid"`.


### List collections

```python
from google_play_scraper import GooglePlayClient, Collection, Category, Age

client = GooglePlayClient()

top_free_tools = client.list(
    collection=Collection.TOP_FREE,
    category=Category.TOOLS,
    num=50,
    lang="en",
    country="us",
)

for app in top_free_tools:
    print(app.title, app.score)
```

See `google_play_scraper.constants` for available `Category`, `Collection`, and `Age` values.


### Reviews with pagination

```python
from google_play_scraper import GooglePlayClient, Sort

client = GooglePlayClient()

reviews, next_token = client.reviews(
    app_id="com.whatsapp",
    sort=Sort.NEWEST,     # or Sort.RATING / Sort.HELPFULNESS
    num=100,              # number of reviews to fetch (up to a server-side limit)
    lang="en",
    country="us",
)
```

`client.reviews` returns a tuple of `(reviews: list[Review], next_token: str | None)`. To request the next page, pass the token to the next call:

```python
from google_play_scraper import GooglePlayClient

client = GooglePlayClient()
reviews, next_token = client.reviews("com.whatsapp", num=100)
if next_token:
    more_reviews, next_token = client.reviews("com.whatsapp", num=100, pagination_token=next_token)
```


### Search suggestions

```python
from google_play_scraper import GooglePlayClient

client = GooglePlayClient()
suggestions = client.suggest("photo ed")
print(suggestions)
```


## Data models

All return types are validated Pydantic models that are easy to consume and serialize.

- `AppOverview`: minimal data used in lists/search (e.g., `title`, `app_id`, `score`, `icon`, `developer`)
- `AppDetails`: extends `AppOverview` with rich metadata (e.g., `description`, `installs`, `histogram`, `price`, `genre`, `screenshots`, `updated`)
- `Review`: normalized review entry (`score`, `text`, `user_name`, `thumbs_up`, dates, developer reply info)

See `google_play_scraper/models.py` for full fields.


## Constants

Import enums to control listing and sorting:

```python
from google_play_scraper import Category, Collection, Sort, Age
```


## Error handling

Common exceptions:

- `AppNotFound`: App ID does not exist or could not be parsed
- `ParsingError`: Unexpected response structure
- `QuotaExceeded`: Rate-limited or temporarily blocked by Google
- `GooglePlayError`: Base class for library errors

Handle errors explicitly:

```python
from google_play_scraper import GooglePlayClient
from google_play_scraper import AppNotFound, GooglePlayError

client = GooglePlayClient()
try:
    app = client.app("com.nonexistent.app")
except AppNotFound:
    print("App not found")
except GooglePlayError as e:
    print("General error:", e)
```


## Configuration, proxies, and rate limiting

- Locale/country: set defaults via `GooglePlayClient(country=..., lang=...)` and override per call
- Rate limiting: `throttle_requests_per_second` to avoid temporary blocking
- Proxies: pass a `requests`-style proxies dict (e.g., `{ "http": "http://host:port", "https": "http://host:port" }`)
- SSL: set `verify_ssl=False` only for troubleshooting


## Best practices and Notes

- Use conservative `throttle_requests_per_second` and caching when scraping at scale
- Respect Google Play Terms of Service and robots.txt. This library is for educational and research purposes; use responsibly
- API responses and page structures can change without notice; pin versions and add monitoring


## Examples and demos

See the `demo/` directory for runnable examples.

Sync demos:

- `demo/sync/demo_app.py` — fetch app details
- `demo/sync/demo_search.py` — search apps
- `demo/sync/demo_list.py` — list collections and categories
- `demo/sync/demo_reviews.py` — fetch reviews with pagination
- `demo/sync/demo_suggest.py` — query suggestions

Async demos:

- `demo/async/demo_app.py` — fetch app details
- `demo/async/demo_search.py` — search apps
- `demo/async/demo_list.py` — list collections and categories
- `demo/async/demo_reviews.py` — fetch reviews with pagination
- `demo/async/demo_suggest.py` — query suggestions

Run with:

```
python -m demo.sync.demo_app
python -m demo.async.demo_app
```


## Links

- PyPI: https://pypi.org/project/play-store-scraper-ng/
- Source: https://github.com/RankoR/google-play-scraper
- Issues: https://github.com/RankoR/google-play-scraper/issues


## Contributing

PRs and issues are welcome! Please run tests locally before submitting changes.


## License

MIT License. See `LICENSE`.