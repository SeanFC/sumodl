from bs4 import BeautifulSoup
import asyncio
from datetime import datetime, timedelta, date
from dataclasses import dataclass
from pathlib import Path
import requests

from playwright.sync_api import sync_playwright, Playwright
from typing import Tuple
from dotenv import load_dotenv
import os
from typing import Iterator

STARTING_TOURNAMENT = date(year = 2025, month=5, day=1)
#TODO: Set this back
EPISODES_PER_SEASON = 2
TOURNAMENTS_PER_YEAR = 6

@dataclass(frozen=True)
class Episode:
    season_id: int
    episode: int

@dataclass(frozen=True)
class SumoFilm:
    season: str
    episode: int
    hd_video_url : str
    thumbnail_url: str

#TODO: This is wrong
#   * the season id could be wrong, (div 31 not months) and the season starts on the 'first or second sunday)
#   *  Just because we're in one season doesn't mean all the episodes are available yet
def get_current_season_episodes(cur_time: datetime) -> Iterator[Episode]:
    season_id = int((cur_time.date() - STARTING_TOURNAMENT).days/31) + 1
    for episode_id in range(1, EPISODES_PER_SEASON+1):
        yield Episode(season_id = season_id, episode = episode_id)

