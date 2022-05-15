from __future__ import print_function

import smtplib
import ssl
from email.message import EmailMessage
import unrevisioned
import sqlite3 as sl
from calendar import monthrange
import datetime

PORT = 465  # For SSL
CON = sl.connect('QUORDLE_LEADERBOARD.db')

def sendEmail():
    recipients = getRecipients()
    if len(recipients) > 0:
        body = buildEmailContent()
        msg = EmailMessage()
        msg.set_content(body, subtype='html')

        msg['Subject'] = 'Score Update'
        msg['From'] = "Quordle Leaderboard <quordleleaderboard@gmail.com>"
        # msg['To'] = recipients
        msg['To'] = 'dylangraham97@gmail.com'

        # Create a secure SSL context
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with smtplib.SMTP_SSL("smtp.gmail.com", PORT, context=context) as server:
            server.login("QuordleLeaderboard@gmail.com", unrevisioned.getPassword())
            server.send_message(msg)
            server.quit()
    else:
        print("No recipients found in the table")

def getRecipients():
    recipients = []
    with CON:
        data = CON.execute("SELECT EMAIL FROM LEADERBOARD")
        for row in data:
            email = str(row)
            email = email.replace('(\'<', '')
            email = email.replace('>\',)', '')
            recipients.append(email)
        return recipients


def buildEmailContent():
    counter = 1
    today = datetime.datetime.today()
    daysInMonth = monthrange(today.year, today.month)
    daysRemaining = daysInMonth[1] - today.day
    html = "<div style=\"padding-bottom:25px\">Days Remaining: " + str(daysRemaining) + "</div>"
    html += "<style>table, th, td {border: 1px solid black;border-collapse: collapse;}</style>"
    html += "<table style=\"boarder=1px\"><tr><th style=\"padding-right:20px\">Position</th><th>Email</th><th style=\"padding-left=20px\">Score</th></tr>"
    with CON:
        data = CON.execute("SELECT * FROM LEADERBOARD order by TOTAL_SCORE asc")
        for row in data:
            html += "<tr><td style=\"text-align:center\">%s</td>" % counter
            email = row[1].replace('<', '')
            email = email.replace('>', '')
            html += "<td style=\"text-align:center\">%s</td>" % email
            html += "<td style=\"text-align:center\">%s</td>" % row[2]
            counter += 1
        html += "</table>"
        return html


if __name__ == '__main__':
    sendEmail()
