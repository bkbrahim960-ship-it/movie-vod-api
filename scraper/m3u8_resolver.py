import re
import time
import random
from typing import Optional, List, Dict
import httpx


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "DNT": "1",
}

CDN_FALLBACK = {
    "v1": "neonhorizonworkshops.com",
    "v2": "cloudnestra.com",
    "v3": "neonhorizonworkshops.com",
    "v4": "neonhorizonworkshops.com",
    "v5": "cloudnestra.com",
    "v6": "cloudnestra.com",
    "v7": "neonhorizonworkshops.com",
    "v8": "neonhorizonworkshops.com",
}


class M3U8Resolver:
    def __init__(self):
        self.client = httpx.Client(
            headers=HEADERS,
            follow_redirects=True,
            timeout=20,
            verify=False,
        )

    def _get(self, url: str, referer: Optional[str] = None) -> Optional[str]:
        headers = {}
        if referer:
            headers["Referer"] = referer
        time.sleep(random.uniform(0.5, 1.0))
        try:
            resp = self.client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.text
        except Exception as e:
            print(f"[M3U8Resolver] GET failed {url}: {e}")
        return None

    def resolve(self, media_type: str, tmdb_id: int) -> List[str]:
        try:
            return self._resolve_chain(media_type, str(tmdb_id))
        except Exception as e:
            print(f"[M3U8Resolver] Chain failed for {media_type}/{tmdb_id}: {e}")
            return []

    def _resolve_chain(self, media_type: str, media_id: str) -> List[str]:
        embed_url = f"https://vidsrc.to/embed/{media_type}/{media_id}"
        html = self._get(embed_url)
        if not html:
            return []

        vsembed_src = self._extract(r'src=["\']([^"\']*vsembed\.ru[^"\']*)["\']', html)
        if not vsembed_src:
            vsembed_src = self._extract(r'src=["\']([^"\']*embed[^"\']*v[^"\']*)["\']', html)
        if not vsembed_src:
            return []
        if vsembed_src.startswith("//"):
            vsembed_src = "https:" + vsembed_src

        vshtml = self._get(vsembed_src, referer=embed_url)
        if not vshtml:
            return []

        hashes = re.findall(r'data-hash=["\']([A-Za-z0-9+/=_\-]+)["\']', vshtml)
        if not hashes:
            return []

        all_streams = []
        for h in hashes[:3]:
            streams = self._process_hash(h, vsembed_src)
            all_streams.extend(streams)

        return list(set(all_streams))

    def _process_hash(self, rcp_hash: str, referer: str) -> List[str]:
        rcp_url = f"https://cloudnestra.com/rcp/{rcp_hash}"
        rcp_html = self._get(rcp_url, referer=referer)
        if not rcp_html:
            return []

        prorcp = self._extract(r"['\"]\/prorcp\/([A-Za-z0-9+/=_\-]+)['\"]", rcp_html)
        if not prorcp:
            return []

        prorcp_url = f"https://cloudnestra.com/prorcp/{prorcp}"
        prhtml = self._get(prorcp_url, referer=rcp_url)
        if not prhtml:
            return []

        file_match = self._extract(r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', prhtml)
        if not file_match:
            file_match = self._extract(r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"', prhtml)
        if not file_match:
            return []

        raw_urls = [u.strip() for u in file_match.split(" or ")]
        results = []
        for raw in raw_urls:
            resolved = raw
            for k, v in CDN_FALLBACK.items():
                resolved = resolved.replace("{" + k + "}", v)
            if "{v" not in resolved and resolved.startswith("http"):
                results.append(resolved)

        return results

    @staticmethod
    def _extract(pattern: str, text: str, group: int = 1) -> Optional[str]:
        m = re.search(pattern, text)
        return m.group(group) if m else None
