import argparse
import json
from resy_bot.logging_config import logging

from resy_bot.models import ResyConfig, TimedReservationRequest
from resy_bot.manager import ResyManager
import app.services.reservation_service as reservation_service

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


def parse_json(resy_config_path: str, reservation_config_path: str) -> dict:
        with open(resy_config_path, "r") as f:
            config_data = json.load(f)

        with open(reservation_config_path, "r") as f:
            reservation_data = json.load(f)
        
        return config_data, reservation_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="ResyBot",
        description="Wait until reservation drop time and make one",
    )

    parser.add_argument("resy_config_path")
    parser.add_argument("reservation_config_path")

    args = parser.parse_args()
    cfg, rcfg = parse_json(args.resy_config_path, args.reservation_config_path)

    reservation_service.reserve(cfg, rcfg)
