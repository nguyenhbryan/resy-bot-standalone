import argparse
import json
from resy_bot.logging_config import logging

from resy_bot.models import ResyConfig, TimedReservationRequest
from resy_bot.manager import ResyManager

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


def check_slots(resy_config_path: str, reservation_config_path: str) -> str:
    logger.info("Checking slots")

    with open(resy_config_path, "r") as f:
        config_data = json.load(f)

    with open(reservation_config_path, "r") as f:
        reservation_data = json.load(f)

    config = ResyConfig(**config_data)
    manager = ResyManager.build(config)

    timed_request = TimedReservationRequest(**reservation_data)

    slots = manager.checkSlots(timed_request.reservation_request)
    for slot in slots:
        print(f"Slot time: {slot.date.start}, type: {slot.config.type}")
    if not slots:
        print("No slots today")
    


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="ResyBot",
        description="Wait until reservation drop time and make one",
    )

    parser.add_argument("resy_config_path")
    parser.add_argument("reservation_config_path")

    args = parser.parse_args()

    check_slots(args.resy_config_path, args.reservation_config_path)
