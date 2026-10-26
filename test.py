import smtplib
import ssl
import getpass

HOST = "email-smtp.ap-southeast-1.amazonaws.com"
PORT = 587

USERNAME = input("SES SMTP Username: ")
PASSWORD = getpass.getpass("SES SMTP Password: ")
SENDER = "noreply@biin.softsync.bd"
RECEIVER = input("Receiver Email: ")

message = f"""From: {SENDER}
To: {RECEIVER}
Subject: AWS SES SMTP Test

AWS SES Singapore SMTP is working successfully!
"""

try:
    with smtplib.SMTP(HOST, PORT, timeout=20) as server:
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()
        server.login(USERNAME, PASSWORD)
        print("SMTP Authentication: SUCCESS")

        server.sendmail(SENDER, [RECEIVER], message)
        print("Email Sent: SUCCESS")

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")