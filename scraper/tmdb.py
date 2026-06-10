import os
import re
import time
from typing import Optional, List, Tuple
from scraper.base import BaseScraper


class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE = "https://image.tmdb.org/t/p"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("TMDB_API_KEY", "")
        self.base = BaseScraper()

    def search_movie(self, title: str, year: Optional[int] = None) -> Optional[dict]:
        if not self.api_key:
            return None
        query = title
        params = f"&year={year}" if year else ""
        url = f"{self.BASE_URL}/search/movie?api_key={self.api_key}&query={query}&language=ar-SA{params}"
        data = self._fetch_json(url)
        if data and data.get("results"):
            return data["results"][0]
        url_en = f"{self.BASE_URL}/search/movie?api_key={self.api_key}&query={query}&language=en-US{params}"
        data_en = self._fetch_json(url_en)
        if data_en and data_en.get("results"):
            return data_en["results"][0]
        return None

    def search_tv(self, title: str, year: Optional[int] = None) -> Optional[dict]:
        if not self.api_key:
            return None
        query = title
        params = f"&first_air_date_year={year}" if year else ""
        url = f"{self.BASE_URL}/search/tv?api_key={self.api_key}&query={query}&language=ar-SA{params}"
        data = self._fetch_json(url)
        if data and data.get("results"):
            return data["results"][0]
        url_en = f"{self.BASE_URL}/search/tv?api_key={self.api_key}&query={query}&language=en-US{params}"
        data_en = self._fetch_json(url_en)
        if data_en and data_en.get("results"):
            return data_en["results"][0]
        return None

    def get_movie_details(self, tmdb_id: int) -> Optional[dict]:
        if not self.api_key:
            return None
        url = f"{self.BASE_URL}/movie/{tmdb_id}?api_key={self.api_key}&language=ar-SA"
        return self._fetch_json(url)

    def get_tv_details(self, tmdb_id: int) -> Optional[dict]:
        if not self.api_key:
            return None
        url = f"{self.BASE_URL}/tv/{tmdb_id}?api_key={self.api_key}&language=ar-SA"
        return self._fetch_json(url)

    def enrich_movie(self, tmdb_data: dict) -> dict:
        poster = None
        backdrop = None
        if tmdb_data.get("poster_path"):
            poster = f"{self.IMAGE_BASE}/w500{tmdb_data['poster_path']}"
        if tmdb_data.get("backdrop_path"):
            backdrop = f"{self.IMAGE_BASE}/w1280{tmdb_data['backdrop_path']}"

        return {
            "tmdb_id": tmdb_data.get("id"),
            "title": tmdb_data.get("title") or tmdb_data.get("name", ""),
            "title_ar": tmdb_data.get("title") if tmdb_data.get("original_language") == "ar" else None,
            "year": self._extract_year(tmdb_data),
            "overview": tmdb_data.get("overview"),
            "poster": poster,
            "backdrop": backdrop,
            "genres": [g["name"] for g in tmdb_data.get("genres", [])],
            "rating": tmdb_data.get("vote_average"),
        }

    def _extract_year(self, data: dict) -> Optional[int]:
        for key in ["release_date", "first_air_date"]:
            val = data.get(key)
            if val:
                m = re.search(r"\b(19\d\d|20\d\d)\b", str(val))
                if m:
                    return int(m.group(1))
        return None

    def _fetch_json(self, url: str) -> Optional[dict]:
        content = self.base.fetch(url)
        if content:
            try:
                import json
                return json.loads(content)
            except Exception:
                pass
        return None
