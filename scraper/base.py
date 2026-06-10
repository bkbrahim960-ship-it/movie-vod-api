import httpx
import re
import time
import json
from typing import Optional, List, Tuple
from bs4 import BeautifulSoup


ROTATING_HEADERS = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
    },
]


class BaseScraper:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._header_index = 0

    def _get_headers(self) -> dict:
        headers = ROTATING_HEADERS[self._header_index % len(ROTATING_HEADERS)].copy()
        self._header_index += 1
        return headers

    def fetch(self, url: str, timeout: Optional[int] = None) -> Optional[str]:
        headers = self._get_headers()
        t = timeout or self.timeout
        for attempt in range(3):
            try:
                with httpx.Client(
                    headers=headers,
                    follow_redirects=True,
                    timeout=t,
                    verify=False,
                ) as client:
                    resp = client.get(url)
                    if resp.status_code == 200:
                        return resp.text
                    elif resp.status_code == 403:
                        time.sleep(1 * (attempt + 1))
                        continue
                    else:
                        return resp.text
            except Exception as e:
                if attempt == 2:
                    print(f"[Base] Failed to fetch {url}: {e}")
                    return None
                time.sleep(1)
        return None

    def fetch_bytes(self, url: str) -> Optional[bytes]:
        headers = self._get_headers()
        try:
            with httpx.Client(headers=headers, follow_redirects=True, timeout=self.timeout, verify=False) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    return resp.content
        except Exception as e:
            print(f"[Base] Failed to fetch bytes {url}: {e}")
        return None

    def parse_m3u(self, content: str) -> List[Tuple[str, str, Optional[str], Optional[str]]]:
        entries = []
        lines = content.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("#EXTINF:"):
                title_match = re.search(r'tvg-name="([^"]*)"', line)
                if not title_match:
                    title_match = re.search(r'#EXTINF:-?\d+.*?,(.+)$', line)
                title = title_match.group(1).strip() if title_match else None

                logo_match = re.search(r'tvg-logo="([^"]*)"', line)
                logo = logo_match.group(1) if logo_match else None

                group_match = re.search(r'group-title="([^"]*)"', line)
                group = group_match.group(1) if group_match else None

                if i + 1 < len(lines):
                    url = lines[i + 1].strip()
                    if url and not url.startswith("#") and url.startswith("http"):
                        entries.append((title, url, logo, group))
                i += 2
            else:
                i += 1
        return entries

    def extract_title_year(self, title: str) -> Tuple[str, Optional[int]]:
        if not title:
            return title, None
        year_match = re.search(r'[\(\[\{](19\d\d|20\d\d)[\)\]\}]', title)
        if year_match:
            year = int(year_match.group(1))
            title_clean = re.sub(r'\s*[\(\[\{](19\d\d|20\d\d)[\)\]\}]\s*', '', title).strip()
            return title_clean, year
        year_match = re.search(r'\b(19\d\d|20\d\d)\b', title)
        if year_match:
            year = int(year_match.group(1))
            title_clean = re.sub(r'\s*\b(19\d\d|20\d\d)\b\s*', '', title).strip()
            return title_clean, year
        return title.strip(), None

    def extract_quality(self, text: str) -> Optional[str]:
        if not text:
            return None
        text = text.lower()
        if "4k" in text or "2160" in text:
            return "4K"
        if "1080" in text or "full hd" in text or "fhd" in text:
            return "1080p"
        if "720" in text or "hd" in text or "hd ready" in text:
            return "720p"
        if "480" in text or "sd" in text:
            return "480p"
        if "360" in text:
            return "360p"
        return None
