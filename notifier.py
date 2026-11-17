"""Email алърти през Resend - СЪЩИЯТ модел като другите ботове (onboarding@resend.dev
подател, за да избегнем domain-verification грешка)."""
import logging

import requests

import config

log = logging.getLogger("notifier")
RESEND_API_URL = "https://api.resend.com/emails"


def send_email(subject: str, body: str) -> bool:
    if not config.ALERT_EMAIL_ENABLED:
        log.info("ALERT_EMAIL_ENABLED=false - пропускам (виж лога): %s", subject)
        return False
    if not (config.RESEND_API_KEY and config.ALERT_EMAIL_TO):
        log.warning("RESEND_API_KEY или ALERT_EMAIL_TO липсват - email пропуснат.")
        return False
    try:
        resp = requests.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {config.RESEND_API_KEY}", "Content-Type": "application/json"},
            json={"from": config.RESEND_FROM_EMAIL, "to": [config.ALERT_EMAIL_TO], "subject": subject, "text": body},
            timeout=15,
        )
        if resp.status_code >= 300:
            log.error("Resend отказа (%s): %s", resp.status_code, resp.text)
            return False
        log.info("Email изпратен до %s: %s", config.ALERT_EMAIL_TO, subject)
        return True
    except Exception as e:
        log.error("Resend изпращането се провали: %s", e)
        return False


def format_entry_alert(entry_price: float, target_price: float, stop_price: float, sizing: dict) -> tuple:
    subject = f"[US100IntradaySignalBot] ВХОД СИГНАЛ @ QQQ ${entry_price:.2f}"
    body = (
        f"Сигнал: rsi_bounce_period18_oversold15.0 (RSI({config.RSI_PERIOD}) отскок над {config.RSI_OVERSOLD:g} прага)\n\n"
        f"ВАЖНО: ботът следи QQQ (прокси за US100/NAS100, 1:1 с Nasdaq-100) - "
        f"сделката трябва да отвориш РЪЧНО на твоя US100/NAS100 CFD при брокера, "
        f"ботът НЕ изпълнява нищо автоматично.\n\n"
        f"QQQ референтна цена: ${entry_price:.2f}\n"
        f"Take-profit (+{config.TARGET_PCT:g}%): ${target_price:.2f} (на QQQ скàла - приложи същия %% към твоята US100 цена)\n"
        f"Stop-loss (-{config.STOP_PCT:g}%): ${stop_price:.2f} (на QQQ скàла - приложи същия %% към твоята US100 цена)\n"
        f"Хоризонт: БЕЗ overnight - принудително затваряне до края на днешната сесия\n\n"
        f"Margin ({sizing['margin_eur']} EUR капитал): {sizing['margin_eur']} EUR\n"
        f"Notional (x{config.LEVERAGE:g} leverage): {sizing['notional_eur']} EUR\n"
        f"При +{config.TARGET_PCT:g}%: +{sizing['potential_gain_eur']} EUR\n"
        f"При -{config.STOP_PCT:g}%: -{sizing['potential_loss_eur']} EUR\n\n"
        f"ЧЕСТНО (изследователски контекст, не финансов съвет): тази стратегия е "
        f"ИЗВЕДЕНА от backtest (17.11.2026) с win_rate ~62-70%% срещу ~52-56%% baseline, "
        f"генерализира на SPY (различен инструмент), но formalniят hit_rate_target "
        f"significance тест (p=0.48-0.74) НЕ достига статистическа значимост при текущото n. "
        f"Разходната оценка ({config.ROUND_TRIP_COST_PCT:g}%% round-trip) е НЕПРОВЕРЕНА placeholder "
        f"за US100 CFD спреда - провери си реалния спред при брокера.\n"
    )
    return subject, body


def format_exit_alert(result: dict, sizing: dict) -> tuple:
    reason_bg = {"target": "TAKE-PROFIT ПОПАДЕНИЕ", "stop": "STOP-LOSS", "time": "ПРИНУДИТЕЛНО ЗАТВАРЯНЕ (край на сесията, без overnight)"}
    pnl_eur = round(sizing["notional_eur"] * result["pnl_pct"] / 100, 2)
    subject = f"[US100IntradaySignalBot] ИЗХОД: {reason_bg.get(result['reason'], result['reason'])} ({result['pnl_pct']:+.2f}%)"
    body = (
        f"Причина: {reason_bg.get(result['reason'], result['reason'])}\n"
        f"QQQ изходна (референтна) цена: ${result['exit_price']:.2f}\n"
        f"P&L на цената (net of {config.ROUND_TRIP_COST_PCT:g}% cost оценка): {result['pnl_pct']:+.2f}%\n"
        f"P&L в EUR (на notional {sizing['notional_eur']} EUR): {pnl_eur:+.2f} EUR\n\n"
        f"Затвори/провери съответната си US100/NAS100 CFD позиция при брокера РЪЧНО.\n"
    )
    return subject, body
