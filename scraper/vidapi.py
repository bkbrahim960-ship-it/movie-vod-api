import json
import re
from typing import List, Optional
from scraper.base import BaseScraper
from scraper.m3u8_resolver import M3U8Resolver
from models import MediaItem, StreamInfo
from scraper.tmdb import TMDBClient


class VidAPIScraper(BaseScraper):
    BASE_URL = "https://vidapi.ru"
    PLAYER_URL = "https://vaplayer.ru"

    def __init__(self, tmdb: TMDBClient):
        super().__init__()
        self.tmdb = tmdb
        self.m3u8 = M3U8Resolver()

    def scrape_all(self) -> List[MediaItem]:
        items = []
        for media_type in ["movie", "tv"]:
            for page in [1, 2]:
                items.extend(self._scrape_page(media_type, page))
        return items

    def _scrape_page(self, media_type: str, page: int) -> List[MediaItem]:
        url = f"{self.BASE_URL}/api/{media_type}?page={page}"
        content = self.fetch(url, timeout=15)
        if not content:
            return []

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return []

        results = data if isinstance(data, list) else data.get("data", data.get("results", []))
        items = []
        for entry in results[:100]:
            item = self._process_entry(entry, media_type)
            if item:
                items.append(item)
        return items

    def _process_entry(self, entry: dict, media_type: str) -> Optional[MediaItem]:
        tmdb_id = entry.get("tmdb_id") or entry.get("id")
        title = entry.get("title", "")
        year = entry.get("year")

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
            m3u8_urls = self.m3u8.resolve(media_type, tmdb_id)
            streams = []
            if m3u8_urls:
                for url in m3u8_urls:
                    streams.append(StreamInfo(url=url, quality="HD", source="vidsrc-m3u8", language="en"))
            streams.append(StreamInfo(
                url=f"{self.PLAYER_URL}/embed/{media_type}/{tmdb_id}",
                quality="HD", source="vidapi-embed", language="en",
            ))
            streams.append(StreamInfo(
                url=f"https://vidsrc.to/embed/{media_type}/{tmdb_id}",
                quality="HD", source="vidsrc-embed", language="en",
            ))
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
                streams=streams,
            )
        return None
