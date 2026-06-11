import json
import re
from typing import List
from bs4 import BeautifulSoup
from scraper.base import BaseScraper
from models import MediaItem, StreamInfo
from scraper.tmdb import TMDBClient


class CinemaOSScraper(BaseScraper):
    BASE_URL = "https://cinemaos.in"

    def __init__(self, tmdb: TMDBClient):
        super().__init__()
        self.tmdb = tmdb

    def scrape_all(self) -> List[MediaItem]:
        items = []
        items.extend(self._scrape_list("movie", "trending"))
        items.extend(self._scrape_list("movie", "top-rated"))
        items.extend(self._scrape_list("tv", "trending"))
        items.extend(self._scrape_list("tv", "top-rated"))
        return items

    def _scrape_list(self, media_type: str, list_type: str) -> List[MediaItem]:
        url = f"{self.BASE_URL}/{media_type}/{list_type}"
        if media_type == "tv":
            url = f"{self.BASE_URL}/tv/{list_type}"
        if media_type == "movie":
            url = f"{self.BASE_URL}/movie/{list_type}"
        content = self.fetch(url)
        if not content:
            return []

        soup = BeautifulSoup(content, "lxml")
        items = []

        cards = soup.select("a[href*='/movie/'], a[href*='/tv/']")
        seen = set()
        for card in cards:
            href = card.get("href", "")
            title_text = card.get_text(strip=True)
            if not href or not title_text:
                continue

            match = re.search(r'/(movie|tv)/(\d+)', href)
            if not match:
                continue
            mtype = match.group(1)
            tmdb_id = int(match.group(2))

            key = f"{mtype}_{tmdb_id}"
            if key in seen:
                continue
            seen.add(key)

            if mtype == "tv":
                details = self.tmdb.get_tv_details(tmdb_id)
            else:
                details = self.tmdb.get_movie_details(tmdb_id)

            if details:
                enriched = self.tmdb.enrich_movie(details)
                item = MediaItem(
                    tmdb_id=tmdb_id,
                    title=enriched["title"],
                    title_ar=enriched.get("title_ar"),
                    year=enriched.get("year"),
                    overview=enriched.get("overview"),
                    poster=enriched.get("poster"),
                    backdrop=enriched.get("backdrop"),
                    genres=enriched.get("genres", []),
                    rating=enriched.get("rating"),
                    media_type=mtype,
                    streams=[
                        StreamInfo(
                            url=f"{self.BASE_URL}/watch/{mtype}/{tmdb_id}",
                            quality="HD",
                            source="cinemaos",
                        ),
                        StreamInfo(
                            url=f"https://vidsrc.to/embed/{mtype}/{tmdb_id}",
                            quality="HD",
                            source="vidsrc",
                        ),
                        StreamInfo(
                            url=f"https://vaplayer.ru/embed/{mtype}/{tmdb_id}",
                            quality="HD",
                            source="vidapi",
                        ),
                    ],
                )
                items.append(item)

        return items
