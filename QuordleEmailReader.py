from __future__ import print_function

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import emoji
import sqlite3 as sl

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']
CON = sl.connect('QUORDLE_LEADERBOARD.db')


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
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id']).execute()
                if isNewMessage(msg):
                    print(msg['snippet'] + '\n\n')
                    todaysScore = parseSnippet(msg['snippet'])
                    if todaysScore >= 0:
                        # print('Total Score: ' + str(todaysScore))
                        fromEmail = msg['payload']['headers'][15]['value']
                        storeScore(todaysScore, fromEmail)
                        storeEmailID(msg)
                else:
                    print("Read an old message so we are stopping")
                    break

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}')

# Parse the email for the 4 emojis that contain the score.
def parseSnippet(msg):
    totalScore = 0
    splitMsg = msg.split()
    if splitMsg[0] == 'Daily' and splitMsg[1] == 'Quordle':
        topEmojiScore = splitMsg[3]
        bottomEmojiScore = splitMsg[4]
        fourEmojiScore = topEmojiScore + bottomEmojiScore
        for ii in fourEmojiScore:
            num = emoji.demojize(ii)
            print(num)
            if num.isnumeric():
                totalScore += int(num)
            elif num == ':red_square:':
                totalScore += 10
        return totalScore
    else:
        print('Email didn\'t start with Quordle and is not being read further')
        return -1


def storeScore(todaysScore, email):
    dbRow = getCurrentScoreRecord(email)
    if dbRow:
        currentScore = dbRow[2]
        ID = dbRow[0]
        newScore = currentScore + todaysScore
        sql = 'UPDATE LEADERBOARD SET ID = ' + str(ID) + ', EMAIL = \'' + email + '\', TOTAL_SCORE = ' + str(newScore)
        with CON:
            CON.execute(sql)
    else:
        sql = 'INSERT INTO LEADERBOARD (EMAIL, TOTAL_SCORE) values(?, ?)'
        data = [
            (email, todaysScore)
        ]
        with CON:
            CON.executemany(sql, data)


def getCurrentScoreRecord(email):
    with CON:
        data = CON.execute("SELECT * FROM LEADERBOARD WHERE EMAIL = '" + email + "'")
        for row in data:
            print(row)
            return row
        return None


def isNewMessage(msg):
    with CON:
        data = CON.execute("SELECT * FROM READ_EMAILS WHERE GMAIL_ID = '" + msg['id'] + "'")
        for row in data:
            return False
        return True


# store the emailID so that we know that one was read and we don't accidentally add its score again later
def storeEmailID(msg):
    sql = 'INSERT INTO READ_EMAILS (GMAIL_ID) values(?)'
    data = [
        (msg['id'],)
    ]
    with CON:
        CON.executemany(sql, data)

def setupDB():
    with CON:
        CON.execute("""
            CREATE TABLE READ_EMAILS (
                ID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                GMAIL_ID TEXT
            );
        """)
        CON.execute("""
            CREATE TABLE LEADERBOARD (
                ID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                EMAIL TEXT,
                TOTAL_SCORE INTEGER
            );
        """)


if __name__ == '__main__':
   # Uncomment if this is the first time running the project and you dont have a QuoprdleLeaderBoard.db in the project directory
   # setupDB()
    main()
