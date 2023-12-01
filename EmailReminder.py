import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
import sqlite3 as sl

import smtplib
import ssl
from email.message import EmailMessage
import unrevisioned
import QuordleEmailReader

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']
CON = sl.connect('QUORDLE_LEADERBOARD.db')
PORT = 465  # For SSL
logging.basicConfig(filename='Quordle.log', encoding='utf-8', level=logging.DEBUG)


def main():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        # Call the Gmail API
        service = build('gmail', 'v1', credentials=creds)
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])

        # Call the Gmail API to fetch INBOX
        results = service.users().messages().list(userId='me', labelIds=['INBOX']).execute()
        messages = results.get('messages', [])

        if not messages:
            print("No messages found.")
        else:
            print("Message snippets:")
            currentPlayers = getCurrentPlayers()
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id']).execute()
                logging.debug("Found Message ID: " + message['id'])
                if isNewMessage(msg):
                    fromEmail = QuordleEmailReader.findFromEmail(msg['payload']['headers'])
                    if isBadFormatEmail(msg['snippet']):
                        badFormatBody = ("Hello,\n" +
                                         "The email you sent was not in the correct format and will not be calculated tonight.\n" +
                                         "If this email was not a score submission then no further action is required and I will get back to " +
                                         "you when I see this message. \n" +
                                         "If this was a score submission be sure it starts with \"Daily Quordle\". This message will " +
                                         "not be counted and you should resumbit your score to prevent recieving a penalty. \n \n" +
                                         " For more info on what a proper submission should look like please go to https://quordleleaderboard.com/ \n \n" +
                                         "Thanks for playing, \n Dylan")
                        sendEmail(fromEmail, 'Unable to Parse Quordle Score', badFormatBody)
                    else:
                        for player in currentPlayers:
                            if player == fromEmail:
                                currentPlayers.remove(player)
                                break
                else:
                    print("Read an old message")
                    logging.debug(
                        "Read an old message; Anyone left in currentPlayers list has not sent in a quordle yet today")

                    if len(currentPlayers) > 0:
                        body = ("It looks like you may have forgotten to send in your Quordle Email today! \n \n" +
                                "Be sure to send it in before 11:55 pm EST tonight! \n \n" +
                                "Please do not reply to this email. Send your score as a new message to Quordleleaderboard@gmail.com")
                        logging.debug("Email Recipients of reminder email: " + str(currentPlayers))
                        sendEmail(currentPlayers, 'Quordle Reminder', body)
                        break
                    else:
                        print("Everyone already sent in their quordle score today :)")
                        break

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}')
        logging.error('Likely bad credentials ' + error)


def isNewMessage(msg):
    with CON:
        data = CON.execute("SELECT * FROM READ_EMAILS WHERE GMAIL_ID = '" + msg['id'] + "'")
        for row in data:
            return False
        return True


def getCurrentPlayers():
    players = []
    with CON:
        data = CON.execute("SELECT DISTINCT EMAIL FROM LEADERBOARD")
        for row in data:
            players.append(str(row[0]))
        # should only come to this on monday when the leaderboard is empty. We will artificially add the three
        # below emails to make sure they are always reminded.
        if len(players) == 0:
            players.append("<dylangraham97@gmail.com>")
            players.append("<kengraham717@gmail.com>")
            players.append("<robert.paquin1@gmail.com>")
        return players


def isBadFormatEmail(msg):
    # Check that the message is in the right format. If it is not we will tell them at this 5pm run
    # to try to give them a chance to correct it.
    splitMsg = msg.split()
    # check to see if there was any email content to parse
    if splitMsg:
        if splitMsg[0] == 'Daily' and splitMsg[1] == 'Quordle':
            print('All is good. No further action required')
            return False
        else:
            print('Email didn\'t start with Daily Quordle')
            return True
    else:
        print('Email had no parseable content?')
        return True


def sendEmail(pRecipient, pSubject, pBody):
    msg = EmailMessage()
    msg.set_content(pBody, subtype='html')

    msg['Subject'] = pSubject
    msg['From'] = "Quordle Leaderboard <quordleleaderboard@gmail.com>"
    msg['Bcc'] = pRecipient
    logging.debug("Email being sent to: " + str(pRecipient))

    # Create a secure SSL context
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    with smtplib.SMTP_SSL("smtp.gmail.com", PORT, context=context) as server:
        server.login("QuordleLeaderboard@gmail.com", unrevisioned.getPassword())
        server.send_message(msg)
        print("Reminder Email Sent")
        server.quit()


if __name__ == '__main__':
    main()