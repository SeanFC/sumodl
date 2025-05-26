from dotenv import load_dotenv
import os
from sumodl.repo import ArkeRepo, NHKSumoRepo
from sumodl.services import update_episodes
from pathlib import Path

if __name__ == "__main__":
    load_dotenv()

    media_directory = os.getenv('MEDIA_DIRECTORY')
  
    arke = ArkeRepo(Path(media_directory))
    nhk = NHKSumoRepo()

    update_episodes(arke, nhk)
