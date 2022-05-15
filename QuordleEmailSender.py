from __future__ import print_function

import smtplib
import ssl
from email.message import EmailMessage
import unrevisioned
import sqlite3 as sl

PORT = 465  # For SSL
CON = sl.connect('QUORDLE_LEADERBOARD.db')

def sendEmail():
    recipients = getRecipients()
    msg = EmailMessage()
    msg.set_content('This is my test message')

    msg['Subject'] = 'Test Subject'
    msg['From'] = "quordleleaderboard@gmail.com"
    msg['To'] = recipients

    # Create a secure SSL context
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    with smtplib.SMTP_SSL("smtp.gmail.com", PORT, context=context) as server:
        server.login("QuordleLeaderboard@gmail.com", unrevisioned.getPassword())
        server.send_message(msg)
        server.quit()

def getRecipients():
    recipients = []
    with CON:
        data = CON.execute("SELECT EMAIL FROM LEADERBOARD ")
        for row in data:
            email = str(row)
            email = email.replace('(\'<', '')
            email = email.replace('>\',)', '')
            recipients.append(email)
        return recipients




if __name__ == '__main__':
    sendEmail()
