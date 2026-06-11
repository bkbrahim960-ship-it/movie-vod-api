import threading
import time
from typing import List
from database import Database
from models import MediaItem
from scraper import GitHubM3UScraper, TelegramScraper, IPTVSitesScraper, CinemaOSScraper, VidsrcScraper, VidAPIScraper, TMDBClient

UPDATE_INTERVAL = 60


class Updater:
    def __init__(self, db: Database, tmdb: TMDBClient):
        self.db = db
        self.tmdb = tmdb
        self._thread = None
        self._running = False
        self._scrapers = []

    def _init_scrapers(self):
        self._scrapers = [
            CinemaOSScraper(self.tmdb),
            VidsrcScraper(self.tmdb),
            VidAPIScraper(self.tmdb),
            GitHubM3UScraper(self.tmdb),
            TelegramScraper(self.tmdb),
            IPTVSitesScraper(self.tmdb),
        ]

    def start(self):
        if self._running:
            return
        self._running = True
        self._init_scrapers()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("[Updater] Started background update loop (every 60s)")

    def stop(self):
        self._running = False
        print("[Updater] Stopped")

    def _run_loop(self):
        while self._running:
            try:
                self._run_all()
            except Exception as e:
                print(f"[Updater] Error in update cycle: {e}")
            time.sleep(UPDATE_INTERVAL)

    def _run_all(self):
        print("[Updater] Starting update cycle...")
        all_items = []
        for scraper in self._scrapers:
            try:
                items = scraper.scrape_all()
                all_items.extend(items)
                print(f"[Updater] {type(scraper).__name__}: {len(items)} items")
            except Exception as e:
                print(f"[Updater] {type(scraper).__name__} failed: {e}")

        saved = 0
        for item in all_items:
            if self.db.save_media(item):
                saved += 1

        self.db.cleanup_orphans()
        stats = self.db.get_stats()
        print(f"[Updater] Cycle complete: {saved} saved, {stats['total']} total, {stats['with_streams']} with streams")
