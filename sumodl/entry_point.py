from dotenv import load_dotenv
import os
from sumodl.repo import ArkeRepo, NHKSumoRepo
from sumodl.services import update_episodes
from pathlib import Path
import argparse
import logging


def _setup_logging(log_level):
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def command_line():
    load_dotenv()

    media_directory = os.getenv("MEDIA_DIRECTORY")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--log",
        default="INFO",
        help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    args = parser.parse_args()

    _setup_logging(args.log)

    arke = ArkeRepo(Path(str(media_directory)))
    nhk = NHKSumoRepo()

    update_episodes(arke, nhk)
