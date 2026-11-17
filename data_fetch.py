"""
5-минутни бари от Alpaca Market Data API v2 (IEX feed, безплатен) за ДНЕШНИЯ
ден - СЪЩАТА логика като load_intraday_alpaca в
Desktop/PennyStockScanner/intraday_strategy_search.py, опростена до само
"днешните бари до момента" (живо изпълнение, не изследване)."""
import logging

import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import config

log = logging.getLogger("data_fetch")


class AlpacaClient:
    def __init__(self):
        self.headers = {
            "APCA-API-KEY-ID": config.ALPACA_API_KEY,
            "APCA-API-SECRET-KEY": config.ALPACA_SECRET_KEY,
        }

    def get_today_intraday_bars(self, symbol: str) -> pd.DataFrame:
        """5-мин бари за symbol от началото на днешния ден (UTC) до сега -
        колони open/high/low/close/volume, индекс = America/New_York локално
        време (naive). Връща празен DataFrame при грешка (НЕ хвърля
        изключение)."""
        now_utc = datetime.now(timezone.utc)
        start_utc = now_utc - timedelta(hours=20)  # с резерва - ще филтрираме до редовна сесия по-долу
        url = f"{config.ALPACA_DATA_URL}/v2/stocks/{symbol}/bars"
        params = {
            "timeframe": "5Min",
            "start": start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "limit": 500,
            "adjustment": "all",
            "feed": "iex",
        }
        try:
            r = requests.get(url, headers=self.headers, params=params, timeout=15)
            r.raise_for_status()
            bars = r.json().get("bars", [])
        except Exception as e:
            log.warning("Alpaca intraday бари fail за %s: %s", symbol, e)
            return pd.DataFrame()
        if not bars:
            return pd.DataFrame()
        df = pd.DataFrame(bars)
        df["t"] = pd.to_datetime(df["t"], utc=True)
        df = df.set_index("t").rename(
            columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}
        )
        keep = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
        df = df[keep].dropna()
        if df.empty:
            return df
        try:
            local_idx = df.index.tz_convert(config.NY_TZ)
            mask = (
                (local_idx.time >= pd.Timestamp(f"{config.MARKET_OPEN_HOUR_NY:02d}:{config.MARKET_OPEN_MINUTE_NY:02d}").time())
                & (local_idx.time < pd.Timestamp(f"{config.MARKET_CLOSE_HOUR_NY:02d}:{config.MARKET_CLOSE_MINUTE_NY:02d}").time())
            )
            df = df[mask]
            df.index = local_idx[mask].tz_localize(None)
        except Exception as e:
            log.warning("Филтриране на сесия се провали: %s", e)
            return pd.DataFrame()
        # само ДНЕШНИТЕ бари (America/New_York календарна дата)
        today_ny = datetime.now(timezone.utc).astimezone(ZoneInfo(config.NY_TZ)).date()
        df = df[df.index.date == today_ny]
        return df.sort_index()
