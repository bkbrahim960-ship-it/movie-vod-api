import json
from typing import List
from scraper.base import BaseScraper
from models import MediaItem, StreamInfo
from scraper.tmdb import TMDBClient


class TelegramScraper(BaseScraper):
    def __init__(self, tmdb: TMDBClient):
        super().__init__()
        self.tmdb = tmdb
        self.sources = self._load_sources()

    def _load_sources(self) -> list:
        try:
            with open("m3u_sources.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("telegram", [])
        except Exception as e:
            print(f"[Telegram] Failed to load sources: {e}")
            return []

    def scrape_source(self, source: dict) -> List[MediaItem]:
        username = source.get("username", "")
        name = source.get("name", username)
        print(f"[Telegram] Scraping {name} (@{username})")

        tg_url = f"https://t.me/s/{username}"
        content = self.fetch(tg_url)
        if not content:
            print(f"[Telegram] Failed to fetch @{username}")
            return []

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, "lxml")

        m3u_links = set()
        for a in soup.find_all("a"):
            href = a.get("href", "")
            if any(ext in href.lower() for ext in [".m3u", ".m3u8", ".txt"]):
                m3u_links.add(href)
            elif "t.me" in href and "m3u" in href.lower():
                m3u_links.add(href)

        messages = soup.find_all("div", class_="tgme_widget_message_text")
        for msg in messages:
            text = msg.get_text()
            for line in text.split("\n"):
                line = line.strip()
                if any(ext in line.lower() for ext in [".m3u", ".m3u8", ".txt"]) and line.startswith("http"):
                    m3u_links.add(line)

        print(f"[Telegram] Found {len(m3u_links)} M3U links from @{username}")

        all_items = []
        for link in m3u_links:
            items = self._process_m3u_link(link, name)
            all_items.extend(items)

        return all_items

    def _process_m3u_link(self, url: str, source_name: str) -> List[MediaItem]:
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
            is_tv = bool(group and any(kw in group.lower() for kw in ["series", "serie", "tv", "مسلسل"]))

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
                        streams=[StreamInfo(url=stream_url, quality=quality, source=f"telegram:{source_name}")],
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
                    streams=[StreamInfo(url=stream_url, quality=quality, source=f"telegram:{source_name}")],
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
                    streams=[StreamInfo(url=stream_url, quality=quality, source=f"telegram:{source_name}")],
                )
                results.append(item)

        return results

    def scrape_all(self) -> List[MediaItem]:
        all_items = []
        for source in self.sources:
            items = self.scrape_source(source)
            all_items.extend(items)
        return all_items
