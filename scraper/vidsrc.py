import json
import re
from typing import List, Optional
from bs4 import BeautifulSoup
from scraper.base import BaseScraper
from models import MediaItem, StreamInfo
from scraper.tmdb import TMDBClient


class VidsrcScraper(BaseScraper):
    BASE_URL = "https://vidsrc.to"

    def __init__(self, tmdb: TMDBClient):
        super().__init__()
        self.tmdb = tmdb

    def scrape_all(self) -> List[MediaItem]:
        items = []
        items.extend(self._scrape_latest("movie"))
        items.extend(self._scrape_latest("tv"))
        return items

    def _scrape_latest(self, media_type: str, pages: int = 2) -> List[MediaItem]:
        items = []

        for page in range(1, pages + 1):
            url = f"{self.BASE_URL}/vapi/{media_type}/new/{page}"
            data = self._fetch_json(url)
            if not data:
                url2 = f"{self.BASE_URL}/vapi/{media_type}/add/{page}"
                data = self._fetch_json(url2)
            if not data:
                continue

            results = data if isinstance(data, list) else data.get("result", [])
            if not results:
                continue

            for entry in results[:50]:
                item = self._process_entry(entry, media_type)
                if item:
                    items.append(item)

        return items

    def _process_entry(self, entry: dict, media_type: str) -> Optional[MediaItem]:
        tmdb_id = entry.get("tmdb_id") or entry.get("id")
        imdb_id = entry.get("imdb_id")
        title = entry.get("title", "")
        year = entry.get("year")

        if not tmdb_id and imdb_id:
            pass
        if not tmdb_id:
            return None

        try:
            tmdb_id = int(tmdb_id)
        except (ValueError, TypeError):
            return None

        if media_type == "tv":
            details = self.tmdb.get_tv_details(tmdb_id)
        else:
            details = self.tmdb.get_movie_details(tmdb_id)

        if details:
            enriched = self.tmdb.enrich_movie(details)
            embed_url = f"{self.BASE_URL}/embed/{media_type}/{tmdb_id}"
            return MediaItem(
                tmdb_id=tmdb_id,
                title=enriched["title"],
                title_ar=enriched.get("title_ar"),
                year=enriched.get("year") or year,
                overview=enriched.get("overview"),
                poster=enriched.get("poster"),
                backdrop=enriched.get("backdrop"),
                genres=enriched.get("genres", []),
                rating=enriched.get("rating"),
                media_type=media_type,
                streams=[
                    StreamInfo(url=embed_url, quality="HD", source="vidsrc", language="en"),
                    StreamInfo(
                        url=f"https://vaplayer.ru/embed/{media_type}/{tmdb_id}",
                        quality="HD",
                        source="vidapi",
                        language="en",
                    ),
                ],
            )
        return None

    def scrape_movie(self, tmdb_id: int) -> Optional[MediaItem]:
        details = self.tmdb.get_movie_details(tmdb_id)
        if not details:
            return None
        enriched = self.tmdb.enrich_movie(details)
        return MediaItem(
            tmdb_id=tmdb_id,
            title=enriched["title"],
            title_ar=enriched.get("title_ar"),
            year=enriched.get("year"),
            overview=enriched.get("overview"),
            poster=enriched.get("poster"),
            backdrop=enriched.get("backdrop"),
            genres=enriched.get("genres", []),
            rating=enriched.get("rating"),
            media_type="movie",
            streams=[
                StreamInfo(
                    url=f"{self.BASE_URL}/embed/movie/{tmdb_id}",
                    quality="HD",
                    source="vidsrc",
                ),
                StreamInfo(
                    url=f"https://vaplayer.ru/embed/movie/{tmdb_id}",
                    quality="HD",
                    source="vidapi",
                ),
            ],
        )

    def _fetch_json(self, url: str) -> Optional[dict]:
        content = self.fetch(url, timeout=15)
        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass
        return None
