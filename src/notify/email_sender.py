"""Email notification via SMTP."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from pathlib import Path


def send_report_email(html_path: str, config: dict):
    """Send daily report HTML as email."""
    notify = config.get("notify", {})
    if not notify.get("enabled", False):
        print("Email notification disabled, skipping.")
        return

    html_file = Path(html_path)
    html_content = html_file.read_text(encoding="utf-8")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(f"知识星球日报 - {html_file.stem}", "utf-8")
    msg["From"] = notify["sender_email"]
    msg["To"] = notify["recipient_email"]

    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        server = smtplib.SMTP_SSL(notify["smtp_host"], notify["smtp_port"])
        server.login(notify["sender_email"], notify["sender_password"])
        server.sendmail(
            notify["sender_email"],
            [notify["recipient_email"]],
            msg.as_string(),
        )
        server.quit()
        print(f"Email sent to {notify['recipient_email']}")
    except Exception as e:
        print(f"Email failed: {e}")
