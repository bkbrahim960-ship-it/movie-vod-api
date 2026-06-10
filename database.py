import sqlite3
import os
import json
from typing import Optional, List
from models import MediaItem, StreamInfo

DB_PATH = os.environ.get("DB_PATH", "vod_data.db")


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS media (
                tmdb_id INTEGER NOT NULL,
                media_type TEXT NOT NULL DEFAULT 'movie',
                title TEXT NOT NULL,
                title_ar TEXT,
                year INTEGER,
                overview TEXT,
                poster TEXT,
                backdrop TEXT,
                genres TEXT DEFAULT '[]',
                rating REAL,
                streams TEXT DEFAULT '[]',
                updated_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (tmdb_id, media_type)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                url TEXT,
                type TEXT,
                last_scraped TEXT,
                item_count INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

    def save_media(self, item: MediaItem) -> bool:
        conn = self._get_connection()
        try:
            existing = conn.execute(
                "SELECT streams FROM media WHERE tmdb_id=? AND media_type=?",
                (item.tmdb_id, item.media_type)
            ).fetchone()

            streams_json = json.dumps([s.model_dump() for s in item.streams], ensure_ascii=False)
            genres_json = json.dumps(item.genres, ensure_ascii=False)

            if existing:
                old_streams = json.loads(existing["streams"])
                all_urls = set()
                for s in old_streams:
                    all_urls.add(s["url"])
                for s in item.streams:
                    if s.url not in all_urls:
                        old_streams.append(s.model_dump())
                        all_urls.add(s.url)
                streams_json = json.dumps(old_streams, ensure_ascii=False)

            conn.execute("""
                INSERT OR REPLACE INTO media
                (tmdb_id, media_type, title, title_ar, year, overview, poster, backdrop, genres, rating, streams, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                item.tmdb_id, item.media_type, item.title, item.title_ar,
                item.year, item.overview, item.poster, item.backdrop,
                genres_json, item.rating, streams_json
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Error saving {item.title}: {e}")
            return False
        finally:
            conn.close()

    def get_media(self, media_type: Optional[str] = None, search: Optional[str] = None,
                  genre: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[MediaItem]:
        conn = self._get_connection()
        try:
            query = "SELECT * FROM media WHERE 1=1"
            params = []

            if media_type:
                query += " AND media_type=?"
                params.append(media_type)
            if search:
                query += " AND (title LIKE ? OR title_ar LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%"])
            if genre:
                query += " AND genres LIKE ?"
                params.append(f"%{genre}%")

            query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_media(r) for r in rows]
        finally:
            conn.close()

    def get_media_by_id(self, tmdb_id: int, media_type: str = "movie") -> Optional[MediaItem]:
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM media WHERE tmdb_id=? AND media_type=?",
                (tmdb_id, media_type)
            ).fetchone()
            return self._row_to_media(row) if row else None
        finally:
            conn.close()

    def get_all_streams(self) -> List[dict]:
        conn = self._get_connection()
        try:
            rows = conn.execute(
                "SELECT tmdb_id, title, media_type, streams FROM media WHERE streams != '[]'"
            ).fetchall()
            results = []
            for r in rows:
                streams = json.loads(r["streams"])
                for s in streams:
                    results.append({
                        "tmdb_id": r["tmdb_id"],
                        "title": r["title"],
                        "media_type": r["media_type"],
                        "url": s["url"],
                        "quality": s.get("quality"),
                        "source": s.get("source", "unknown"),
                    })
            return results
        finally:
            conn.close()

    def get_stats(self) -> dict:
        conn = self._get_connection()
        try:
            total = conn.execute("SELECT COUNT(*) FROM media").fetchone()[0]
            movies = conn.execute("SELECT COUNT(*) FROM media WHERE media_type='movie'").fetchone()[0]
            series = conn.execute("SELECT COUNT(*) FROM media WHERE media_type='tv'").fetchone()[0]
            with_streams = conn.execute("SELECT COUNT(*) FROM media WHERE streams != '[]'").fetchone()[0]
            return {
                "total": total,
                "movies": movies,
                "series": series,
                "with_streams": with_streams,
            }
        finally:
            conn.close()

    def cleanup_orphans(self):
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM media WHERE title IS NULL OR length(title) < 2")
            conn.execute("DELETE FROM media WHERE streams IS NULL OR streams = '[]'")
            conn.commit()
        except Exception as e:
            print(f"[DB] Cleanup error: {e}")
        finally:
            conn.close()

    def _row_to_media(self, row: sqlite3.Row) -> MediaItem:
        return MediaItem(
            tmdb_id=row["tmdb_id"],
            title=row["title"],
            title_ar=row.get("title_ar"),
            year=row.get("year"),
            overview=row.get("overview"),
            poster=row.get("poster"),
            backdrop=row.get("backdrop"),
            genres=json.loads(row["genres"]) if row.get("genres") else [],
            rating=row.get("rating"),
            media_type=row["media_type"],
            streams=[StreamInfo(**s) for s in json.loads(row["streams"])] if row.get("streams") else [],
            updated_at=row.get("updated_at"),
            created_at=row.get("created_at"),
        )
