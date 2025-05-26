from bs4 import BeautifulSoup
import asyncio
from datetime import datetime, timedelta, date
from dataclasses import dataclass
from pathlib import Path
import requests

from playwright.sync_api import sync_playwright, Playwright
from typing import Tuple

_STARTING_TOURNAMENT = date(year = 2025, month=5, day=1)
#TODO: Set this back
_EPISODES_PER_SEASON = 2

@dataclass(frozen=True)
class Episode:
    season_id: int
    episode: int

from typing import Iterator


@dataclass(frozen=True)
class SumoFilm:
    season: str
    episode: int
    hd_video_url : str
    thumbnail_url: str

class NHKSumoRepo():
    _BASE_URL = Path("https://www3.nhk.or.jp/nhkworld/en/tv/sumo/tournament")
    def __init__(self, debug=False):
        self._debug = debug

    def get_film(self, episode) -> SumoFilm:
        url = self._BASE_URL / self._get_episode_url(episode)

        with sync_playwright() as playwright:
            content_descriptor_url, content_thumbnail_url = self._get_episode_metadata(playwright, url)

        #content_descriptor_url = "https://api01-platform.stream.co.jp/apiservice/getMediaByParam/?token=NDc4NThCNTkxQzFCNkQ3ODA4NjcwNTZGREYzNURBNzM=&type=json&optional_id=nw_vod_v_en_2061_781_20250512013000_01_1746983000&active_flg=1"
        #content_thumbnail_url = "https://ssl-cache.stream.ne.jp/www50/eqj833muwr/jmc_pub/thumbnail/00162/e5332ea600a84ee388fabbc4a5f92f85_26_13.jpg"
        return self._decode_film(content_descriptor_url, content_thumbnail_url)

    
    def _get_episode_url(self, episode: Episode) -> str:
        year = _STARTING_TOURNAMENT.year + int((episode.season_id-1)/_TOURNAMENTS_PER_YEAR)
        month  = _STARTING_TOURNAMENT.month + (episode.season_id-1)%_TOURNAMENTS_PER_YEAR
        return f"{year}{month:02}/day{episode.episode}.html"

    #TODO: Can throw
    def _get_episode_metadata(self, playwright: Playwright, url) -> Tuple[str, str]:
        browser = playwright.chromium.launch(headless=not debug)
        page = browser.new_page()

        page.goto(url, wait_until="networkidle")

        # Get the main video frame
        for frame in page.frames:
            if "moviePlayer" in frame.name:
                break
        else:
            #TODO: Error
            print("Couldn\'t find frame")
            return

        requests = []
        page.on("request", lambda req: requests.append(req))
        page.goto(frame.url, wait_until="networkidle")

        for video_request in requests:
            if "getMediaByParam" in video_request.url:
                break
        else:
            #TODO: error
            print("Couldn\'t find media request")
            return

        for thumb_request in requests:
            if "thumbnail" in thumb_request.url and ".jpg" in thumb_request.url:
                break
        else:
            #TODO: error
            print("Couldn\'t find thumbnail")
            return

        browser.close()

        return video_request.url, thumb_request.url

    #TODO: can throw
    def _decode_film(self, url: str, thumbnail_url: str) -> SumoFilm:
        response = requests.get(url).json()

        try:
            # Day 1 has a different format
            day = int(response['meta'][0]['title'].split("Day")[1].strip().split(" ")[0])
        except ValueError:
            # Other days
            day = int(response['meta'][0]['title'].split("Day")[1].strip().split(":")[0])

        publication_time = response['meta'][0]['publication_date']
        start_time = datetime.strptime(publication_time, '%Y/%m/%d %H:%M:%S')

        tournament_start_time = start_time - timedelta(days=day - 1)

        return SumoFilm(
            season = f"{tournament_start_time.year} - {tournament_start_time.strftime("%B")}",
            episode = day,
            hd_video_url = response['meta'][0]['movie_url']["mb_hd"],
            thumbnail_url = thumbnail_url
        )


class ArkeRepo():
    _SUMO_SHOW_NAME = "Grand Sumo (1926 - )"

    def __init__(self, path: Path):
        self._base_path = path

    def pull_episode(self, film_record : SumoFilm):
        show_dir = self._base_path / self._SUMO_SHOW_NAME

        cur_tornament_time = datetime.strptime(film_record.season, "%Y - %B").date()
        season_id = int((cur_tornament_time - _STARTING_TOURNAMENT).days/31) + 1
        season_dir = show_dir / f"Season {season_id:02}" 
        Path.mkdir(season_dir, parents=True, exist_ok=True)
    
        #TODO: These are really domain things? (vid+thumb)
        thumbnail_path = season_dir/ f"{film_record.episode:02}-thumb.jpg"
        if not thumbnail_path.exists():
            response = requests.get(film_record.thumbnail_url)
            if response.status_code == 200:
                with open(str(thumbnail_path), 'wb') as f:
                    f.write(response.content)
            else:
                #TODO: Error logic
                pass

        from yt_dlp import YoutubeDL
        episode_path = season_dir/ f"{film_record.episode:02}.mkv"
        if not episode_path.exists():
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mkv',
                'outtmpl': str(episode_path)
            }
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download(film_record.hd_video_url)

    def get_episodes(self) -> Iterator[Episode]:
        for root, dirs, files in (self._base_path/self._SUMO_SHOW_NAME).walk():
            for file in files:
                if file.split(".")[-1] != "mkv":
                    continue

                yield Episode(
                    season_id = int(root.name.split(" ")[-1]),
                    episode = int(file.split(".")[0])
                    )


#TODO: This is wrong
#   * the season id could be wrong, (div 31 not months) and the season starts on the 'first or second sunday)
#   *  Just because we're in one season doesn't mean all the episodes are available yet
def get_current_season_episodes(cur_time: datetime) -> Iterator[Episode]:
    season_id = int((cur_time.date() - _STARTING_TOURNAMENT).days/31) + 1
    for episode_id in range(1, _EPISODES_PER_SEASON+1):
        yield Episode(season_id = season_id, episode = episode_id)


def update_episodes(arke: ArkeRepo, nhk: NHKRepo):
    available_episodes = set(arke.get_episodes())
    possible_episodes = set(get_current_season_episodes(datetime.now()))
    unfound_episodes = possible_episodes - available_episodes 

    # You could do this async, we're just not for simplicity
    for episode in unfound_episodes:
        film = nhk.get_film(episode)
        arke.pull_episode(film)

if __name__ == "__main__":
  
    BASE_ON_DISK_DIRECTORY = Path("sftp://sean@192.168.1.199:22/tmp")
    BASE_ON_DISK_DIRECTORY = Path("/tmp")

    arke = ArkeRepo(BASE_ON_DISK_DIRECTORY)
    nhk = NHKSumoRepo()

    update_episodes(arke, nhk)
