"""
Живата стратегия: rsi_bounce_period18_oversold15.0 (виж
Desktop/PennyStockScanner/intraday_strategy_search.py, sig_rsi_bounce) +
target/stop exit логика, СЪЩИЯТ ред на проверка като simulate_trade_ts в
qqq_intraday_finalize.py (stop се проверява ПЪРВО при same-bar засичане на
двете - консервативно)."""
import numpy as np
import pandas as pd

import config


def rsi_bounce_signal(intraday_df: pd.DataFrame, period: int = config.RSI_PERIOD, oversold: float = config.RSI_OVERSOLD) -> bool:
    """True, ако ПОСЛЕДНИЯТ (най-новия завършен) бар на intraday_df отговаря
    на rsi_bounce: RSI(period) излиза над oversold прага нагоре, след като е
    бил под него - отскок от свръхпродаденост в рамките на деня. Идентична
    логика на sig_rsi_bounce от research кода, но тук проверяваме само
    ПОСЛЕДНИЯ бар (живо изпълнение), не цялата серия наведнъж."""
    n = len(intraday_df)
    if n <= period + 2:
        return False
    close = intraday_df["close"]
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    was_oversold = rsi.shift(1) < oversold
    if pd.isna(was_oversold.iloc[-1]) or pd.isna(rsi.iloc[-1]):
        return False
    return bool(rsi.iloc[-1] >= oversold and was_oversold.iloc[-1])


def position_sizing() -> dict:
    """Само 1 инструмент, никога повече от 1 отворена позиция едновременно -
    затова ВИНАГИ пълният капитал (за разлика от Top100SignalBot, където се
    дели между няколко едновременни сигнала)."""
    margin_eur = config.TOTAL_CAPITAL_EUR
    notional_eur = margin_eur * config.LEVERAGE
    return {
        "margin_eur": round(margin_eur, 2),
        "notional_eur": round(notional_eur, 2),
        "potential_gain_eur": round(notional_eur * config.TARGET_PCT / 100, 2),
        "potential_loss_eur": round(notional_eur * config.STOP_PCT / 100, 2),
    }


def check_exit(position: dict, latest_bar: pd.Series, force_close: bool) -> dict:
    """Проверява ОТВОРЕНАТА позиция срещу последния бар. Връща
    {"closed": bool, "reason": "target"|"stop"|"time", "exit_price": float,
    "pnl_pct": float} - или {"closed": False}. РЕД: stop се проверява ПЪРВО
    (консервативно, ако и target, и stop са докоснати в СЪЩИЯ бар).
    force_close=True означава "sредата наближава края на сесията - затвори
    на последната цена независимо от TP/SL" (БЕЗ overnight - потвърдено
    17.11)."""
    stop_price = position["stop_price"]
    target_price = position["target_price"]
    if latest_bar["low"] <= stop_price:
        pnl_pct = -config.STOP_PCT - config.ROUND_TRIP_COST_PCT
        return {"closed": True, "reason": "stop", "exit_price": stop_price, "pnl_pct": round(pnl_pct, 3)}
    if latest_bar["high"] >= target_price:
        pnl_pct = config.TARGET_PCT - config.ROUND_TRIP_COST_PCT
        return {"closed": True, "reason": "target", "exit_price": target_price, "pnl_pct": round(pnl_pct, 3)}
    if force_close:
        exit_price = float(latest_bar["close"])
        raw_pnl = (exit_price - position["entry_price"]) / position["entry_price"] * 100
        pnl_pct = raw_pnl - config.ROUND_TRIP_COST_PCT
        return {"closed": True, "reason": "time", "exit_price": exit_price, "pnl_pct": round(pnl_pct, 3)}
    return {"closed": False}
