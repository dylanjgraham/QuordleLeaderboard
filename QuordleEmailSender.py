from __future__ import print_function

import smtplib
import ssl
from email.message import EmailMessage

import emoji

import unrevisioned
import sqlite3 as sl
from calendar import monthrange
import datetime
import logging

PORT = 465  # For SSL
CON = sl.connect('QUORDLE_LEADERBOARD.db')
IS_LAST_DAY = False
logging.basicConfig(filename='Quordle.log', encoding='utf-8', level = logging.DEBUG)

def sendEmail():
    recipients = getRecipients()
    if len(recipients) > 0:
        body = buildEmailContent()
        msg = EmailMessage()
        msg.set_content(body, subtype='html')

        msg['Subject'] = 'Score Update'
        msg['From'] = "Quordle Leaderboard <quordleleaderboard@gmail.com>"
        msg['Bcc'] = recipients
        logging.debug("Email Recipients: " + str(recipients))

        # Create a secure SSL context
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with smtplib.SMTP_SSL("smtp.gmail.com", PORT, context=context) as server:
            server.login("QuordleLeaderboard@gmail.com", unrevisioned.getPassword())
            server.send_message(msg)
            print("Email Sent")
            server.quit()
            logging.debug("Days remaining = " + str(getDaysRemaining()))
            if getDaysRemaining() == 0:
                logging.warning("Days remaining was " + str(getDaysRemaining()) + " so we are truncating the leaderBoard")
                truncateLeaderboard()
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
        print(recipients)
        return recipients


def buildEmailContent():
    with CON:
        counter = 1
        daysRemaining = getDaysRemaining()
        if daysRemaining > 0:
            html = "<div style=\"padding-bottom:25px\">Days Remaining: " + str(daysRemaining) + "</div>"
        else:
            winners = findWinner()
            stringWinners = ""
            for winner in winners:
                stringWinners += winner + emoji.emojize(":crown:") + ", "
            stringWinners = stringWinners[:-2]  # removes the last comma

            html = "<div style=\"padding-bottom:25px\">Days Remaining: " + str(daysRemaining) + "</div>"
            html += "<div style=\"padding-bottom:25px\">Congratulations " + stringWinners + "</div>"
            addCrownToWinner(winners)
        html += "<style>table, th, td {border: 1px solid black;border-collapse: collapse;}</style>"
        html += "<table style=\"boarder=1px\"><tr><th style=\"padding-right:20px\">Position</th><th>Email</th><th style=\"padding-left=20px\">Score</th><th style=\"padding-left=20px\">Last Round</th><th style=\"padding-left=20px\">Total " + emoji.emojize(":crown:") + "</th></tr>"
        data = CON.execute("SELECT * FROM LEADERBOARD order by TOTAL_SCORE asc")
        for row in data:
            html += "<tr><td style=\"text-align:center\">%s</td>" % counter
            email = row[1].replace('<', '')
            email = email.replace('>', '')
            html += "<td style=\"text-align:center\">%s</td>" % email
            html += "<td style=\"text-align:center\">%s</td>" % row[2]
            html += "<td style=\"text-align:center\">%s</td>" % row[4]
            historicData = CON.execute("SELECT * FROM HISTORIC_WINS where EMAIL = '" + email + "'")
            isInTable = False
            for row2 in historicData:
                isInTable = True
                html += "<td style=\"text-align:center\">%s</td>" % row2[2]
            if not isInTable:
                html += "<td style=\"text-align:center\">%s</td>" % "0"
            counter += 1
        html += "</table>"
        if "**" in html:
            html += "<p>** Indicates a player that was added mid week and therefore has a score of 4 red squares for each " \
                "day they missed </p>"
        print(html)
        return html


def getDaysRemaining():
    today = datetime.datetime.today().weekday()
    daysRemaining = 6 - today
    return daysRemaining

def truncateLeaderboard():
    logging.warning("Truncating leaderBoard")
    with CON:
        CON.execute("DELETE FROM LEADERBOARD")
        print("truncated leaderboard")


def findWinner():
    winners = []
    firstPlaceScore = -1
    data = CON.execute("SELECT * FROM LEADERBOARD order by TOTAL_SCORE asc")
    for row in data:
        email = row[1].replace('<', '')
        email = email.replace('>', '')
        if len(winners) < 1:
            winners.append(email)
            firstPlaceScore = row[2]
        elif row[2] == firstPlaceScore:
            winners.append(email)
        else:
            break
    return winners

def addCrownToWinner(winners):
    isInTable = False
    for email in winners:
        with CON:
            data = CON.execute("SELECT * FROM HISTORIC_WINS WHERE EMAIL = '" + email + "'")
            for row in data:
                isInTable = True
        if isInTable:
            CON.execute("UPDATE HISTORIC_WINS SET NUM_WINS = NUM_WINS + 1 WHERE EMAIL = '" + email + "'")
        else:
            sql = 'INSERT INTO HISTORIC_WINS (EMAIL, NUM_WINS) values(?, ?)'
            data = [
                (email, 1)
            ]
            with CON:
                CON.executemany(sql, data)

def sendMailToMe(message):
    body = message
    msg = EmailMessage()
    msg.set_content(body, subtype='html')

    msg['Subject'] = 'Quordle Error'
    msg['From'] = "Quordle Leaderboard <quordleleaderboard@gmail.com>"
    msg['To'] = 'dylangraham97@gmail.com'

    # Create a secure SSL context
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    with smtplib.SMTP_SSL("smtp.gmail.com", PORT, context=context) as server:
        server.login("QuordleLeaderboard@gmail.com", unrevisioned.getPassword())
        server.send_message(msg)

if __name__ == '__main__':
    sendEmail()
    
