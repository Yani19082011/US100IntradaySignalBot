"""
US100IntradaySignalBot - INTRADAY rsi_bounce_period18_oversold15.0 сигнален
бот за US100/NAS100 (следи QQQ като прокси). Flask health endpoint (за
Render + keep-alive pinger) + фонов цикъл, който проверява на всеки
config.CHECK_INTERVAL_MINUTES минути ПРЕЗ ЦЯЛАТА търговска сесия (за разлика
от дневните ботове Top100SignalBot/GoldSignalBot, които проверяват само
веднъж на ден - тук стратегията е intraday, трябва да следи target/stop и
принудителното затваряне в реално време, не само накрая на деня)."""
import logging
import threading
import time
from datetime import datetime, date

from flask import Flask
from zoneinfo import ZoneInfo

import config
import data_fetch
import strategy
import notifier
import positions_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("app")

app = Flask(__name__)
_status = {"last_check_at": None, "position_open": False, "market_open": False}
alpaca = data_fetch.AlpacaClient()


@app.route("/")
def health():
    return {"status": "ok", **_status}


@app.route("/test-email")
def test_email():
    sent = notifier.send_email("[US100IntradaySignalBot] ТЕСТ", "Тестов email - ако виждаш това, Resend настройката работи.")
    return {"sent": sent}


@app.route("/run-check-now")
def run_check_now():
    """Ръчно пускане на проверката веднага (за тестване), вместо да чакаш
    следващия автоматичен цикъл."""
    run_check()
    return {"status": "ok", **_status}


def _ny_now():
    return datetime.now(ZoneInfo(config.NY_TZ))


def _market_window(now_ny: datetime):
    """Връща (is_open, minutes_to_close) за редовната NYSE/Nasdaq сесия
    (09:30-16:00 America/New_York). НЕ отчита US празници (известно
    ограничение, виж README.md) - само уикенд + часови диапазон."""
    if now_ny.weekday() >= 5:
        return False, None
    open_t = now_ny.replace(hour=config.MARKET_OPEN_HOUR_NY, minute=config.MARKET_OPEN_MINUTE_NY, second=0, microsecond=0)
    close_t = now_ny.replace(hour=config.MARKET_CLOSE_HOUR_NY, minute=config.MARKET_CLOSE_MINUTE_NY, second=0, microsecond=0)
    if not (open_t <= now_ny < close_t):
        return False, None
    minutes_to_close = (close_t - now_ny).total_seconds() / 60.0
    return True, minutes_to_close


def run_check():
    now_ny = _ny_now()
    is_open, minutes_to_close = _market_window(now_ny)
    _status["market_open"] = is_open
    if not is_open:
        log.info("Пазарът е затворен (NY час: %s) - нищо за проверка.", now_ny.strftime("%H:%M"))
        _status["last_check_at"] = datetime.now(ZoneInfo(config.SOFIA_TZ)).isoformat()
        return

    today_str = now_ny.date().isoformat()
    force_close = minutes_to_close <= config.FORCE_CLOSE_MINUTES_BEFORE_END

    df = alpaca.get_today_intraday_bars(config.PROXY_SYMBOL)
    if df.empty:
        log.warning("Няма intraday бари за %s още - прескачам тази проверка.", config.PROXY_SYMBOL)
        _status["last_check_at"] = datetime.now(ZoneInfo(config.SOFIA_TZ)).isoformat()
        return
    latest_bar = df.iloc[-1]

    position = positions_store.load_position()
    if position:
        result = strategy.check_exit(position, latest_bar, force_close)
        if result["closed"]:
            sizing = position["sizing"]
            subject, body = notifier.format_exit_alert(result, sizing)
            notifier.send_email(subject, body)
            log.info("ИЗХОД: %s (%+.2f%%)", result["reason"], result["pnl_pct"])
            positions_store.save_position(None)
            position = None
        else:
            log.info("Позицията остава отворена (entry=$%.2f, TP=$%.2f, SL=$%.2f).",
                      position["entry_price"], position["target_price"], position["stop_price"])

    _status["position_open"] = position is not None

    if position is None:
        already_traded_today = positions_store.load_last_traded_date() == today_str
        entry_cutoff_ok = minutes_to_close > config.NO_NEW_ENTRIES_AFTER_MINUTES_BEFORE_END
        if not already_traded_today and entry_cutoff_ok:
            if strategy.rsi_bounce_signal(df):
                entry_price = float(latest_bar["close"])
                target_price = entry_price * (1 + config.TARGET_PCT / 100)
                stop_price = entry_price * (1 - config.STOP_PCT / 100)
                sizing = strategy.position_sizing()
                new_position = {
                    "symbol": config.PROXY_SYMBOL,
                    "entry_date": today_str,
                    "entry_time": now_ny.isoformat(),
                    "entry_price": entry_price,
                    "target_price": target_price,
                    "stop_price": stop_price,
                    "sizing": sizing,
                }
                positions_store.save_position(new_position)
                positions_store.save_last_traded_date(today_str)
                subject, body = notifier.format_entry_alert(entry_price, target_price, stop_price, sizing)
                notifier.send_email(subject, body)
                log.info("ВХОД СИГНАЛ @ $%.2f (margin %.2f EUR)", entry_price, sizing["margin_eur"])
                _status["position_open"] = True

    _status["last_check_at"] = datetime.now(ZoneInfo(config.SOFIA_TZ)).isoformat()


def _intraday_loop():
    while True:
        try:
            run_check()
        except Exception as e:
            log.exception("Проверката гръмна: %s", e)
        time.sleep(config.CHECK_INTERVAL_MINUTES * 60)


def _self_ping_loop():
    """Keep-alive за Render free tier - виж README.md за cron-job.org
    като външен pinger; това е ДОПЪЛНИТЕЛНА вътрешна предпазна мярка."""
    import requests
    while True:
        time.sleep(600)
        try:
            requests.get(f"http://127.0.0.1:{config.PORT}/", timeout=10)
        except Exception:
            pass


threading.Thread(target=_intraday_loop, daemon=True).start()
threading.Thread(target=_self_ping_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT)
