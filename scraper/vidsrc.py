import json
import time
from typing import List, Optional
from scraper.base import BaseScraper
from scraper.m3u8_resolver import M3U8Resolver
from models import MediaItem, StreamInfo
from scraper.tmdb import TMDBClient


class VidsrcScraper(BaseScraper):
    BASE_URL = "https://vidsrc.to"

    def __init__(self, tmdb: TMDBClient):
        super().__init__()
        self.tmdb = tmdb
        self.m3u8 = M3U8Resolver()

    def scrape_all(self) -> List[MediaItem]:
        items = []
        for tmdb_id in self._get_popular_ids()[:30]:
            item = self.scrape_movie(tmdb_id)
            if item:
                items.append(item)
            time.sleep(1)
        return items

    def _get_popular_ids(self) -> List[int]:
        ids = []
        for page in [1, 2]:
            url = f"{self.BASE_URL}/vapi/movie/new/{page}"
            data = self._fetch_json(url)
            if not data:
                url = f"{self.BASE_URL}/vapi/movie/add/{page}"
                data = self._fetch_json(url)
            if not data:
                continue
            results = data if isinstance(data, list) else data.get("result", [])
            for entry in results[:30]:
                tid = entry.get("tmdb_id") or entry.get("id")
                if tid:
                    try:
                        ids.append(int(tid))
                    except (ValueError, TypeError):
                        pass
        return ids

    def scrape_movie(self, tmdb_id: int) -> Optional[MediaItem]:
        details = self.tmdb.get_movie_details(tmdb_id)
        if not details:
            return None
        enriched = self.tmdb.enrich_movie(details)

        m3u8_urls = self.m3u8.resolve("movie", tmdb_id)
        streams = []

        if m3u8_urls:
            for url in m3u8_urls:
                streams.append(StreamInfo(url=url, quality="HD", source="vidsrc-m3u8", language="en"))
        else:
            streams.append(StreamInfo(
                url=f"{self.BASE_URL}/embed/movie/{tmdb_id}",
                quality="HD", source="vidsrc-embed", language="en",
            ))

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
            streams=streams,
        )

    def _fetch_json(self, url: str) -> Optional[dict]:
        content = self.fetch(url, timeout=15)
        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass
        return None
