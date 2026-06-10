from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class StreamInfo(BaseModel):
    url: str
    quality: Optional[str] = None
    source: str = "unknown"
    language: Optional[str] = None


class MediaItem(BaseModel):
    tmdb_id: int
    title: str
    title_ar: Optional[str] = None
    year: Optional[int] = None
    overview: Optional[str] = None
    poster: Optional[str] = None
    backdrop: Optional[str] = None
    genres: List[str] = []
    rating: Optional[float] = None
    media_type: str = "movie"
    streams: List[StreamInfo] = []
    updated_at: Optional[str] = None
    created_at: Optional[str] = None
