"""
Персистентно състояние - локален JSON файл за отворената позиция (макс 1
наведнъж) + текстов файл за "последна търгувана дата" (само 1 вход на ден -
СЪЩАТА конвенция като research-а, само ПЪРВИЯТ сигнал на деня се брои).
ЗАБЕЛЕЖКА: на Render free tier дискът се трие при redeploy - същият познат
проблем като при другите ботове; добави Upstash Redis по-късно, ако искаш да
оцелее (виж README.md)."""
import json
import logging
import os

import config

log = logging.getLogger("positions_store")


def load_position() -> dict | None:
    if not os.path.exists(config.POSITION_STATE_FILE):
        return None
    try:
        with open(config.POSITION_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if data else None
    except Exception as e:
        log.error("Не можах да прочета %s: %s - тръгвам без отворена позиция.", config.POSITION_STATE_FILE, e)
        return None


def save_position(position: dict | None) -> None:
    try:
        with open(config.POSITION_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(position or {}, f, indent=2, default=str)
    except Exception as e:
        log.error("Не можах да запиша %s: %s", config.POSITION_STATE_FILE, e)


def load_last_traded_date() -> str | None:
    if not os.path.exists(config.LAST_TRADED_DATE_FILE):
        return None
    try:
        with open(config.LAST_TRADED_DATE_FILE, "r", encoding="utf-8") as f:
            val = f.read().strip()
            return val or None
    except Exception as e:
        log.error("Не можах да прочета %s: %s", config.LAST_TRADED_DATE_FILE, e)
        return None


def save_last_traded_date(date_str: str) -> None:
    try:
        with open(config.LAST_TRADED_DATE_FILE, "w", encoding="utf-8") as f:
            f.write(date_str)
    except Exception as e:
        log.error("Не можах да запиша %s: %s", config.LAST_TRADED_DATE_FILE, e)
