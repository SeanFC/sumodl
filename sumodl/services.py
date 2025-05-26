from datetime import datetime

import logging

from sumodl.repo import ArkeRepo, NHKSumoRepo
from sumodl.domain import get_current_season_episodes

logger = logging.getLogger(__name__)


def update_episodes(arke: ArkeRepo, nhk: NHKSumoRepo):
    logger.info("Updating available episodes")

    available_episodes = set(arke.get_episodes())
    possible_episodes = set(get_current_season_episodes(datetime.now()))
    unfound_episodes = possible_episodes - available_episodes

    logger.info(f"Found {len(unfound_episodes)} new possible episodes")

    # You could do this async, we're just not for simplicity
    for episode in unfound_episodes:
        logger.info(f"Attemping to pull S{episode.season_id}-E{episode.episode}")
        film = nhk.get_film(episode)
        arke.pull_episode(film)
        logger.info(f"Successfully pulled S{episode.season_id}-E{episode.episode}")
