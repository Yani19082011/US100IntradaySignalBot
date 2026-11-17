"""
Настройки на US100IntradaySignalBot. Всичко чувствително идва от Environment
Variables (Render) / .env (локално) - виж .env.example.
"""
import os

# --- Стратегия (17.11, избрана СЪЗНАТЕЛНО пред алтернативен по-силен на QQQ
# COMBO кандидат - виж README.md "ЗАЩО ТОЗИ СИГНАЛ, НЕ ПО-СИЛНИЯТ" за пълната
# причина: тази генерализира на SPY (cross-symbol тест), другата - не. НЕ
# променяй RSI_PERIOD/RSI_OVERSOLD/TARGET_PCT/STOP_PCT без нова 3-прозорец
# + cross-symbol проверка (виж qqq_intraday_finalize.py/qqq_stress_test*.py
# в Desktop/PennyStockScanner) - промяната прави резултата невалиден. ---
RSI_PERIOD = 18
RSI_OVERSOLD = 15.0
TARGET_PCT = 0.46     # изведен от mfe_pct 50-ти перцентил, прозорец 1 (17.11)
STOP_PCT = 0.63        # изведен от mae_pct 20-ти перцентил, прозорец 1 (17.11)
ROUND_TRIP_COST_PCT = float(os.environ.get("ROUND_TRIP_COST_PCT", "0.05"))  # ПРЕПОРЪЧВАМЕ да смениш с реалния си US100 CFD спред, виж README.md

# --- Инструмент - сигналът се следи на QQQ (Invesco QQQ Trust, прокси за
# Nasdaq-100 1:1), защото US100/NAS100 CFD няма исторически данни за
# backtesting и няма intraday бари в реално време през безплатен източник -
# СЪЩАТА логика като за дневния research. РЕАЛНАТА сделка се изпълнява от
# ТЕБ, ръчно, на твоя US100/NAS100 CFD инструмент при брокера - ботът САМО
# изпраща email алърти, НЕ изпълнява сделки автоматично. ---
PROXY_SYMBOL = os.environ.get("PROXY_SYMBOL", "QQQ")

# --- БЕЗ overnight - принудително затваряне преди края на търговската сесия,
# независимо дали TP/SL е ударен (потвърдено 17.11 - CFD swap/financing
# разход при 20x ливъридж + overnight gap риск). Сесия 09:30-16:00
# America/New_York (редовна NYSE/Nasdaq сесия). ---
MARKET_OPEN_HOUR_NY = 9
MARKET_OPEN_MINUTE_NY = 30
MARKET_CLOSE_HOUR_NY = 16
MARKET_CLOSE_MINUTE_NY = 0
FORCE_CLOSE_MINUTES_BEFORE_END = int(os.environ.get("FORCE_CLOSE_MINUTES_BEFORE_END", "5"))
# след тази граница НЕ се отварят НОВИ позиции (но вече отворени продължават
# да се следят до принудителното затваряне) - предпазна мярка, не е от самия
# backtest (който допуска вход по всяко време на деня), а разумно огранчение
# за живо изпълнение, за да няма вход минути преди принудително затваряне.
NO_NEW_ENTRIES_AFTER_MINUTES_BEFORE_END = int(os.environ.get("NO_NEW_ENTRIES_AFTER_MINUTES_BEFORE_END", "30"))

# --- Капитал / leverage (СЪЩИЯТ модел като Top100SignalBot, но тук е САМО 1
# инструмент - никога повече от 1 отворена позиция едновременно, затова няма
# нужда от деление между няколко сигнала). ---
TOTAL_CAPITAL_EUR = float(os.environ.get("TOTAL_CAPITAL_EUR", "2500"))
LEVERAGE = float(os.environ.get("LEVERAGE", "20"))

# --- Данни - Alpaca Market Data API v2 (IEX feed, безплатен), 5-минутни
# бари - СЪЩИЯТ работещ ключ, който вече е в Desktop/PennyStockScanner/.env
# (paper акаунт) - копирай го и тук. ---
ALPACA_API_KEY = os.environ.get("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY", "")
ALPACA_DATA_URL = os.environ.get("ALPACA_DATA_URL", "https://data.alpaca.markets")

# --- Email алърти (СЪЩИЯТ Resend модел като другите ботове) ---
ALERT_EMAIL_ENABLED = os.environ.get("ALERT_EMAIL_ENABLED", "false").lower() == "true"
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")
ALERT_EMAIL_TO = os.environ.get("ALERT_EMAIL_TO", "yani.kolev2011@gmail.com")

# --- Колко често да проверява ПРЕЗ деня (минути) - за разлика от дневните
# ботове (веднъж на ден), тук стратегията е INTRADAY (5-мин бари), затова
# проверява на кратки интервали ПРЕЗ цялата сесия, не само накрая. ---
CHECK_INTERVAL_MINUTES = int(os.environ.get("CHECK_INTERVAL_MINUTES", "2"))
SOFIA_TZ = "Europe/Sofia"
NY_TZ = "America/New_York"

# --- Persistent state на отворената позиция (макс 1 наведнъж) - ЗАБЕЛЕЖКА:
# на Render free tier локалният диск се трие при всеки redeploy (същият
# познат проблем като при другите ботове). ---
POSITION_STATE_FILE = os.environ.get("POSITION_STATE_FILE", "open_position.json")
# пази коя дата е била последно "вече търгувана" (само 1 вход на ден,
# СЪЩАТА конвенция като research-а - само ПЪРВИЯТ сигнал на деня се брои)
LAST_TRADED_DATE_FILE = os.environ.get("LAST_TRADED_DATE_FILE", "last_traded_date.txt")

PORT = int(os.environ.get("PORT", "10000"))
