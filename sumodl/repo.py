from datetime import datetime, timedelta
from pathlib import Path
import requests
import logging

from playwright.sync_api import sync_playwright, Playwright
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from typing import Tuple, Iterator
from sumodl.domain import (
    SumoFilm,
    Episode,
    STARTING_TOURNAMENT,
    TOURNAMENTS_PER_YEAR,
    MONTHS_PER_YEAR,
    TOURNAMENTS_PER_YEAR,
)

logger = logging.getLogger(__name__)


class NoEpisode(Exception):
    def __init__(self):
        super().__init__("Episode not available")


class BadEpisodeData(Exception):
    def __init__(self, section):
        super().__init__(f"The {section} of the episode couldn't be found")


class NHKSumoRepo:
    _BASE_URL = Path("https://www3.nhk.or.jp/nhkworld/en/tv/sumo/tournament")

    def __init__(self, debug=False):
        self._debug = debug

    # TODO: Can throw
    def get_film(self, episode) -> SumoFilm:
        url = self._BASE_URL / self._get_episode_url(episode)
        logging.debug(f"Finding episode at {url=}")

        with sync_playwright() as playwright:
            try:
                content_descriptor_url, content_thumbnail_url = (
                    self._get_episode_metadata(playwright, url)
                )
            except PlaywrightError as e:
                raise NoEpisode() from e
            except BadEpisodeData as e:
                raise NoEpisode() from e

        logging.debug(
            f"Finding episode info for {content_descriptor_url=} and {content_thumbnail_url=}"
        )
        return self._decode_film(content_descriptor_url, content_thumbnail_url)

    def _get_episode_url(self, episode: Episode) -> str:
        year = STARTING_TOURNAMENT.year + int(
            (episode.season_id - 1) / TOURNAMENTS_PER_YEAR
        )
        month = STARTING_TOURNAMENT.month
        month += (
            (MONTHS_PER_YEAR / TOURNAMENTS_PER_YEAR)
            * (episode.season_id - 1)
            % TOURNAMENTS_PER_YEAR
        )
        month = int(month)
        return f"{year}{month:02}/day{episode.episode}.html"

    # TODO: Can throw
    def _get_episode_metadata(self, playwright: Playwright, url) -> Tuple[str, str]:
        browser = playwright.firefox.launch(headless=not self._debug)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        page.goto(url, wait_until="load")

        # Account for a cookies consent box
        # Note: This is temperamental, maybe need to wait for longer
        try:
            page.wait_for_selector("button:has-text('Accept')", timeout=3000)
            page.click("button:has-text('Accept')")
        except PlaywrightTimeoutError:
            pass

        # Get the main video frame
        try:
            page.wait_for_selector("iframe", timeout=5000)
        except PlaywrightTimeoutError:
            raise BadEpisodeData("frame")
        for frame in page.frames:
            if "moviePlayer" in frame.name:
                break
        else:
            raise BadEpisodeData("frame")

        requests = []
        page.on("request", lambda req: requests.append(req))
        page.goto(frame.url, wait_until="networkidle")

        for video_request in requests:
            if "getMediaByParam" in video_request.url:
                break
        else:
            raise BadEpisodeData("media request")

        for thumb_request in requests:
            if "thumbnail" in thumb_request.url and ".jpg" in thumb_request.url:
                break
        else:
            raise BadEpisodeData("thumbnail")

        browser.close()

        return video_request.url, thumb_request.url

    # TODO: can throw
    def _decode_film(self, url: str, thumbnail_url: str) -> SumoFilm:
        response = requests.get(url).json()

        try:
            # Day 1 has a different format
            day = int(
                response["meta"][0]["title"].split("Day")[1].strip().split(" ")[0]
            )
        except ValueError:
            # Other days
            day = int(
                response["meta"][0]["title"].split("Day")[1].strip().split(":")[0]
            )

        publication_time = response["meta"][0]["publication_date"]
        start_time = datetime.strptime(publication_time, "%Y/%m/%d %H:%M:%S")

        tournament_start_time = start_time - timedelta(days=day - 1)

        return SumoFilm(
            season=f"{tournament_start_time.year} - {tournament_start_time.strftime('%B')}",
            episode=day,
            hd_video_url=response["meta"][0]["movie_url"]["mb_hd"],
            thumbnail_url=thumbnail_url,
        )


class ArkeRepo:
    _SUMO_SHOW_NAME = "Grand Sumo (1926-)"

    def __init__(self, path: Path):
        self._base_path = path

    def pull_episode(self, film_record: SumoFilm):
        show_dir = self._base_path / self._SUMO_SHOW_NAME

        cur_tornament_time = datetime.strptime(film_record.season, "%Y - %B").date()
        season_id = int((cur_tornament_time - STARTING_TOURNAMENT).days / 31) + 1
        season_dir = show_dir / f"Season {season_id:02}"
        Path.mkdir(season_dir, parents=True, exist_ok=True)

        # TODO: These are really domain things? (vid+thumb)
        thumbnail_path = season_dir / f"{film_record.episode:02}-thumb.jpg"
        if not thumbnail_path.exists():
            response = requests.get(film_record.thumbnail_url)
            if response.status_code == 200:
                with open(str(thumbnail_path), "wb") as f:
                    f.write(response.content)
            else:
                # TODO: Error logic
                pass

        from yt_dlp import YoutubeDL

        episode_path = season_dir / f"{film_record.episode:02}.mkv"
        if not episode_path.exists():
            ydl_opts = {
                "format": "bestvideo+bestaudio/best",
                "merge_output_format": "mkv",
                "outtmpl": str(episode_path),
            }
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download(film_record.hd_video_url)

    def get_episodes(self) -> Iterator[Episode]:
        for root, dirs, files in (self._base_path / self._SUMO_SHOW_NAME).walk():
            for file in files:
                if file.split(".")[-1] != "mkv":
                    continue

                yield Episode(
                    season_id=int(root.name.split(" ")[-1]),
                    episode=int(file.split(".")[0]),
                )
