import re
import json
from typing import List, Tuple, Optional
from scraper.base import BaseScraper
from models import MediaItem, StreamInfo
from scraper.tmdb import TMDBClient


class GitHubM3UScraper(BaseScraper):
    def __init__(self, tmdb: TMDBClient):
        super().__init__()
        self.tmdb = tmdb
        self.sources = self._load_sources()

    def _load_sources(self) -> list:
        try:
            with open("m3u_sources.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("github", [])
        except Exception as e:
            print(f"[GitHubM3U] Failed to load sources: {e}")
            return []

    def scrape_source(self, source: dict) -> List[MediaItem]:
        url = source.get("url", "")
        name = source.get("name", "unknown")
        print(f"[GitHubM3U] Fetching {name}: {url}")

        content = self.fetch(url)
        if not content:
            print(f"[GitHubM3U] Failed to fetch {url}")
            return []

        entries = self.parse_m3u(content)
        print(f"[GitHubM3U] Found {len(entries)} entries from {name}")

        results = []
        seen_titles = set()
        processed = 0
        max_entries = 500
        for title, url, logo, group in entries:
            processed += 1
            if processed > max_entries:
                break
            if not title:
                continue

            clean_title, year = self.extract_title_year(title)
            quality = self.extract_quality(f"{title} {group or ''}")
            is_tv = bool(group and any(kw in group.lower() for kw in ["series", "serie", "tv", "مسلسل"]))

            key = f"{clean_title.lower()}_{year or 0}"
            if key in seen_titles:
                continue
            seen_titles.add(key)

            if is_tv:
                tmdb_data = self.tmdb.search_tv(clean_title, year)
            else:
                tmdb_data = self.tmdb.search_movie(clean_title, year)
            import time
            time.sleep(0.3)

            if tmdb_data:
                enriched = self.tmdb.enrich_movie(tmdb_data)
                item = MediaItem(
                    tmdb_id=enriched["tmdb_id"],
                    title=enriched["title"],
                    title_ar=enriched["title_ar"],
                    year=enriched["year"],
                    overview=enriched["overview"],
                    poster=enriched["poster"],
                    backdrop=enriched["backdrop"],
                    genres=enriched["genres"],
                    rating=enriched["rating"],
                    media_type="tv" if is_tv else "movie",
                    streams=[StreamInfo(
                        url=url,
                        quality=quality,
                        source=f"github:{name}",
                        language=self._detect_language(title, group),
                    )],
                )
                results.append(item)
                print(f"[GitHubM3U] ✓ {item.title} ({item.year})")
            else:
                item = MediaItem(
                    tmdb_id=hash(clean_title) % 10000000,
                    title=clean_title,
                    year=year,
                    media_type="tv" if is_tv else "movie",
                    streams=[StreamInfo(
                        url=url,
                        quality=quality,
                        source=f"github:{name}",
                        language=self._detect_language(title, group),
                    )],
                )
                results.append(item)

        return results

    def scrape_all(self) -> List[MediaItem]:
        all_items = []
        for source in self.sources:
            items = self.scrape_source(source)
            all_items.extend(items)
        return all_items

    def _detect_language(self, title: str, group: Optional[str] = None) -> str:
        if group:
            g = group.lower()
            if "arabic" in g or "عربي" in g:
                return "ar"
            if "english" in g or "en" in g:
                return "en"
            if "turkish" in g or "تركي" in g:
                return "tr"
            if "hindi" in g:
                return "hi"
        arabic_chars = sum(1 for c in title if '\u0600' <= c <= '\u06ff')
        if arabic_chars > 3:
            return "ar"
        return "en"
