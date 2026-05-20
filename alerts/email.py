import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import pandas as pd
from config import GMAIL_USER, GMAIL_APP_PASS, ALERT_EMAIL


def _direction_color(direction: str) -> str:
    return {"bullish": "#16a34a", "bearish": "#dc2626"}.get(direction, "#6b7280")


def _confidence_badge(conf: str) -> str:
    colors = {"High": "#15803d", "Medium": "#b45309", "Low": "#6b7280"}
    color = colors.get(conf, "#6b7280")
    return f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;">{conf}</span>'


def _build_html(picks_df: pd.DataFrame, explanations: dict[str, str], date: str) -> str:
    rows_html = ""
    for _, row in picks_df.iterrows():
        ticker = row["ticker"]
        direction = row.get("direction", "—")
        score = row.get("score", 0)
        duration = row.get("duration", "—")
        confidence = row.get("confidence", "—")
        signals = "<br>".join(row.get("signals_triggered", []) or ["—"])
        explanation = explanations.get(ticker, "").replace("\n", "<br>")
        dir_color = _direction_color(direction)
        badge = _confidence_badge(confidence)

        rows_html += f"""
        <tr>
          <td style="padding:12px;font-weight:bold;font-size:16px;">{ticker}</td>
          <td style="padding:12px;color:{dir_color};font-weight:bold;">{direction.upper()}</td>
          <td style="padding:12px;font-size:18px;font-weight:bold;">{score}</td>
          <td style="padding:12px;">{badge}</td>
          <td style="padding:12px;color:#4b5563;">{duration}</td>
          <td style="padding:12px;color:#6b7280;font-size:13px;">{signals}</td>
        </tr>
        <tr>
          <td colspan="6" style="padding:4px 12px 16px 12px;color:#374151;background:#f9fafb;font-size:13px;">
            {explanation}
          </td>
        </tr>
        """

    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:900px;margin:0 auto;color:#111;">
      <h2 style="color:#1d4ed8;">Market Predictions — {date}</h2>
      <p style="color:#6b7280;">{len(picks_df)} setup(s) flagged with score ≥ 50. Predicted 5%+ move within listed window.</p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0"
             style="border-collapse:collapse;border:1px solid #e5e7eb;">
        <thead>
          <tr style="background:#1d4ed8;color:#fff;">
            <th style="padding:10px;text-align:left;">Ticker</th>
            <th style="padding:10px;text-align:left;">Direction</th>
            <th style="padding:10px;text-align:left;">Score</th>
            <th style="padding:10px;text-align:left;">Confidence</th>
            <th style="padding:10px;text-align:left;">Window</th>
            <th style="padding:10px;text-align:left;">Signals</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
      <p style="color:#9ca3af;font-size:12px;margin-top:24px;">
        This is not financial advice. For informational purposes only.
      </p>
    </body></html>
    """


def send_daily_digest(picks_df: pd.DataFrame, explanations: dict[str, str]) -> bool:
    if not GMAIL_USER or not GMAIL_APP_PASS:
        print("[email] No Gmail credentials configured — skipping email.")
        return False

    date_str = datetime.today().strftime("%Y-%m-%d")
    n = len(picks_df)
    subject = f"Market Predictions — {n} setup{'s' if n != 1 else ''} flagged | {date_str}"
    html_body = _build_html(picks_df, explanations, date_str)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = ALERT_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASS)
            server.sendmail(GMAIL_USER, ALERT_EMAIL, msg.as_string())
        print(f"[email] Digest sent to {ALERT_EMAIL}")
        return True
    except Exception as e:
        print(f"[email] Failed to send: {e}")
        return False
