from datetime import datetime, date
from dataclasses import dataclass

from typing import Iterator

STARTING_TOURNAMENT = date(year=2025, month=5, day=1)
EPISODES_PER_SEASON = 15
TOURNAMENTS_PER_YEAR = 6
MONTHS_PER_YEAR = 12


@dataclass(frozen=True)
class Episode:
    season_id: int
    episode: int


@dataclass(frozen=True)
class SumoFilm:
    season: str
    episode: int
    hd_video_url: str
    thumbnail_url: str


# TODO: This is wrong
#   * the season id could be wrong, (div 31 not months) and the season starts on the 'first or second Sunday)
#   *  Just because we're in one season doesn't mean all the episodes are available yet
def get_current_season_episodes(cur_time: datetime) -> Iterator[Episode]:
    season_id = int((cur_time.date() - STARTING_TOURNAMENT).days / 31) 
    season_id /= MONTHS_PER_YEAR/TOURNAMENTS_PER_YEAR
    season_id += 1
    season_id = int(season_id)

    for episode_id in range(1, EPISODES_PER_SEASON + 1):
        yield Episode(season_id=season_id, episode=episode_id)
