from datetime import datetime

from sumodl.repo import ArkeRepo, NHKSumoRepo
from sumodl.domain import get_current_season_episodes

def update_episodes(arke: ArkeRepo, nhk: NHKSumoRepo):
    available_episodes = set(arke.get_episodes())
    possible_episodes = set(get_current_season_episodes(datetime.now()))
    unfound_episodes = possible_episodes - available_episodes 

    # You could do this async, we're just not for simplicity
    for episode in unfound_episodes:
        film = nhk.get_film(episode)
        arke.pull_episode(film)
