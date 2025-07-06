import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASS

def send_alert(recipients, subject, body_text, body_html=None):
    """
    Send an email alert to the given recipients.
    - recipients: list of email addresses
    - subject: email subject line
    - body_text: plain-text version of the email
    - body_html: optional HTML version
    """
    msg = MIMEMultipart('alternative')
    msg['From'] = SMTP_USER
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = subject

    # Attach the plain-text part
    part1 = MIMEText(body_text, 'plain')
    msg.attach(part1)

    # Attach the HTML part if provided
    if body_html:
        part2 = MIMEText(body_html, 'html')
        msg.attach(part2)

    # Send the email via SMTP
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, recipients, msg.as_string())
