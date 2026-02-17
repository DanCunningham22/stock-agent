import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from models import Alert
from config import (
    TWILIO_SID, TWILIO_AUTH, TWILIO_FROM, ALERT_PHONE,
    ALERT_EMAIL, GMAIL_ADDRESS, GMAIL_APP_PASSWORD,
    ALERT_PRICE_DROP_PCT, ALERT_PRICE_SPIKE_PCT,
    ALERT_VOLUME_MULTIPLIER, ALERT_INSIDER_BUY_MIN,
    ALERT_SHORT_INTEREST_PCT,
)


def check_alerts(ticker, stock_data, price_data, insider_data):
    alerts = []
    now = datetime.now().isoformat()

    pct_1d = price_data.get("pct_change_1d")
    if pct_1d is not None and pct_1d <= -ALERT_PRICE_DROP_PCT:
        alerts.append(Alert(
            ticker=ticker, alert_type="PRICE_DROP", severity="high",
            message=f"{ticker} dropped {pct_1d:.1f}% today! Price: ${price_data.get('current', '?')}",
            data={"pct_change": pct_1d}, timestamp=now,
        ))

    if pct_1d is not None and pct_1d >= ALERT_PRICE_SPIKE_PCT:
        alerts.append(Alert(
            ticker=ticker, alert_type="PRICE_SPIKE", severity="high",
            message=f"{ticker} surged {pct_1d:.1f}% today! Price: ${price_data.get('current', '?')}",
            data={"pct_change": pct_1d}, timestamp=now,
        ))

    vol_ratio = price_data.get("volume_ratio")
    if vol_ratio is not None and vol_ratio >= ALERT_VOLUME_MULTIPLIER:
        alerts.append(Alert(
            ticker=ticker, alert_type="UNUSUAL_VOLUME", severity="medium",
            message=f"{ticker} volume is {vol_ratio:.1f}x normal!",
            data={"volume_ratio": vol_ratio}, timestamp=now,
        ))

    price = stock_data.get("price", 0)
    high_52w = stock_data.get("fifty_two_week_high", 0)
    if price and high_52w and price >= high_52w * 0.98:
        alerts.append(Alert(
            ticker=ticker, alert_type="52_WEEK_HIGH", severity="medium",
            message=f"{ticker} near 52-week high ${high_52w:.2f}! Current: ${price:.2f}",
            data={"price": price, "high_52w": high_52w}, timestamp=now,
        ))

    low_52w = stock_data.get("fifty_two_week_low", 0)
    if price and low_52w and price <= low_52w * 1.02:
        alerts.append(Alert(
            ticker=ticker, alert_type="52_WEEK_LOW", severity="high",
            message=f"{ticker} near 52-week LOW ${low_52w:.2f}! Current: ${price:.2f}. Potential buy?",
            data={"price": price, "low_52w": low_52w}, timestamp=now,
        ))

    short_pct = stock_data.get("short_percent_of_float")
    if short_pct is not None and short_pct * 100 >= ALERT_SHORT_INTEREST_PCT:
        alerts.append(Alert(
            ticker=ticker, alert_type="HIGH_SHORT_INTEREST", severity="medium",
            message=f"{ticker} has {short_pct*100:.1f}% short interest!",
            data={"short_percent": short_pct * 100}, timestamp=now,
        ))

    if isinstance(insider_data, list):
        for trade in insider_data:
            if isinstance(trade, dict) and "error" not in trade and "message" not in trade:
                trade_type = str(trade.get("type", "")).lower()
                value = trade.get("value", 0) or 0
                if ("buy" in trade_type or "purchase" in trade_type) and value >= ALERT_INSIDER_BUY_MIN:
                    alerts.append(Alert(
                        ticker=ticker, alert_type="INSIDER_BUY", severity="high",
                        message=f"INSIDER BUY {ticker}: {trade.get('insider','?')} bought ${value:,.0f}!",
                        data=trade, timestamp=now,
                    ))

    sma_50 = price_data.get("sma_50")
    sma_200 = price_data.get("sma_200")
    above_50 = price_data.get("above_sma_50")
    above_200 = price_data.get("above_sma_200")
    if sma_50 and sma_200:
        if sma_50 > sma_200 and above_50 and above_200:
            alerts.append(Alert(
                ticker=ticker, alert_type="GOLDEN_CROSS", severity="medium",
                message=f"{ticker} golden cross: 50d SMA > 200d SMA. Bullish.",
                data={"sma_50": sma_50, "sma_200": sma_200}, timestamp=now,
            ))
        elif sma_50 < sma_200 and not above_50 and not above_200:
            alerts.append(Alert(
                ticker=ticker, alert_type="DEATH_CROSS", severity="medium",
                message=f"{ticker} death cross: 50d SMA < 200d SMA. Bearish.",
                data={"sma_50": sma_50, "sma_200": sma_200}, timestamp=now,
            ))

    return alerts


def send_email_alert(alerts):
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD or not ALERT_EMAIL:
        print("  Email not configured - skipping")
        return False
    if not alerts:
        return False

    high = [a for a in alerts if a.severity == "high"]
    med = [a for a in alerts if a.severity == "medium"]

    body = "STOCK ALERT SUMMARY\n" + "=" * 40 + "\n\n"
    if high:
        body += "!! HIGH PRIORITY !!\n" + "-" * 20 + "\n"
        for a in high:
            body += f"\n[{a.alert_type}] {a.message}\n"
    if med:
        body += "\n\nMEDIUM PRIORITY\n" + "-" * 20 + "\n"
        for a in med:
            body += f"\n[{a.alert_type}] {a.message}\n"
    body += "\n\n---\nStock Research Agent - Automated Alert"

    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = ALERT_EMAIL
    msg["Subject"] = f"Stock Alert: {len(high)} high, {len(med)} medium priority"
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"  Email sent to {ALERT_EMAIL}")
        return True
    except Exception as e:
        print(f"  Email failed: {e}")
        return False


def send_text_alert(alerts):
    if not TWILIO_SID or not TWILIO_AUTH or not TWILIO_FROM or not ALERT_PHONE:
        print("  Twilio not configured - skipping")
        return False

    high = [a for a in alerts if a.severity == "high"]
    if not high:
        return False

    body = "STOCK ALERT:\n\n"
    for a in high[:5]:
        body += f"{a.message}\n\n"

    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_AUTH)
        message = client.messages.create(body=body[:1600], from_=TWILIO_FROM, to=ALERT_PHONE)
        print(f"  Text sent to {ALERT_PHONE}")
        return True
    except Exception as e:
        print(f"  Text failed: {e}")
        return False


def send_alerts(alerts):
    if not alerts:
        print("  No alerts triggered")
        return
    print(f"  {len(alerts)} alerts triggered!")
    send_email_alert(alerts)
    send_text_alert(alerts)
