from bs4 import BeautifulSoup
import asyncio
from datetime import datetime, timedelta, date
from dataclasses import dataclass
from pathlib import Path
import requests
import logging

from playwright.sync_api import sync_playwright, Playwright
from typing import Tuple
from dotenv import load_dotenv
import os
from typing import Iterator
from sumodl.domain import SumoFilm, Episode, STARTING_TOURNAMENT, EPISODES_PER_SEASON , TOURNAMENTS_PER_YEAR

class NHKSumoRepo():
    _BASE_URL = Path("https://www3.nhk.or.jp/nhkworld/en/tv/sumo/tournament")
    def __init__(self, debug=False):
        self._debug = debug

    def get_film(self, episode) -> SumoFilm:
        url = self._BASE_URL / self._get_episode_url(episode)
        logging.debug(f"Finding episode at {url=}")

        with sync_playwright() as playwright:
            content_descriptor_url, content_thumbnail_url = self._get_episode_metadata(playwright, url)

        logging.debug(f"Finding episdoe info for {content_descriptor_url=} and {content_thumbnail_url=}")
        return self._decode_film(content_descriptor_url, content_thumbnail_url)

    
    def _get_episode_url(self, episode: Episode) -> str:
        year = STARTING_TOURNAMENT.year + int((episode.season_id-1)/TOURNAMENTS_PER_YEAR)
        month  = STARTING_TOURNAMENT.month + (episode.season_id-1)%TOURNAMENTS_PER_YEAR
        return f"{year}{month:02}/day{episode.episode}.html"

    #TODO: Can throw
    def _get_episode_metadata(self, playwright: Playwright, url) -> Tuple[str, str]:
        browser = playwright.chromium.launch(headless=not self._debug)
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
        season_id = int((cur_tornament_time - STARTING_TOURNAMENT).days/31) + 1
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
