import os
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from database import Database
from models import MediaItem
from scraper.tmdb import TMDBClient
from updater import Updater

app = FastAPI(
    title="Movie VOD API",
    description="M3U VOD scraper with TMDB metadata",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Database()
tmdb = TMDBClient()
updater = Updater(db, tmdb)


@app.on_event("startup")
async def startup():
    db.cleanup_orphans()
    updater.start()


@app.get("/")
async def root():
    return {"name": "Movie VOD API", "version": "1.0.0"}


@app.get("/api/health")
async def health():
    stats = db.get_stats()
    return {
        "status": "ok",
        "tmdb_configured": bool(tmdb.api_key),
        "stats": stats,
    }


@app.get("/api/movies")
async def get_movies(
    search: Optional[str] = Query(None),
    genre: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    items = db.get_media(media_type="movie", search=search, genre=genre, limit=limit, offset=offset)
    return {"success": True, "data": items, "total": len(items)}


@app.get("/api/series")
async def get_series(
    search: Optional[str] = Query(None),
    genre: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    items = db.get_media(media_type="tv", search=search, genre=genre, limit=limit, offset=offset)
    return {"success": True, "data": items, "total": len(items)}


@app.get("/api/media/{tmdb_id}")
async def get_media(tmdb_id: int, media_type: str = Query("movie")):
    item = db.get_media_by_id(tmdb_id, media_type)
    if not item:
        return {"success": False, "error": "Not found"}
    return {"success": True, "data": item}


@app.get("/api/streams")
async def get_all_streams():
    streams = db.get_all_streams()
    return {"success": True, "data": streams, "total": len(streams)}


@app.get("/api/stats")
async def get_stats():
    stats = db.get_stats()
    return {"success": True, "data": stats}


@app.post("/api/scrape")
async def trigger_scrape():
    try:
        updater._run_all()
        return {"success": True, "message": "Scrape cycle completed"}
    except Exception as e:
        return {"success": False, "error": str(e)}
