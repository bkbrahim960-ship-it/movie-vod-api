import json
import re
from typing import List
from bs4 import BeautifulSoup
from scraper.base import BaseScraper
from models import MediaItem, StreamInfo
from scraper.tmdb import TMDBClient


class IPTVSitesScraper(BaseScraper):
    def __init__(self, tmdb: TMDBClient):
        super().__init__()
        self.tmdb = tmdb
        self.sources = self._load_sources()

    def _load_sources(self) -> list:
        try:
            with open("m3u_sources.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("iptv_sites", [])
        except Exception as e:
            print(f"[IPTVSites] Failed to load sources: {e}")
            return []

    def scrape_source(self, source: dict) -> List[MediaItem]:
        url = source.get("url", "")
        name = source.get("name", "unknown")
        print(f"[IPTVSites] Scraping {name}: {url}")

        content = self.fetch(url)
        if not content:
            return []

        soup = BeautifulSoup(content, "lxml")

        m3u_urls = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.endswith(".m3u") or href.endswith(".m3u8") or "m3u" in href.lower():
                if href.startswith("http"):
                    m3u_urls.add(href)
                else:
                    from urllib.parse import urljoin
                    m3u_urls.add(urljoin(url, href))

        for script in soup.find_all("script"):
            if script.string:
                matches = re.findall(r'https?://[^\s"\'<>]+\.(?:m3u8?|txt)[^\s"\'<>]*', script.string)
                for m in matches:
                    m3u_urls.add(m)

        print(f"[IPTVSites] Found {len(m3u_urls)} M3U URLs from {name}")

        all_items = []
        for m3u_url in m3u_urls:
            items = self._process_m3u(m3u_url, name)
            all_items.extend(items)

        return all_items

    def _process_m3u(self, url: str, source_name: str) -> List[MediaItem]:
        content = self.fetch(url)
        if not content:
            return []

        entries = self.parse_m3u(content)
        results = []
        seen_ids = set()

        for title, stream_url, logo, group in entries[:200]:
            if not title:
                continue

            clean_title, year = self.extract_title_year(title)
            quality = self.extract_quality(f"{title} {group or ''}")
            is_tv = bool(group and any(kw in group.lower() for kw in ["series", "serie", "tv", "مسلسل", "episode", "season"]))

            if is_tv:
                tmdb_data = self.tmdb.search_tv(clean_title, year)
            else:
                tmdb_data = self.tmdb.search_movie(clean_title, year)

            if tmdb_data:
                enriched = self.tmdb.enrich_movie(tmdb_data)
                tmdb_id = enriched["tmdb_id"]
                if tmdb_id in seen_ids:
                    item = MediaItem(
                        tmdb_id=tmdb_id,
                        title=enriched["title"],
                        media_type="tv" if is_tv else "movie",
                        streams=[StreamInfo(url=stream_url, quality=quality, source=f"iptv:{source_name}")],
                    )
                    results.append(item)
                    continue

                seen_ids.add(tmdb_id)
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
                    media_type="tv" if is_tv else "movie",
                    streams=[StreamInfo(url=stream_url, quality=quality, source=f"iptv:{source_name}")],
                )
                results.append(item)
            else:
                clean_title_lower = clean_title.lower()
                fake_id = hash(clean_title_lower) % 10000000
                if fake_id in seen_ids:
                    continue
                seen_ids.add(fake_id)
                item = MediaItem(
                    tmdb_id=fake_id,
                    title=clean_title,
                    year=year,
                    media_type="tv" if is_tv else "movie",
                    streams=[StreamInfo(url=stream_url, quality=quality, source=f"iptv:{source_name}")],
                )
                results.append(item)

        return results

    def scrape_all(self) -> List[MediaItem]:
        all_items = []
        for source in self.sources:
            items = self.scrape_source(source)
            all_items.extend(items)
        return all_items
