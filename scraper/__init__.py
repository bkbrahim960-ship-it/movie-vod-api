from scraper.github_m3u import GitHubM3UScraper
from scraper.telegram import TelegramScraper
from scraper.iptv_sites import IPTVSitesScraper
from scraper.cinemaos import CinemaOSScraper
from scraper.vidsrc import VidsrcScraper
from scraper.vidapi import VidAPIScraper
from scraper.base import BaseScraper
from scraper.tmdb import TMDBClient
from scraper.m3u8_resolver import M3U8Resolver

__all__ = [
    "GitHubM3UScraper",
    "TelegramScraper",
    "IPTVSitesScraper",
    "CinemaOSScraper",
    "VidsrcScraper",
    "VidAPIScraper",
    "BaseScraper",
    "TMDBClient",
]
